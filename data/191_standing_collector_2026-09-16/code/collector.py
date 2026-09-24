#!/usr/bin/env python3
"""Standing data collector for the recession-research programme (collection 191).

Plain HTTP fetches, python3 stdlib only (pandas is optional and only used to try to read the GPR .xls).
Every job is registered in sources.json (order, parameters, derived-series rules); this file holds the
per-source fetch/parse functions.  Everything lands under ../warehouse/<source>/ ; derived series are
two-column CSVs (date,value).  One log: ../logs/collector.log.  One lock: ../logs/collector.lock.

  python3 collector.py once            run every enabled job one time
  python3 collector.py loop            run every job, sleep (sources.json: loop_sleep_hours), repeat forever
  python3 collector.py <job> [<job>..] run the named job(s)
  python3 collector.py list            print the job registry
  add --force to ignore the "refreshed < fresh_hours ago" skip

Resumable: a file refreshed less than fresh_hours (20) ago is not fetched again; FRED bulk files are
skipped for fred.fresh_days (7) days; past-year archives that cannot change are kept once fetched.
"""
import os, re, sys, csv, io, json, gzip, time, glob, html, math, queue, atexit, socket, shutil, hashlib, threading, traceback
import urllib.request, urllib.error, urllib.parse
from datetime import datetime, date, timedelta, timezone
try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None

CODE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(CODE)
WH = os.path.join(ROOT, 'warehouse')
LOGS = os.path.join(ROOT, 'logs')
os.makedirs(WH, exist_ok=True); os.makedirs(LOGS, exist_ok=True)
SRC = json.load(open(os.path.join(CODE, 'sources.json')))
DATA_ROOT = os.path.dirname(ROOT)                       # ".../Onset Detector Data"
ENV = os.path.join(DATA_ROOT, SRC.get('env_file', 'onset-detector-new-2026-08-23/live_data/config/local.env'))
FORCE = '--force' in sys.argv
ARGS = [a for a in sys.argv[1:] if not a.startswith('--')]
UA = SRC['http'].get('user_agent', 'Mozilla/5.0')
TODAY = lambda: date.today().isoformat()

# One FRED rate limit for every collector on this Mac (17 Sep 2026): the queue collector in _collector calls the same
# gate. FRED counts requests per address, and the two programs throttling themselves separately drew 55 blocks.
sys.path.insert(0, os.path.join(DATA_ROOT, '_shared'))
try:
    from fred_gate import fred_wait, fred_blocked
except Exception:
    def fred_wait(*a, **k): return 0.0
    def fred_blocked(*a, **k): return 0.0

# The fetch engine (17 Sep 2026): conditional requests, kept-alive connections, and a ladder of other ways to the same
# bytes when a door is shut. See _shared/fetch_engine.py.
try:
    import fetch_engine as FE          # FE.LOG is wired to log() below, once log() exists
except Exception:
    FE = None

# ------------------------------------------------------------------ keys (never logged)
def key(name):
    try: txt = open(ENV).read()
    except OSError: return ''
    m = re.search(r'^%s=([^\r\n]+)' % re.escape(name), txt, re.M)
    return m.group(1).strip().strip('"').strip("'") if m else ''

def fred_keys():
    """The pool keys only, when there is a pool: the primary FRED_API_KEY is left to the live system (bhs_update.py),
    which was answered 429 while the bulk pull shared its key (16 September 2026)."""
    k = key('FRED_API_KEY')
    pool = [x.strip() for x in key('FRED_API_KEY_POOL').split(',') if x.strip()]
    pool = [x for x in dict.fromkeys(pool) if x != k]
    return pool if pool else ([k] if k else [])

def redact(u):
    return re.sub(r'(api_key=)[^&]+', r'\1***', u)

# ------------------------------------------------------------------ log
def _rotate_log():
    """Keep the log bounded (17 Sep 2026): past 40 MB it is compressed beside itself at the next start."""
    p = os.path.join(LOGS, 'collector.log')
    try:
        if os.path.getsize(p) > 40 * 1048576:
            dst = os.path.join(LOGS, 'collector_until_%s.log.gz' % time.strftime('%Y-%m-%d_%H%M'))
            with open(p, 'rb') as a, gzip.open(dst, 'wb') as b: shutil.copyfileobj(a, b)
            open(p, 'w').close()
    except OSError: pass
_rotate_log()
_LOGF = open(os.path.join(LOGS, 'collector.log'), 'a')
_loglk = threading.Lock()
def log(*a):
    s = time.strftime('%Y-%m-%d %H:%M:%S ') + ' '.join(str(x) for x in a)
    with _loglk:
        _LOGF.write(s + '\n'); _LOGF.flush()
    try:
        if sys.stdout.isatty(): print(s, flush=True)   # under launchd stdout is a file: the log is not written twice
    except Exception: pass

# ------------------------------------------------------------------ http
try:                                   # a long pass over many addresses needs more than the default 256 descriptors
    import resource
    _soft, _hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    resource.setrlimit(resource.RLIMIT_NOFILE, (max(_soft, min(4096, _hard)), _hard))
except Exception:
    pass

if FE is not None: FE.LOG[0] = log     # the engine writes into the collector's own log

class _LastCode(threading.local):
    """The code of the most recent request, per thread. A plain list was read by whichever job asked first once jobs
    began running beside each other (17 September 2026)."""
    code = None

_LC = _LastCode()


class _LastCodeView:
    def __getitem__(self, i): return _LC.code
    def __setitem__(self, i, v): _LC.code = v


LAST_CODE = _LastCodeView()
def http_get(url, headers=None, timeout=None, retries=None, data=None, method=None, quiet=False,
             if_path=None, alts=None, min_bytes=1, allow=None):
    """GET (or POST when data is given) through the fetch engine: conditional, connection-reusing, and, when a door is
    shut, walking the ladder of other ways to the same bytes. Returns bytes, FE.NOT_MODIFIED when the source says
    nothing changed, or None. Falls back to the plain loop below when the engine is missing."""
    if FE is not None:
        b = FE.smart_get(url, headers=headers, timeout=timeout or SRC['http'].get('timeout', 120), if_path=if_path,
                         alts=alts, data=data, method=method, allow=allow, min_bytes=min_bytes, quiet=quiet)
        LAST_CODE[0] = FE.last_code()
        if b is None and not quiet: log('FAIL', LAST_CODE[0], redact(url)[:200])
        return b
    return _http_get_plain(url, headers, timeout, retries, data, method, quiet)


def _http_get_plain(url, headers=None, timeout=None, retries=None, data=None, method=None, quiet=False):
    """GET (or POST when data is given). Returns bytes or None. 4xx (except 429) are not retried."""
    timeout = timeout or SRC['http'].get('timeout', 120)
    retries = retries or SRC['http'].get('retries', 4)
    h = {'User-Agent': UA, 'Accept': '*/*'}; h.update(headers or {})
    LAST_CODE[0] = None; last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=h, data=data, method=method)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                LAST_CODE[0] = r.status
                return r.read()
        except urllib.error.HTTPError as e:
            LAST_CODE[0] = e.code; last = 'HTTP %d' % e.code
            body = ''
            try: body = e.read(300).decode(errors='ignore').replace('\n', ' ')
            except Exception: pass
            if e.code in (400, 401, 403, 404, 405, 410, 422):
                if not quiet: log('HTTP', e.code, redact(url)[:220], body[:120])
                return None
            log('HTTP', e.code, 'attempt', attempt + 1, redact(url)[:220], body[:80])
            time.sleep((30 if e.code == 429 else 6) * (attempt + 1))
        except Exception as e:
            last = type(e).__name__
            log('ERR', type(e).__name__, str(e)[:90], 'attempt', attempt + 1, redact(url)[:220])
            time.sleep(6 * (attempt + 1))
    log('FAIL', last, redact(url)[:220])
    return None

def http_json(url, **kw):
    # 24 Sep 2026 (ops-0924): a JSON caller needs the body. The engine made every request conditional from its cached
    # ETag, the source answered 304 with no body, and json.loads read that as an error - so each unchanged JSON listing
    # (Indeed's GitHub listings, for days) looked failed and nothing it lists was fetched. Asked unconditionally now:
    # an if_path that does not exist tells the engine there is no copy to compare with.
    kw.setdefault('if_path', os.path.join(WH, '.no-copy--ask-unconditionally'))
    b = http_get(url, **kw)
    if b is None: return None
    if FE is not None and b is FE.NOT_MODIFIED: return None
    try: return json.loads(b)
    except Exception as e:
        log('BADJSON', type(e).__name__, redact(url)[:200], b[:100]); return None

def http_stream_gz(url, out, headers=None, timeout=600):
    """Stream a (large) response straight into out (.gz). Returns bytes received or None."""
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tmp = out + '.tmp'; LAST_CODE[0] = None
    h = {'User-Agent': UA, 'Accept': '*/*'}; h.update(headers or {})
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=h); n = 0; t0 = time.time()
            with urllib.request.urlopen(req, timeout=timeout) as r, gzip.open(tmp, 'wb', compresslevel=4) as f:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk: break
                    f.write(chunk); n += len(chunk)
            os.replace(tmp, out)
            log('  streamed', os.path.relpath(out, WH), n, 'bytes', '%.0fs' % (time.time() - t0))
            return n
        except urllib.error.HTTPError as e:
            LAST_CODE[0] = e.code
            log('HTTP', e.code, redact(url)[:200])
            if e.code in (400, 401, 403, 404, 410): return _stream_by_curl(url, out, headers, timeout)
            time.sleep(15 * (attempt + 1))
        except Exception as e:
            log('ERR', type(e).__name__, str(e)[:90], redact(url)[:200]); time.sleep(15 * (attempt + 1))
    return _stream_by_curl(url, out, headers, timeout)


def _stream_by_curl(url, out, headers=None, timeout=1800):
    """The same download through curl, straight into the compressed file. The streaming path used to be the one place
    the fetch engine's ladder did not reach, which is how the Mexican social-security register (403 to a plain
    request, 402 MB through curl) was recorded as unavailable (17 September 2026)."""
    tmp = out + '.tmp'
    cmd = ['curl', '-sSL', '--compressed', '--max-time', str(int(timeout)),
           '-A', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36']
    for k, v in (headers or {}).items(): cmd += ['-H', '%s: %s' % (k, v)]
    cmd.append(url)
    try:
        import subprocess
        t0 = time.time(); n = 0
        with subprocess.Popen(cmd, stdout=subprocess.PIPE) as pr, gzip.open(tmp, 'wb', compresslevel=4) as f:
            while True:
                chunk = pr.stdout.read(1 << 20)
                if not chunk: break
                f.write(chunk); n += len(chunk)
        if n < 1000:
            try: os.remove(tmp)
            except OSError: pass
            log('  curl stream got nothing', redact(url)[:150]); return None
        os.replace(tmp, out)
        log('  streamed by curl', os.path.relpath(out, WH), n, 'bytes', '%.0fs' % (time.time() - t0))
        return n
    except Exception as e:
        log('  curl stream failed', type(e).__name__, str(e)[:100]); return None

def nimble_fetch(url, render=False):
    """Nimble Web API (only used where plain HTTP cannot get the page). Returns HTML text or None."""
    k = key('NIMBLE_API_KEY')
    if not k: log('nimble: no key'); return None
    body = json.dumps({'url': url, 'format': 'html', 'render': bool(render), 'country': 'US'}).encode()
    b = http_get(SRC['nimble']['web_endpoint'], headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + k},
                 data=body, timeout=200, retries=2)
    if b is None: return None
    log('  nimble fetched', url[:120], len(b), 'bytes')
    return b.decode(errors='ignore')

# ------------------------------------------------------------------ files
def fresh(path, hours=None):
    if FORCE: return False
    hours = SRC.get('fresh_hours', 20) if hours is None else hours
    try: return (time.time() - os.path.getmtime(path)) < hours * 3600
    except OSError: return False

def write_bytes(path, b):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    if path.endswith('.gz') and not b[:2] == b'\x1f\x8b':
        with gzip.open(tmp, 'wb', compresslevel=5) as f: f.write(b)
    else:
        with open(tmp, 'wb') as f: f.write(b)
    os.replace(tmp, path)

def write_text(path, s):
    write_bytes(path, s.encode('utf-8'))

def write_json(path, obj):
    write_bytes(path, json.dumps(obj).encode('utf-8'))

def write_csv(path, header, rows, gz=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    gz = path.endswith('.gz') if gz is None else gz
    tmp = path + '.tmp'; n = 0
    f = gzip.open(tmp, 'wt', newline='', encoding='utf-8', compresslevel=5) if gz else open(tmp, 'w', newline='', encoding='utf-8')
    with f:
        w = csv.writer(f); w.writerow(header)
        for r in rows: w.writerow(r); n += 1
    os.replace(tmp, path)
    return n

def fmt(v):
    if isinstance(v, float):
        if v != v: return ''
        return ('%.10g' % v)
    return v

def write_series(path, pairs, quiet=False):
    """Two-column date,value CSV. pairs: dict date->value or iterable of (date, value). Sorted; None/NaN dropped."""
    if isinstance(pairs, dict): pairs = pairs.items()
    rows = []
    for d, v in pairs:
        if d is None or v is None or v == '': continue
        if isinstance(v, float) and v != v: continue
        rows.append((d, fmt(v)))
    rows.sort()
    if not rows:
        log('  series', os.path.relpath(path, WH), 'EMPTY (not written)'); return 0
    n = write_csv(path, ['date', 'value'], rows)
    if not quiet: log('  series', os.path.relpath(path, WH), n, 'rows', rows[0][0], '->', rows[-1][0])
    return n

def read_series(path):
    d = {}
    if not os.path.exists(path): return d
    for r in read_csv_rows(path):
        if r.get('date') and r.get('value') not in (None, ''): d[r['date']] = r['value']
    return d

def read_csv_rows(path, encoding='utf-8-sig'):
    op = gzip.open if path.endswith('.gz') else open
    with op(path, 'rt', newline='', encoding=encoding, errors='replace') as f:
        rd = csv.DictReader(f)
        rows = []
        for r in rd:
            rows.append({(k or '').strip(): (v.strip() if isinstance(v, str) else v) for k, v in r.items()})
        return rows

def read_csv_lists(path, encoding='utf-8-sig'):
    """(header, rows) with rows as lists -- for the big tables (memory)."""
    op = gzip.open if path.endswith('.gz') else open
    with op(path, 'rt', newline='', encoding=encoding, errors='replace') as f:
        rd = csv.reader(f); header = next(rd, [])
        return [h.strip() for h in header], [r for r in rd if r]

def to_iso(s, fmts=None):
    s = (s or '').strip()
    if not s: return None
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})', s)
    if m: return '%s-%s-%s' % m.groups()
    m = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{4})', s)
    if m: return '%s-%02d-%02d' % (m.group(3), int(m.group(1)), int(m.group(2)))
    m = re.match(r'^(\d{4})(\d{2})(\d{2})$', s)
    if m: return '%s-%s-%s' % m.groups()
    for f in (fmts or []):
        try: return datetime.strptime(s, f).strftime('%Y-%m-%d')
        except ValueError: pass
    return None

def num(s):
    """'12,345' -> 12345.0 ; '(8.5)' -> -8.5 ; '' -> None"""
    if s is None: return None
    if isinstance(s, (int, float)): return float(s)
    t = str(s).strip().replace(',', '').replace('$', '')
    if t in ('', '.', '-', 'NA', 'N/A', 'ND', 'null', 'None', '---'): return None
    neg = t.startswith('(') and t.endswith(')')
    if neg: t = t[1:-1]
    try: return -float(t) if neg else float(t)
    except ValueError: return None

def rolling_sum(series, window):
    """series: dict date->float (daily). Sum over the trailing window where every day is present."""
    out = {}
    for d in series:
        d0 = date.fromisoformat(d); tot = 0.0; ok = True
        for i in range(window):
            v = series.get((d0 - timedelta(days=i)).isoformat())
            if v is None: ok = False; break
            tot += v
        if ok: out[d] = tot
    return out

MONTHS = {m.lower(): i + 1 for i, m in enumerate(['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'])}
MONTHS.update({m[:3]: MONTHS[m] for m in list(MONTHS)})
MONTHS['sept'] = 9

def html_tables(h):
    """Every <table> as a list of rows (list of cell strings)."""
    out = []
    for t in re.findall(r'<table[^>]*>(.*?)</table>', h, re.S | re.I):
        rows = []
        for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', t, re.S | re.I):
            cells = [html.unescape(re.sub(r'<[^>]+>', ' ', c)) for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr, re.S | re.I)]
            cells = [re.sub(r'\s+', ' ', c).strip() for c in cells]
            if cells: rows.append(cells)
        if rows: out.append(rows)
    return out

# ------------------------------------------------------------------ generic "files" job
LOW_DISK = [False]

def keep_vintage(job, f, out):
    """Real-time record of a plain file (added 17 Sep 2026). When the job says keep_vintages, a dated, gzipped copy of
    the file is kept under <dir>/vintages/ every time its content changes, so what a source showed on each day can be
    read back later (most sources overwrite their history when they revise). The content is compared by sha256 of the
    unpacked bytes, so an unchanged file costs nothing. Files above vintage_max_mb (default 30) are left out, and
    nothing is kept while the disk is low."""
    if not (job.get('keep_vintages') and f.get('keep_vintages', True)) or LOW_DISK[0]: return
    try:
        if os.path.getsize(out) > 1048576 * f.get('vintage_max_mb', job.get('vintage_max_mb', 30)): return
        h = hashlib.sha256()
        op = gzip.open if out.endswith('.gz') else open
        with op(out, 'rb') as fh:
            for ch in iter(lambda: fh.read(1 << 20), b''): h.update(ch)
        vd = os.path.join(os.path.dirname(out), 'vintages'); mark = os.path.join(vd, os.path.basename(out) + '.lastsha')
        last = open(mark).read().strip() if os.path.exists(mark) else ''
        if last == h.hexdigest(): return
        dst = os.path.join(vd, TODAY() + '__' + os.path.basename(out)); os.makedirs(vd, exist_ok=True)
        if out.endswith('.gz') or out.endswith('.zip') or out.endswith('.xlsx'):
            shutil.copyfile(out, dst)
        else:
            with open(out, 'rb') as a, gzip.open(dst + '.gz', 'wb', compresslevel=6) as b: shutil.copyfileobj(a, b)
        write_text(mark, h.hexdigest())
        log('  vintage kept', os.path.relpath(dst, WH))
    except Exception as e:
        log('  vintage EXC', f.get('out'), type(e).__name__, str(e)[:100])

def _fetch_file(job, f, d):
    """One file of a files job. Returns 'fresh', 'unchanged', 'saved', 'skipped' or a failure word. Raises nothing."""
    out = os.path.join(d, f['out'])
    hours = f.get('fresh_hours', job.get('fresh_hours'))
    if fresh(out, hours) or fresh(out + '.gz', hours):
        log('  fresh', f['out']); return 'fresh', out
    if os.path.exists(out + '.gz') and not os.path.exists(out):
        out_gz = out + '.gz'                      # a large file kept compressed at rest; its date governs freshness
    else:
        out_gz = None
    if job.get('mark_404_days') and fresh(out + '.404', 24 * job['mark_404_days']):
        return 'skipped', out
    if f.get('stream'):
        n = http_stream_gz(f['url'], out, headers=f.get('headers'))
        if n is None:
            log('  FAIL', f['out'], 'code', LAST_CODE[0]); return 'fail', out
        keep_vintage(job, f, out); return 'saved', out
    b = http_get(f['url'], headers=f.get('headers'), if_path=out, alts=f.get('alt_urls'),
                 min_bytes=f.get('min_bytes', 100))
    if FE is not None and b is FE.NOT_MODIFIED:
        if not os.path.exists(out):                   # 'unchanged' with nothing on disk is not an answer: ask again plainly
            b = http_get(f['url'], headers=f.get('headers'), alts=f.get('alt_urls'), min_bytes=f.get('min_bytes', 100))
            if b is None or b is FE.NOT_MODIFIED:
                log('  FAIL', f['out'], 'code', LAST_CODE[0]); return 'fail', out
        else:
            try: os.utime(out, None)                  # the source says it has not changed: nothing crossed the wire
            except OSError: pass
            return 'unchanged', out
    if b is None:
        log('  FAIL', f['out'], 'code', LAST_CODE[0])
        if LAST_CODE[0] == 404 and job.get('mark_404_days'): write_text(out + '.404', datetime.now().isoformat())
        return ('throttled' if LAST_CODE[0] in (429, None) else 'fail'), out
    if len(b) < f.get('min_bytes', 100):
        log('  too small', f['out'], len(b)); return 'fail', out
    # A file past the threshold is kept gzipped at rest. Every reader in this programme opens .gz directly, and the
    # warehouse's uncompressed comma-separated files were five and a third gigabytes of the fourteen (18 Sep 2026).
    thresh = int(SRC.get('gzip_over_mb', 40)) * 1048576
    if len(b) > thresh and not f['out'].endswith(('.gz', '.zip', '.xlsx', '.xls', '.pdf', '.parquet')):
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with gzip.open(out + '.gz.tmp', 'wb', compresslevel=6) as g:
            g.write(b)
        os.replace(out + '.gz.tmp', out + '.gz')
        if os.path.exists(out):
            try: os.remove(out)
            except OSError: pass
        log('  saved', f['out'] + '.gz', len(b), 'bytes in,', os.path.getsize(out + '.gz'), 'kept')
        keep_vintage(job, f, out + '.gz')
        return 'saved', out + '.gz'
    write_bytes(out, b); log('  saved', f['out'], len(b), 'bytes')
    keep_vintage(job, f, out)
    if job.get('pause_seconds'): time.sleep(job['pause_seconds'])
    return 'saved', out


def job_files(job):
    """Plain files.

    Each file is asked for conditionally: when a copy is already on disk the request carries its date and its ETag, so
    a source that has not changed answers 304 with an empty body and the file costs a round trip instead of a download.
    A file that cannot be had at its own address is tried at `alt_urls` and, inside the engine, by other routes to the
    same bytes. Options for a throttled source: stop_after_throttles (the job ends for this cycle after that many
    answers of 429 or no answer), pause_seconds (a wait after each file), mark_404_days (a file answered 404 is not
    asked for again for that many days), parallel (how many files at once; only for sources with no rate limit).
    """
    d = os.path.join(WH, job['dir']); throttled = 0
    par = int(job.get('parallel', 1))
    if par > 1 and not job.get('pause_seconds') and not job.get('stop_after_throttles') and FE is not None:
        for f, res in FE.fetch_many(job['files'], lambda f: _fetch_file(job, f, d), threads=par):
            out = res[1] if res else os.path.join(d, f['out'])
            for dv in f.get('derive', []):
                try: derive(dv, out, os.path.join(d, 'derived'))
                except Exception as e: log('  derive EXC', f['out'], dv.get('type'), type(e).__name__, str(e)[:120])
        return
    for f in job['files']:
        try:
            state, out = _fetch_file(job, f, d)
        except Exception as e:
            log('  file EXC', f.get('out'), type(e).__name__, str(e)[:120]); continue
        if state == 'throttled':
            throttled += 1
            if job.get('stop_after_throttles') and throttled >= job['stop_after_throttles']:
                log('  throttled', throttled, 'times: job ends for this cycle, the rest follow on the next'); break
        for dv in f.get('derive', []):
            try: derive(dv, out, os.path.join(d, 'derived'))
            except Exception as e: log('  derive EXC', f['out'], dv.get('type'), type(e).__name__, str(e)[:120])


def job_dated_files(job):
    """Files whose address is built from a date rather than found on a page.

    Added 17 September 2026 for sources that publish at a predictable address each month or week and give no index
    page a program may read (the NFIB monthly report is the case that forced it: its own pages answer 403 to everything
    while the report itself sits at an open address carrying the month). For each pattern the last `months` months (or
    `weeks` weeks) are built with strftime and asked for once; an address that answers 404 is marked and not asked for
    again for `mark_404_days`, so a month that has not been published yet costs one request and then nothing. Every
    file kept is dated by construction, so the folder is a vintage archive without any further work."""
    d = os.path.join(WH, job['dir'])
    today = date.today()
    for spec in job.get('patterns', []):
        if spec.get('quarters'):                      # an address carrying a year and a quarter, as the QCEW does
            n = int(spec['quarters']); y, q = today.year, (today.month - 1) // 3 + 1
            for _ in range(n):
                url = spec['url'].format(y=y, q=q); out = os.path.join(d, spec['out'].format(y=y, q=q))
                q -= 1
                if q == 0: q = 4; y -= 1
                if os.path.exists(out) and os.path.getsize(out) > spec.get('min_bytes', 2000): continue
                if fresh(out + '.404', 24 * spec.get('mark_404_days', 7)): continue
                b = http_get(url, min_bytes=spec.get('min_bytes', 2000), quiet=True)
                if b is None or (FE is not None and b is FE.NOT_MODIFIED):
                    write_text(out + '.404', datetime.now().isoformat()); continue
                write_bytes(out, b); log('  saved', os.path.relpath(out, d), len(b), 'bytes')
            continue
        back = (int(spec.get('days', 0)) or int(spec.get('months', 0)) or int(spec.get('weeks', 0)) or 6)
        step_weeks = bool(spec.get('weeks'))
        for i in range(back):
            if spec.get('days'):
                when = today - timedelta(days=i)
            elif step_weeks:
                when = today - timedelta(days=7 * i)
            else:
                y, m = today.year, today.month - i
                while m <= 0: m += 12; y -= 1
                when = date(y, m, 1)
            url = when.strftime(spec['url'])
            if spec.get('lower'): url = url.replace(when.strftime('%b'), when.strftime('%b').lower())
            out = os.path.join(d, when.strftime(spec['out']))
            if os.path.exists(out) and os.path.getsize(out) > spec.get('min_bytes', 2000): continue
            if fresh(out + '.404', 24 * spec.get('mark_404_days', 7)): continue
            b = http_get(url, min_bytes=spec.get('min_bytes', 2000), quiet=True)
            if b is None or (FE is not None and b is FE.NOT_MODIFIED):
                write_text(out + '.404', datetime.now().isoformat()); continue
            write_bytes(out, b); log('  saved', os.path.relpath(out, d), len(b), 'bytes')


def derive(spec, raw, outdir):
    t = spec.get('type', 'columns')
    DERIVERS[t](spec, raw, outdir)

def derive_columns(spec, raw, outdir):
    rows = read_csv_rows(raw, spec.get('encoding', 'utf-8-sig'))
    dc = spec['date_col']; fmts = spec.get('date_fmts')
    for col, name in spec['value_cols'].items():
        pairs = []
        for r in rows:
            d = to_iso(r.get(dc), fmts); v = (r.get(col) or '').strip().replace(',', '')
            if d and num(v) is not None: pairs.append((d, v))
        write_series(os.path.join(outdir, name + '.csv'), pairs)

def derive_ymd(spec, raw, outdir):
    rows = read_csv_rows(raw)
    for col, name in spec['value_cols'].items():
        pairs = []
        for r in rows:
            try: d = '%04d-%02d-%02d' % (int(r['year']), int(r['month']), int(r['day']))
            except Exception: continue
            if num(r.get(col)) is not None: pairs.append((d, r[col].strip()))
        write_series(os.path.join(outdir, name + '.csv'), pairs)

def derive_bfs_wide(spec, raw, outdir):
    rows = read_csv_rows(raw); freq = spec.get('freq', 'monthly')
    geos = set(spec.get('geos', ['US'])); sectors = set(spec.get('sectors', ['TOTAL']))
    series = {}
    for r in rows:
        if r.get('geo') not in geos or (r.get('naics_sector', 'TOTAL') not in sectors): continue
        k = (r['series'], r['geo'], r['sa'])
        for col, v in r.items():
            if freq == 'monthly' and col in MONTHS and num(v) is not None:
                series.setdefault(k, {})['%s-%02d-01' % (r['year'], MONTHS[col])] = v
            elif freq == 'quarterly' and re.fullmatch(r'Q[1-4]', col) and num(v) is not None:
                series.setdefault(k, {})['%s-%02d-01' % (r['year'], 3 * int(col[1]) - 2)] = v
    for (s, g, sa), d in sorted(series.items()):
        write_series(os.path.join(outdir, 'bfs_%s_%s_%s_%s.csv' % (s, g, 'SA' if sa == 'A' else 'NSA', freq)), d)

def derive_ar539(spec, raw, outdir):
    ic, cw, states = {}, {}, {}
    with open(raw, newline='', encoding='utf-8-sig', errors='replace') as f:
        for r in csv.DictReader(f):
            d = to_iso(r.get('rptdate')); d2 = to_iso(r.get('c2')) or d
            if not d: continue
            a, b = num(r.get('c3')), num(r.get('c8'))
            if a is not None: ic[d] = ic.get(d, 0.0) + a
            if b is not None: cw[d2] = cw.get(d2, 0.0) + b
            states.setdefault(d, set()).add(r.get('st')); states.setdefault(d2, set()).add(r.get('st'))
    # keep weeks with a full set of reporting states (>= 50) so partial latest weeks do not print as collapses
    full = {d for d, s in states.items() if len(s) >= 50}
    write_series(os.path.join(outdir, 'ar539_initial_claims_sum_states_weekly.csv'), {d: v for d, v in ic.items() if d in full})
    write_series(os.path.join(outdir, 'ar539_continued_weeks_claimed_sum_states_weekly.csv'), {d: v for d, v in cw.items() if d in full})

def derive_xls_try(spec, raw, outdir):
    try:
        import pandas as pd
        df = pd.read_excel(raw)
        cols = list(df.columns); log('  xls parsed with pandas', os.path.basename(raw), df.shape, cols[:8])
        dc = spec.get('date_col') or cols[0]
        for col, name in spec.get('value_cols', {}).items():
            if col in df.columns:
                pairs = [(to_iso(str(d)), v) for d, v in zip(df[dc], df[col]) if to_iso(str(d)) and v == v]
                write_series(os.path.join(outdir, name + '.csv'), pairs)
    except Exception as e:
        log('  xls not parsed (kept raw):', os.path.basename(raw), type(e).__name__, str(e)[:100])

DERIVERS = {'columns': derive_columns, 'ymd': derive_ymd, 'bfs_wide': derive_bfs_wide, 'ar539': derive_ar539, 'xls_try': derive_xls_try}

# ------------------------------------------------------------------ GitHub-listed CSV repos (Indeed, Opportunity Insights)
def job_github(job):
    for repo in job['repos']:
        d = os.path.join(WH, repo['dir']); max_b = repo.get('max_mb', 100) * 1000000
        base = 'https://api.github.com/repos/%s/contents/%s' % (repo['repo'], repo.get('path', ''))
        items = http_json(base, headers={'Accept': 'application/vnd.github+json'})
        if not isinstance(items, list): log('  listing failed', repo['repo'], repo.get('path', ''), 'code', LAST_CODE[0]); continue
        write_json(os.path.join(d, '_listing.json'), items)
        if repo.get('recurse'):
            extra = []
            for it in items:
                if it.get('type') == 'dir':
                    sub = http_json(it['url'], headers={'Accept': 'application/vnd.github+json'})
                    if isinstance(sub, list): extra += sub
                    time.sleep(0.5)
            items += extra
        got = skipped = 0
        for it in items:
            if it.get('type') != 'file': continue
            name = it['name']
            if not name.lower().endswith(tuple(repo.get('ext', ['.csv']))): continue
            if it.get('size', 0) > max_b: log('  skip (size)', it['path'], it.get('size')); continue
            out = os.path.join(d, it['path'].replace('/', '__'))
            shaf = out + '.sha'
            if not FORCE and os.path.exists(out) and os.path.exists(shaf) and open(shaf).read().strip() == it.get('sha', ''):
                skipped += 1; continue
            b = http_get(it['download_url'], timeout=600)
            if b is None: continue
            write_bytes(out, b); write_text(shaf, it.get('sha', '')); got += 1
            time.sleep(0.3)
        log('  github', repo['repo'], repo.get('path', ''), 'fetched', got, 'unchanged', skipped)

# ------------------------------------------------------------------ TSA
def parse_tsa(h):
    rows = {}
    for t in html_tables(h):
        for cells in t:
            if len(cells) >= 2 and re.fullmatch(r'\d{1,2}/\d{1,2}/\d{4}', cells[0]):
                v = cells[1].replace(',', '')
                if v.isdigit(): rows[to_iso(cells[0])] = int(v)
    return rows

def job_tsa(job):
    d = os.path.join(WH, 'tsa'); out = os.path.join(d, 'tsa_throughput_daily.csv')
    rows = {}
    seed = os.path.join(DATA_ROOT, job.get('seed', ''))
    if job.get('seed') and os.path.exists(seed):
        for r in read_csv_rows(seed):
            if to_iso(r.get('date')) and num(r.get('passengers')) is not None: rows[to_iso(r['date'])] = int(float(r['passengers']))
    for k, v in read_series(out).items(): rows[k] = int(float(v))
    yr = date.today().year
    pages = [(job['url'], 'current')] + [(job['url'] + '/%d' % y, str(y)) for y in range(job.get('first_year', 2019), yr)]
    for u, name in pages:
        raw = os.path.join(d, 'raw', 'passenger-volumes_%s.html.gz' % name)
        if name.isdigit() and int(name) < yr and os.path.exists(raw):
            h = gzip.open(raw, 'rt', encoding='utf-8', errors='replace').read()
        elif fresh(raw):
            h = gzip.open(raw, 'rt', encoding='utf-8', errors='replace').read()
        else:
            b = http_get(u, headers={'Accept': 'text/html'})
            h = b.decode(errors='replace') if b else None
            if h is None and LAST_CODE[0] in (403, 429, None):
                h = nimble_fetch(u, render=False); log('  tsa via nimble', name, 'ok' if h else 'failed')
            if h is None: log('  tsa page failed', name, 'code', LAST_CODE[0]); continue
            write_text(raw, h)
        got = parse_tsa(h); rows.update(got); log('  tsa', name, len(got), 'rows')
    write_series(out, rows)

# ------------------------------------------------------------------ NY Fed markets API
def job_nyfed(job):
    d = os.path.join(WH, 'nyfed')
    raw = os.path.join(d, 'rates_all.json.gz')
    if not fresh(raw):
        b = http_get(job['rates_url'])
        if b: write_bytes(raw, b); log('  rates_all', len(b), 'bytes')
    if os.path.exists(raw):
        js = json.load(gzip.open(raw, 'rt'))
        by = {}
        for r in js.get('refRates', []):
            by.setdefault(r.get('type'), []).append(r)
        allrows = []
        for t, rs in sorted(by.items()):
            write_series(os.path.join(d, 'derived', '%s_rate.csv' % t), [(r['effectiveDate'], r.get('percentRate')) for r in rs if r.get('percentRate') is not None])
            if t == 'SOFRAI': write_series(os.path.join(d, 'derived', 'SOFR_index.csv'), [(r['effectiveDate'], r.get('index')) for r in rs if r.get('index') is not None])
            vol = [(r['effectiveDate'], r.get('volumeInBillions')) for r in rs if r.get('volumeInBillions') is not None]
            if vol: write_series(os.path.join(d, 'derived', '%s_volume_bn.csv' % t), vol)
            for r in rs: allrows.append([r.get('effectiveDate'), t, r.get('percentRate'), r.get('volumeInBillions'), r.get('percentPercentile1'), r.get('percentPercentile25'), r.get('percentPercentile75'), r.get('percentPercentile99'), r.get('targetRateFrom'), r.get('targetRateTo'), r.get('average30day'), r.get('average90day'), r.get('average180day'), r.get('index'), r.get('revisionIndicator')])
        allrows.sort(key=lambda x: (x[0] or '', x[1] or ''))
        write_csv(os.path.join(d, 'rates_all.csv'), ['date', 'type', 'rate', 'volume_bn', 'p1', 'p25', 'p75', 'p99', 'target_from', 'target_to', 'avg30', 'avg90', 'avg180', 'index', 'revision'], allrows)
    # repo / reverse repo operations, one JSON per year
    yr = date.today().year; ops = []
    for y in range(job.get('rp_first_year', 2013), yr + 1):
        f = os.path.join(d, 'rp', 'rp_results_%d.json.gz' % y)
        if not os.path.exists(f) or y >= yr - 1 and not fresh(f) or FORCE:
            js = http_json(job['rp_url'] % (y, y))
            if js is not None: write_bytes(f, json.dumps(js).encode()); log('  rp', y, len(js.get('repo', {}).get('operations', [])), 'ops')
        if os.path.exists(f):
            try: ops += json.load(gzip.open(f, 'rt')).get('repo', {}).get('operations', [])
            except Exception as e: log('  rp bad file', f, type(e).__name__)
        time.sleep(0.5)
    rows = []; onrrp = {}; onrp = {}
    for o in ops:
        dets = {x.get('securityType', ''): x for x in o.get('details', [])}
        rows.append([o.get('operationDate'), o.get('operationType'), o.get('operationMethod'), o.get('term'), o.get('termCalenderDays'), o.get('settlementDate'), o.get('maturityDate'), o.get('totalAmtSubmitted'), o.get('totalAmtAccepted'), o.get('participatingCpty'), o.get('acceptedCpty'), o.get('auctionStatus'),
                     dets.get('Treasury', {}).get('amtAccepted'), dets.get('Agency', {}).get('amtAccepted'), dets.get('Mortgage-Backed', {}).get('amtAccepted'), dets.get('Treasury', {}).get('percentOfferingRate'), dets.get('Treasury', {}).get('percentAwardRate'), o.get('operationId')])
        if o.get('auctionStatus', 'Results') != 'Results': continue
        if 'Reverse' in (o.get('operationType') or '') and (o.get('termCalenderDays') in (1, 3, 4) or o.get('term') == 'Overnight'):
            onrrp[o['operationDate']] = onrrp.get(o['operationDate'], 0.0) + (o.get('totalAmtAccepted') or 0)
        elif 'Reverse' not in (o.get('operationType') or '') and (o.get('term') == 'Overnight'):
            onrp[o['operationDate']] = onrp.get(o['operationDate'], 0.0) + (o.get('totalAmtAccepted') or 0)
    rows.sort(key=lambda r: (r[0] or '', r[-1] or ''))
    write_csv(os.path.join(d, 'rp_operations.csv'), ['operation_date', 'type', 'method', 'term', 'term_days', 'settlement', 'maturity', 'submitted', 'accepted', 'participating_cpty', 'accepted_cpty', 'status', 'tsy_accepted', 'agency_accepted', 'mbs_accepted', 'tsy_offering_rate', 'tsy_award_rate', 'operation_id'], rows)
    write_series(os.path.join(d, 'derived', 'ON_RRP_accepted_daily.csv'), {k: v / 1e9 for k, v in onrrp.items()})
    write_series(os.path.join(d, 'derived', 'ON_RP_accepted_daily.csv'), {k: v / 1e9 for k, v in onrp.items()})
    log('  rp operations', len(rows))

# ------------------------------------------------------------------ Fedwire / FedACH tables (HTML)
def _period_key(cell, freq):
    c = cell.strip()
    m = re.match(r'^(\d{4})\s*:?\s*([A-Za-z]+)?\s*(Q[1-4])?', c)
    if not m: return None
    y = m.group(1)
    if freq == 'annual':
        return '%s-01-01' % y if re.match(r'^\d{4}\d?$', c) or re.match(r'^\d{4}\D', c) else None
    if freq == 'quarterly':
        q = re.search(r'Q([1-4])', c)
        return '%s-%02d-01' % (y, 3 * int(q.group(1)) - 2) if q else None
    if freq == 'monthly':
        mo = (m.group(2) or '').lower()
        mo = MONTHS.get(mo) or MONTHS.get(mo[:3])
        return '%s-%02d-01' % (y, mo) if mo else None

def job_fedwire(job):
    d = os.path.join(WH, 'fedwire')
    for p in job['pages']:
        raw = os.path.join(d, 'raw', p['name'] + '.html.gz')
        if not fresh(raw):
            b = http_get(p['url'], headers={'Accept': 'text/html'})
            if b is None: log('  page failed', p['name'], 'code', LAST_CODE[0]); continue
            write_bytes(raw, b)
        h = gzip.open(raw, 'rt', encoding='utf-8', errors='replace').read()
        tables = html_tables(h)
        if not tables: log('  no table', p['name']); continue
        rows = max(tables, key=len)
        write_csv(os.path.join(d, p['name'] + '.csv'), ['period'] + ['col%d' % i for i in range(1, max(len(r) for r in rows))], [r for r in rows if r])
        series = {k: {} for k in p['cols']}
        for r in rows:
            k = _period_key(r[0], p['freq'])
            if not k: continue
            for name, idx in p['cols'].items():
                if idx < len(r) and num(r[idx]) is not None: series[name][k] = num(r[idx])
        for name, s in series.items():
            write_series(os.path.join(d, 'derived', '%s_%s_%s.csv' % (p['prefix'], name, p['freq'])), s)

# ------------------------------------------------------------------ Port of Los Angeles monthly TEUs (one HTML table per year)
def job_pola(job):
    d = os.path.join(WH, 'ports', 'port_of_los_angeles'); yr = date.today().year
    cols = {'Loaded Imports': 'loaded_imports', 'Empty Imports': 'empty_imports', 'Total Imports': 'total_imports', 'Loaded Exports': 'loaded_exports',
            'Empty Exports': 'empty_exports', 'Total Exports': 'total_exports', 'Total TEUs': 'total_teus'}
    series = {v: {} for v in cols.values()}; long = []
    for y in range(job.get('first_year', 1995), yr + 1):
        raw = os.path.join(d, 'raw', 'teu_%d.html.gz' % y)
        if FORCE or not os.path.exists(raw) or (y >= yr - 1 and not fresh(raw)):
            b = http_get(job['url'] % y, headers={'Accept': 'text/html'})
            if b is None: log('  pola page failed', y, 'code', LAST_CODE[0]); continue
            write_bytes(raw, b); time.sleep(0.5)
        h = gzip.open(raw, 'rt', encoding='utf-8', errors='replace').read()
        for t in html_tables(h):
            hdr = next((r for r in t if 'Loaded Imports' in r), None)
            if not hdr: continue
            ix = {cols[c]: i for i, c in enumerate(hdr) if c in cols}
            for r in t:
                mo = MONTHS.get(r[0].strip().lower()) if r else None
                if not mo or len(r) < 3: continue
                dt = '%d-%02d-01' % (y, mo); rec = {'date': dt}
                for name, i in ix.items():
                    v = num(r[i]) if i < len(r) else None
                    if v is not None: series[name][dt] = v; rec[name] = v
                if len(rec) > 1: long.append(rec)
    for name, sr in series.items():
        write_series(os.path.join(d, 'derived', 'pola_%s_monthly.csv' % name), sr, quiet=name != 'total_teus')
    keys = ['date'] + list(cols.values())
    long.sort(key=lambda r: r['date'])
    write_csv(os.path.join(d, 'pola_monthly_teu.csv'), keys, [[r.get(k) for k in keys] for r in long])
    log('  pola months', len(long))

# ------------------------------------------------------------------ TreasuryDirect auctions
TD_COLS = ['cusip', 'securityType', 'securityTerm', 'type', 'term', 'auctionDate', 'issueDate', 'maturityDate', 'offeringAmount', 'totalAccepted', 'totalTendered', 'bidToCoverRatio', 'highYield', 'highDiscountRate', 'highInvestmentRate', 'highPrice', 'highDiscountMargin', 'interestRate', 'averageMedianYield', 'lowYield', 'allocationPercentage', 'competitiveAccepted', 'competitiveTendered', 'noncompetitiveAccepted', 'primaryDealerAccepted', 'primaryDealerTendered', 'directBidderAccepted', 'directBidderTendered', 'indirectBidderAccepted', 'indirectBidderTendered', 'somaAccepted', 'somaTendered', 'fimaNoncompetitiveAccepted', 'reopening', 'cashManagementBillCMB', 'tips', 'floatingRate']

def job_treasurydirect(job):
    d = os.path.join(WH, 'treasurydirect'); yr = date.today().year; recs = []
    b = http_get(job['auctioned_url'])
    if b: write_bytes(os.path.join(d, 'auctioned_latest.json.gz'), b)
    for y in range(job.get('first_year', 1979), yr + 1):
        f = os.path.join(d, 'raw', 'auctions_%d.json.gz' % y)
        if FORCE or not os.path.exists(f) or (y >= yr - 1 and not fresh(f)):
            js = http_json(job['search_url'] % (y, y), timeout=300)
            if js is not None: write_bytes(f, json.dumps(js).encode()); log('  auctions', y, len(js))
            time.sleep(0.5)
        if os.path.exists(f):
            try: recs += json.load(gzip.open(f, 'rt'))
            except Exception as e: log('  bad file', f, type(e).__name__)
    def share(a, b):
        a, b = num(a), num(b)
        return round(a / b, 4) if a is not None and b else None
    rows = []
    for r in recs:
        row = [r.get(c) for c in TD_COLS]
        row += [share(r.get('primaryDealerAccepted'), r.get('competitiveAccepted')), share(r.get('directBidderAccepted'), r.get('competitiveAccepted')), share(r.get('indirectBidderAccepted'), r.get('competitiveAccepted'))]
        rows.append(row)
    rows.sort(key=lambda x: (x[5] or '', x[0] or ''))
    write_csv(os.path.join(d, 'auctions.csv'), TD_COLS + ['dealer_share', 'direct_share', 'indirect_share'], rows)
    log('  auctions total', len(rows), rows[0][5][:10] if rows else '', '->', rows[-1][5][:10] if rows else '')
    # derived: bid-to-cover by security type (daily, mean when several auctions of a type on a day)
    btc = {}
    for r in recs:
        v = num(r.get('bidToCoverRatio')); dt = (r.get('auctionDate') or '')[:10]; t = (r.get('securityType') or '').replace(' ', '_')
        if v is None or not dt or not t: continue
        btc.setdefault(t, {}).setdefault(dt, []).append(v)
    for t, s in btc.items():
        write_series(os.path.join(d, 'derived', 'bid_to_cover_%s_daily.csv' % t), {k: sum(v) / len(v) for k, v in s.items()}, quiet=True)
    log('  bid-to-cover series', sorted(btc))

# ------------------------------------------------------------------ FEMA
def job_fema(job):
    d = os.path.join(WH, 'fema'); raw = os.path.join(d, 'DisasterDeclarationsSummaries.csv.gz')
    if not fresh(raw):
        rows = []; skip = 0; cols = None
        while True:
            js = http_json(job['url'] % skip, timeout=300)
            if js is None: break
            page = js.get('DisasterDeclarationsSummaries', [])
            if cols is None and page: cols = list(page[0].keys())
            rows += page; skip += job.get('page', 10000)
            log('  fema', len(rows))
            if len(page) < job.get('page', 10000): break
            time.sleep(0.5)
        if rows and cols:
            write_csv(raw, cols, [[r.get(c) for c in cols] for r in rows])
    if not os.path.exists(raw): return
    rows = read_csv_rows(raw)
    dis = {}; areas = {}
    for r in rows:
        dt = (r.get('declarationDate') or '')[:10]
        if not dt: continue
        dis.setdefault(dt, set()).add(r.get('disasterNumber')); areas[dt] = areas.get(dt, 0) + 1
    if dis:
        d0, d1 = min(dis), max(dis); cur = date.fromisoformat(d0); end = date.fromisoformat(d1)
        cnt, ar = {}, {}
        while cur <= end:
            k = cur.isoformat(); cnt[k] = len(dis.get(k, ())); ar[k] = areas.get(k, 0); cur += timedelta(days=1)
        write_series(os.path.join(d, 'derived', 'fema_disaster_declarations_daily_count.csv'), cnt)
        write_series(os.path.join(d, 'derived', 'fema_declared_areas_daily_count.csv'), ar)
        write_series(os.path.join(d, 'derived', 'fema_disaster_declarations_28d_sum.csv'), rolling_sum({k: float(v) for k, v in cnt.items()}, 28))

# ------------------------------------------------------------------ CDC
def epiweek_end(ew):
    y, w = divmod(int(ew), 100)
    jan4 = date(y, 1, 4); sun = jan4 - timedelta(days=(jan4.weekday() + 1) % 7)
    return (sun + timedelta(days=6 + 7 * (w - 1))).isoformat()

def job_cdc(job):
    d = os.path.join(WH, 'cdc')
    raw = os.path.join(d, 'fluview_ilinet_nat.json.gz')
    if not fresh(raw):
        b = http_get(job['fluview_url'])
        if b: write_bytes(raw, b)
    if os.path.exists(raw):
        js = json.load(gzip.open(raw, 'rt')); ep = js.get('epidata', [])
        wili = {epiweek_end(r['epiweek']): r['wili'] for r in ep if r.get('wili') is not None}
        ili = {epiweek_end(r['epiweek']): r['ili'] for r in ep if r.get('ili') is not None}
        write_csv(os.path.join(d, 'fluview_ilinet_nat_weekly.csv'), ['week_end', 'epiweek', 'wili', 'ili', 'num_ili', 'num_patients', 'num_providers', 'release_date'], [[epiweek_end(r['epiweek']), r['epiweek'], r.get('wili'), r.get('ili'), r.get('num_ili'), r.get('num_patients'), r.get('num_providers'), r.get('release_date')] for r in ep])
        write_series(os.path.join(d, 'derived', 'ilinet_nat_weighted_ili_weekly.csv'), wili)
        write_series(os.path.join(d, 'derived', 'ilinet_nat_unweighted_ili_weekly.csv'), ili)
    nw = os.path.join(d, 'nwss_wastewater_2ew6-ywp6.csv.gz')
    if not fresh(nw, job.get('nwss_fresh_hours', 20 * 7)):
        http_stream_gz(job['nwss_url'], nw, timeout=1800)
    if os.path.exists(nw) and not fresh(os.path.join(d, 'derived', 'nwss_mean_percentile_daily.csv'), 20 * 7) or FORCE:
        try:
            pct, ptc, n = {}, {}, {}
            with gzip.open(nw, 'rt', newline='', encoding='utf-8', errors='replace') as f:
                for r in csv.DictReader(f):
                    dt = (r.get('date_end') or '')[:10]
                    if not dt: continue
                    a, b = num(r.get('percentile')), num(r.get('ptc_15d'))
                    if a is not None and 0 <= a <= 100: pct[dt] = pct.get(dt, 0.0) + a; n[dt] = n.get(dt, 0) + 1
                    if b is not None: ptc.setdefault(dt, []).append(b)
            write_series(os.path.join(d, 'derived', 'nwss_mean_percentile_daily.csv'), {k: pct[k] / n[k] for k in pct if n[k] >= 20})
            write_series(os.path.join(d, 'derived', 'nwss_mean_ptc_15d_daily.csv'), {k: sum(v) / len(v) for k, v in ptc.items() if len(v) >= 20})
            write_series(os.path.join(d, 'derived', 'nwss_sites_reporting_daily.csv'), {k: v for k, v in n.items()})
        except Exception as e: log('  nwss derive EXC', type(e).__name__, str(e)[:120])

# ------------------------------------------------------------------ Daily Treasury Statement
def fiscal_pages(base, params, fields, page=10000, log_every=10, timeout=300):
    rows = []; p = 1
    while True:
        q = dict(params); q.update({'page[size]': page, 'page[number]': p})
        js = http_json(base + '?' + urllib.parse.urlencode(q), timeout=timeout)
        if js is None: return None
        rows += [[r.get(c) for c in fields] for r in js.get('data', [])]
        pages = int(js.get('meta', {}).get('total-pages', 1) or 1)
        if p % log_every == 0: log('   page', p, 'of', pages, len(rows))
        if p >= pages: break
        p += 1; time.sleep(0.2)
    return rows

def job_dts(job):
    d = os.path.join(WH, 'dts')
    for t in job['tables']:
        raw = os.path.join(d, t['name'] + '.csv.gz')
        if fresh(raw): log('  fresh', t['name']); continue
        rows = fiscal_pages(job['base'] + t['name'], {'sort': 'record_date', 'fields': ','.join(t['fields'])}, t['fields'])
        if rows is None: log('  FAIL', t['name']); continue
        write_csv(raw, t['fields'], rows); log('  ', t['name'], len(rows), 'rows', rows[0][0] if rows else '', '->', rows[-1][0] if rows else '')
    raw = os.path.join(d, 'deposits_withdrawals_operating_cash.csv.gz')
    if not os.path.exists(raw): return
    hdr, rows = read_csv_lists(raw)
    ix = {h: i for i, h in enumerate(hdr)}
    iD, iA, iT, iC, iV = ix['record_date'], ix['account_type'], ix['transaction_type'], ix['transaction_catg'], ix['transaction_today_amt']
    cats = {}
    for r in rows:
        k = (r[iT], r[iA], r[iC])
        c = cats.setdefault(k, [r[iD], r[iD], 0]); c[0] = min(c[0], r[iD]); c[1] = max(c[1], r[iD]); c[2] += 1
    write_csv(os.path.join(d, 'dts_categories.csv'), ['transaction_type', 'account_type', 'transaction_catg', 'first_date', 'last_date', 'n'], [list(k) + v for k, v in sorted(cats.items())])
    log('  dts distinct (type, account, category) triples', len(cats), '-> dts/dts_categories.csv')
    ftd = os.path.join(d, 'federal_tax_deposits.csv.gz'); ftd_rows = []
    if os.path.exists(ftd):
        h4, r4 = read_csv_lists(ftd); j4 = {h: i for i, h in enumerate(h4)}
        ftd_rows = [(r[j4['record_date']], r[j4['tax_deposit_type']] or '', r[j4['tax_deposit_today_amt']]) for r in r4]
    for name, rule in job['derived'].items():
        inc = [re.compile(p, re.I) for p in rule['match']]; exc = [re.compile(p, re.I) for p in rule.get('exclude', [])]
        s = {}; matched = {}
        for pat in rule.get('ftd_match', []):   # legacy Table IV line (federal_tax_deposits, ends 2023-02-13)
            p4 = re.compile(pat, re.I)
            for dt, typ, amt in ftd_rows:
                if p4.search(typ) and num(amt) is not None:
                    s[dt] = s.get(dt, 0.0) + num(amt)
                    m = matched.setdefault('[Table IV] ' + typ, [dt, dt]); m[0] = min(m[0], dt); m[1] = max(m[1], dt)
        for r in rows:
            if r[iT] != rule['type']: continue
            c = r[iC] or ''
            if not any(p.search(c) for p in inc) or any(p.search(c) for p in exc): continue
            v = num(r[iV])
            if v is None: continue
            s[r[iD]] = s.get(r[iD], 0.0) + v
            m = matched.setdefault(c, [r[iD], r[iD]]); m[0] = min(m[0], r[iD]); m[1] = max(m[1], r[iD])
        log('  dts rule', name, 'matched:', ' | '.join('%s [%s..%s]' % (k, v[0], v[1]) for k, v in sorted(matched.items())))
        p_daily = os.path.join(d, 'derived', 'dts_%s_daily.csv' % name)
        try:   # 17 Sep 2026: days a live pull (105/workspace/s2/live_sources.py, hourly) wrote after this raw file's last day stay; a cycle never rolls a series back
            last_raw = rows[-1][iD] if rows else ''
            for k_, v_ in read_series(p_daily).items():
                if k_ > last_raw and k_ not in s and num(v_) is not None: s[k_] = num(v_)
        except Exception: pass
        write_series(p_daily, s)
        write_series(os.path.join(d, 'derived', 'dts_%s_20bd_sum.csv' % name), rolling_sum_bdays(s, 20), quiet=True)
    ocb = os.path.join(d, 'operating_cash_balance.csv.gz')
    if os.path.exists(ocb):
        h2, r2 = read_csv_lists(ocb); j = {h: i for i, h in enumerate(h2)}
        pat = re.compile(job.get('tga_match', r'^Federal Reserve Account$|^Treasury General Account \(TGA\)( Closing Balance)?$'), re.I)
        skip = re.compile(r'Opening Balance|Total TGA|Closing Balance', re.I)
        s = {}; tot = {}; names = set()
        for r in r2:
            a = r[j['account_type']] or ''; names.add(a); dt = r[j['record_date']]
            v = num(r[j['open_today_bal']]) if 'Closing Balance' in a else num(r[j['close_today_bal']])
            if v is None: continue
            if pat.search(a): s[dt] = v
            if not skip.search(a) or 'Closing Balance' in a: tot[dt] = tot.get(dt, 0.0) + v
        log('  dts operating cash balance account types:', ' | '.join(sorted(names)))
        write_series(os.path.join(d, 'derived', 'dts_tga_closing_balance_daily.csv'), s)
        write_series(os.path.join(d, 'derived', 'dts_total_operating_balance_daily.csv'), tot)

def rolling_sum_bdays(series, n):
    """Sum of the last n observations (business days as published), keyed by the last date."""
    ks = sorted(series); out = {}
    for i in range(n - 1, len(ks)):
        out[ks[i]] = sum(series[k] for k in ks[i - n + 1:i + 1])
    return out

# ------------------------------------------------------------------ EIA API v2
def eia_pages(route, params, fields, start=None, page=5000, log_every=20):
    k = key('EIA_API_KEY')
    if not k: log('  eia: no key'); return None
    rows = []; off = 0
    while True:
        q = [('api_key', k), ('data[0]', 'value'), ('length', page), ('offset', off)] + list(params)
        if start: q.append(('start', start))
        js = http_json('https://api.eia.gov/v2/%s/data/?%s' % (route, urllib.parse.urlencode(q)), timeout=300)
        if js is None: return None
        if 'error' in js: log('  eia error', route, str(js.get('error'))[:200]); return None
        resp = js.get('response', {}); chunk = resp.get('data', [])
        rows += [[r.get(f) for f in fields] for r in chunk]; off += page
        if (off // page) % log_every == 0: log('   eia', route, len(rows), 'of', resp.get('total'))
        if len(chunk) < page: break
        time.sleep(0.25)
    return rows

def eia_facet_ids(route, facet):
    k = key('EIA_API_KEY')
    js = http_json('https://api.eia.gov/v2/%s/facet/%s?api_key=%s' % (route, facet, k), timeout=120)
    if not js: return None
    return sorted(f['id'] for f in js.get('response', {}).get('facets', []) if f.get('id'))

def eia_route_job(d, name, route, params, fields, keyf, inc_days, per_series_dir=None, series_idx=1, split=None):
    """Fetch a whole EIA route (paginated), incremental after the first full pull. Rows are lists in `fields` order.
    split=('respondent', 'facets[respondent][]') fetches one facet value at a time (deep offsets are slow on the EIA API)."""
    raw = os.path.join(d, name + '.csv.gz')
    old = read_csv_lists(raw)[1] if os.path.exists(raw) else []
    if fresh(raw): log('  fresh', name)
    else:
        start = None
        if old and not FORCE:
            last = max(r[0] for r in old)
            start = (date.fromisoformat(last[:10]) - timedelta(days=inc_days)).isoformat()
            if len(last) == 7: start = start[:7]
        if split:
            ids = eia_facet_ids(route, split[0]); new = [] if ids else None
            for i, fid in enumerate(ids or []):
                part = eia_pages(route, list(params) + [(split[1], fid)], fields, start=start, log_every=1000)
                if part is None: log('   eia', route, split[0], fid, 'FAILED'); continue
                new += part
                if (i + 1) % 10 == 0: log('   eia', route, i + 1, 'of', len(ids), split[0] + 's', len(new), 'rows')
        else:
            new = eia_pages(route, params, fields, start=start)
        if new is None: log('  FAIL', name)
        else:
            rows = ([r for r in old if r[0] < start] if start else []) + new
            rows.sort(key=keyf)
            write_csv(raw, fields, rows); old = rows
            log('  ', name, len(rows), 'rows', 'fetched', len(new), 'from', start or 'origin', rows[0][0] if rows else '', '->', rows[-1][0] if rows else '')
    if per_series_dir and old:
        by = {}
        for r in old:
            if num(r[2]) is not None: by.setdefault(r[series_idx], {})[r[0]] = r[2]
        for sid, v in by.items():
            write_series(os.path.join(per_series_dir, re.sub(r'[^A-Za-z0-9_.-]', '_', sid) + '.csv'), v, quiet=True)
        log('  ', name, 'per-series files', len(by))
    return old

def job_eia(job):
    d = os.path.join(WH, 'eia')
    srt = [('sort[0][column]', 'period'), ('sort[0][direction]', 'asc'), ('sort[1][column]', 'series'), ('sort[1][direction]', 'asc')]
    rows = eia_route_job(d, 'petroleum_sum_sndw_weekly', 'petroleum/sum/sndw', [('frequency', 'weekly')] + srt,
                         ['period', 'series', 'value', 'series-description', 'units', 'duoarea', 'product', 'process'], lambda r: (r[0], r[1]), 70, os.path.join(d, 'petroleum_sndw'))
    if rows:
        meta = {r[1]: r[3:] for r in rows}
        write_csv(os.path.join(d, 'petroleum_sndw_series.csv'), ['series', 'description', 'units', 'duoarea', 'product', 'process'], [[k] + list(v) for k, v in sorted(meta.items())])
    rows = eia_route_job(d, 'natural_gas_stor_wkly', 'natural-gas/stor/wkly', [('frequency', 'weekly')] + srt,
                         ['period', 'series', 'value', 'series-description', 'units', 'duoarea', 'process'], lambda r: (r[0], r[1]), 70, os.path.join(d, 'natural_gas_stor_wkly'))
    if rows:
        meta = {r[1]: r[3:] for r in rows}
        write_csv(os.path.join(d, 'natural_gas_stor_wkly_series.csv'), ['series', 'description', 'units', 'duoarea', 'process'], [[k] + list(v) for k, v in sorted(meta.items())])
    rows = eia_route_job(d, 'eia930_daily_region_data_D', 'electricity/rto/daily-region-data',
                         [('frequency', 'daily'), ('facets[type][]', 'D'), ('sort[0][column]', 'period'), ('sort[0][direction]', 'asc'), ('sort[1][column]', 'respondent'), ('sort[1][direction]', 'asc'), ('sort[2][column]', 'timezone'), ('sort[2][direction]', 'asc')],
                         ['period', 'respondent', 'value', 'timezone', 'respondent-name'], lambda r: (r[0], r[1], r[3]), 45, split=('respondent', 'facets[respondent][]'))
    us48 = {}
    if rows:
        by = {}
        for r in rows:
            if num(r[2]) is None: continue
            by.setdefault(r[1], []).append([r[0], r[3], r[2]])
            if r[1] == 'US48' and r[3] == 'Eastern': us48[r[0]] = float(r[2])
        for resp, rs in by.items():
            write_csv(os.path.join(d, 'eia930_daily', re.sub(r'[^A-Za-z0-9_-]', '_', resp) + '_D.csv'), ['date', 'timezone', 'value_mwh'], sorted(rs))
        log('  eia930 respondents', len(by), 'US48 eastern days', len(us48))
        del rows, by
    # backfill 2015-07 -> 2018-12 from the EIA-930 six-month balance files (API has nothing before 2019)
    hourly_path = os.path.join(d, 'eia930_us48_hourly_from_balance_files.csv')
    hourly = {}
    if os.path.exists(hourly_path):
        for r in read_csv_rows(hourly_path): hourly[r['utc_hour_end']] = (float(r['mwh']), int(r['n_bas']))
    for fn in job.get('balance_files', []):
        raw = os.path.join(d, 'eia930_balance', fn + '.csv.gz')
        if not os.path.exists(raw):
            if http_stream_gz(job['balance_base'] + fn + '.csv', raw, timeout=1800) is None: continue
        marker = raw + '.parsed'
        if os.path.exists(marker) and not FORCE: continue
        try:
            n = 0
            with gzip.open(raw, 'rt', newline='', encoding='utf-8', errors='replace') as f:
                rd = csv.DictReader(f)
                for r in rd:
                    v = num(r.get('Demand (MW) (Imputed)'))
                    if v is None: v = num(r.get('Demand (MW) (Adjusted)'))
                    if v is None: v = num(r.get('Demand (MW)'))
                    if v is None: continue
                    u = r.get('UTC Time at End of Hour') or ''
                    m = re.match(r'(\d{1,2})/(\d{1,2})/(\d{4}) (\d{1,2}):\d{2}(?::\d{2})? ?([AP]M)?', u)
                    if not m: continue
                    hh = int(m.group(4)) % 12 + (12 if m.group(5) == 'PM' else 0) if m.group(5) else int(m.group(4))
                    k = '%s-%02d-%02dT%02d' % (m.group(3), int(m.group(1)), int(m.group(2)), hh)
                    a, b = hourly.get(k, (0.0, 0)); hourly[k] = (a + v, b + 1); n += 1
            write_text(marker, TODAY()); log('  parsed balance file', fn, n, 'rows')
        except Exception as e: log('  balance parse EXC', fn, type(e).__name__, str(e)[:120])
    if hourly:
        write_csv(hourly_path, ['utc_hour_end', 'mwh', 'n_bas'], [[k, fmt(v[0]), v[1]] for k, v in sorted(hourly.items())])
        tz = ZoneInfo('America/New_York') if ZoneInfo else None
        days = {}
        for k, (v, nb) in hourly.items():
            t = datetime.strptime(k, '%Y-%m-%dT%H').replace(tzinfo=timezone.utc) - timedelta(minutes=30)
            dl = (t.astimezone(tz) if tz else t - timedelta(hours=5)).date().isoformat()
            a, b = days.get(dl, (0.0, 0)); days[dl] = (a + v, b + 1)
        back = {k: v for k, (v, nh) in days.items() if nh >= 20}
        ov = [back[k] / us48[k] for k in back if k in us48 and us48[k]]
        if ov: log('  balance-file vs API US48 overlap days', len(ov), 'mean ratio %.4f' % (sum(ov) / len(ov)))
        merged = {k: v for k, v in back.items() if k < job.get('api_from', '2019-01-01')}; merged.update(us48)
    else:
        merged = dict(us48)
    if merged:
        write_series(os.path.join(d, 'EIA930DEMAND_US48_daily.csv'), merged)
        write_series(os.path.join(d, 'EIA930DEMAND_US48_daily_7d_sum.csv'), rolling_sum(merged, 7))
        write_series(os.path.join(d, 'EIA930DEMAND_US48_daily_28d_sum.csv'), rolling_sum(merged, 28))

# ------------------------------------------------------------------ Cboe daily put/call JSON (recent days only on the CDN)
def job_cboe_pc(job):
    d = os.path.join(WH, 'cboe', 'pc_daily'); os.makedirs(d, exist_ok=True)
    idx_path = os.path.join(d, '_index.json')
    idx = json.load(open(idx_path)) if os.path.exists(idx_path) else {}
    today = date.today(); n = 0; miss_run = 0; budget = job.get('per_cycle', 500)
    for i in range(0, job.get('max_days_back', 800)):
        dt = (today - timedelta(days=i)).isoformat()
        st = idx.get(dt)
        if st == 'ok' or (st and st != 'ok' and i > 7):
            miss_run = miss_run + 1 if st != 'ok' else 0
            if miss_run > job.get('stop_after_misses', 45): break
            continue
        if (today - timedelta(days=i)).weekday() >= 5: idx[dt] = 'weekend'; continue
        if n >= budget: break
        b = http_get(job['url'] % dt, quiet=True); n += 1
        if b is None:
            idx[dt] = str(LAST_CODE[0]); miss_run += 1
            if miss_run > job.get('stop_after_misses', 45): log('  cboe pc: stopping at', dt, 'after', miss_run, 'consecutive misses'); break
            continue
        try:
            js = json.loads(b); write_json(os.path.join(d, dt + '.json'), js); idx[dt] = 'ok'; miss_run = 0
        except Exception: idx[dt] = 'badjson'
        time.sleep(0.2)
    write_json(idx_path, idx)
    ok = sorted(k for k, v in idx.items() if v == 'ok')
    log('  cboe pc days held', len(ok), ok[0] if ok else '', '->', ok[-1] if ok else '', 'requests', n)
    ratios = {}; vols = {}
    for dt in ok:
        try: js = json.load(open(os.path.join(d, dt + '.json')))
        except Exception: continue
        for r in js.get('ratios', []):
            v = num(r.get('value'))
            if v is not None: ratios.setdefault(r['name'], {})[dt] = v
        for grp in ('SUM OF ALL PRODUCTS', 'INDEX OPTIONS', 'EQUITY OPTIONS', 'EXCHANGE TRADED PRODUCTS'):
            for r in js.get(grp, []):
                if r.get('name') == 'VOLUME':
                    for side in ('call', 'put', 'total'):
                        if r.get(side) is not None: vols.setdefault('%s_%s' % (grp, side), {})[dt] = r[side]
    for name, s in ratios.items():
        write_series(os.path.join(WH, 'cboe', 'derived', 'pc_ratio_' + re.sub(r'[^A-Za-z0-9]+', '_', name).strip('_').lower() + '.csv'), s, quiet=True)
    for name, s in vols.items():
        write_series(os.path.join(WH, 'cboe', 'derived', 'options_volume_' + re.sub(r'[^A-Za-z0-9]+', '_', name).strip('_').lower() + '.csv'), s, quiet=True)
    log('  cboe pc derived ratio series', len(ratios), 'volume series', len(vols))

# ------------------------------------------------------------------ Nimble-only pages (plain HTTP first, Nimble when it fails)
def job_nimble(job):
    d = os.path.join(WH, 'nimble')
    for t in job['targets']:
        raw = os.path.join(d, t['name'] + '.html.gz')
        if fresh(raw, t.get('fresh_hours', 6 * 24)): log('  fresh', t['name']); continue
        h = None
        if not t.get('nimble_only'):
            b = http_get(t['url'], headers={'Accept': 'text/html'}, timeout=45, retries=1)
            if b is not None and len(b) > t.get('min_bytes', 5000): h = b.decode(errors='replace'); how = 'plain'
        if h is None:
            h = nimble_fetch(t['url'], render=t.get('render', True)); how = 'nimble'
        if h is None: log('  FAIL', t['name'], 'code', LAST_CODE[0]); continue
        write_text(raw, h)
        tables = html_tables(h)
        if tables:
            allrows = []
            for i, tb in enumerate(tables):
                for r in tb: allrows.append([i] + r)
            write_csv(os.path.join(d, t['name'] + '_tables.csv'), ['table'] + ['c%d' % i for i in range(max(len(r) for r in allrows) - 1)], allrows)
        blobs = re.findall(r'<script[^>]*type="application/(?:ld\+)?json"[^>]*>(.*?)</script>', h, re.S | re.I)
        state = re.findall(r'(?:__INITIAL_STATE__|__NEXT_DATA__|__PRELOADED_STATE__|window\.__data)\s*=\s*(\{.*?\})\s*;?\s*</script>', h, re.S)
        if blobs or state: write_text(os.path.join(d, t['name'] + '_embedded.json.txt'), '\n\n'.join(blobs + state))
        log('  ', t['name'], how, len(h), 'bytes', 'tables', len(tables), 'json blobs', len(blobs) + len(state))
    # one discovery search, kept for later vetting, never acted on
    out = os.path.join(WH, 'discovery', 'nimble_search_results.json')
    if os.path.exists(out) and not FORCE:
        try:
            if any(r.get('http') == 200 for r in json.load(open(out))): return   # done once; never acted on
        except Exception: pass
    k = key('NIMBLE_API_KEY')
    if not k: return
    results = []
    for q in job.get('search_queries', []):
        for engine in job.get('search_engines', ['google_search', 'bing_search']):
            body = json.dumps({'search_engine': engine, 'query': q, 'country': 'US', 'locale': 'en', 'parse': True}).encode()
            b = http_get(SRC['nimble']['serp_endpoint'], headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + k}, data=body, timeout=120, retries=1)
            results.append({'query': q, 'engine': engine, 'fetched_at': time.strftime('%Y-%m-%d %H:%M:%S'), 'http': LAST_CODE[0], 'response': (json.loads(b) if b and b[:1] in (b'{', b'[') else (b.decode(errors='replace')[:5000] if b else None))})
            time.sleep(1)
            if LAST_CODE[0] == 200: break
    if results: write_json(out, results); log('  discovery search saved', len(results), 'calls; ok:', any(r['http'] == 200 for r in results))

# ------------------------------------------------------------------ FRED bulk + ALFRED vintages
FREQS = ['daily', 'weekly', 'biweekly', 'monthly', 'quarterly']
class Fred:
    """FRED API client: per-key gap (per_key_seconds) plus a global cap (max_rps, all keys together), and an
    IP-block detector: FRED's edge (Akamai) answers 403 Access Denied to every request from an IP that asked
    too fast; on 403 every thread pauses, one probe per block_pause_min minutes, until FRED answers again."""
    def __init__(self):
        self.keys = fred_keys(); self.gap = SRC['fred'].get('per_key_seconds', 0.7)
        self.min_gap = 1.0 / float(SRC['fred'].get('max_rps', 3.0)); self.next_t = 0.0
        self.last = {k: 0.0 for k in self.keys}; self.lk = threading.Lock()
        self.ok = threading.Event(); self.ok.set(); self.blk = threading.Lock()
        if not self.keys: raise RuntimeError('no FRED keys in local.env')
    def _throttle(self, k):
        with self.lk:
            now = time.time()
            wait = max(self.gap - (now - self.last[k]), self.next_t - now, 0.0)
            self.next_t = max(now, self.next_t) + self.min_gap
            self.last[k] = now + wait
        if wait > 0: time.sleep(wait)
    def _blocked(self):
        """Called on 403. The first caller probes until FRED answers; the others wait on the event."""
        if not self.blk.acquire(blocking=False):
            self.ok.wait(); return
        try:
            self.ok.clear(); pause = 60 * SRC['fred'].get('block_pause_min', 10); n = 0
            while True:
                n += 1; log('  FRED 403 Access Denied (IP block) - pausing %.0f min (probe %d)' % (pause / 60, n))
                time.sleep(pause)
                try:
                    u = 'https://api.stlouisfed.org/fred/series?' + urllib.parse.urlencode({'series_id': 'ICSA', 'api_key': self.keys[n % len(self.keys)], 'file_type': 'json'})
                    with urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': UA}), timeout=60) as r: r.read()
                    log('  FRED answers again after %d probe(s)' % n); break
                except urllib.error.HTTPError as e:
                    if e.code != 403: break
                    pause = min(pause * 2, 60 * SRC['fred'].get('block_pause_max_min', 60))
                except Exception:
                    pass
        finally:
            self.ok.set(); self.blk.release()
    def get(self, path, k, **kw):
        kw.update(api_key=k, file_type='json')
        u = 'https://api.stlouisfed.org/fred/' + path + '?' + urllib.parse.urlencode(kw)
        for attempt in range(6):
            self.ok.wait(); self._throttle(k); fred_wait()   # machine-wide gate: the queue collector shares this limit
            try:
                with urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': UA}), timeout=180) as r: return json.load(r)
            except urllib.error.HTTPError as e:
                if e.code == 400: return {'error': 400}
                if e.code == 403: fred_blocked(); self._blocked(); continue
                if e.code == 429: time.sleep(20 + 20 * attempt); continue
                time.sleep(3 + 5 * attempt)
            except Exception:
                time.sleep(3 + 5 * attempt)
        return None

def fred_catalog(fred):
    """Catalog per frequency: copied from collection 189, refreshed from FRED when older than catalog_refresh_days."""
    cat = {}; cd = os.path.join(WH, 'fred_catalog'); os.makedirs(cd, exist_ok=True)
    src = os.path.join(DATA_ROOT, SRC['fred']['catalog_dir'])
    for f in FREQS:
        fn = os.path.join(cd, 'fred_nation_usa_%s.json' % f); old = os.path.join(src, 'fred_nation_usa_%s.json' % f)
        if not os.path.exists(fn) and os.path.exists(old):
            write_bytes(fn, open(old, 'rb').read())
        if not fresh(fn, 24 * SRC['fred'].get('catalog_refresh_days', 30)) or not os.path.exists(fn):
            rows, off, i = [], 0, 0; ok = True
            while True:
                d = fred.get('tags/series', fred.keys[i % len(fred.keys)], tag_names='nation;usa;' + f, limit=1000, offset=off, order_by='series_id'); i += 1
                if not d or 'seriess' not in d: ok = False; break
                rows += d['seriess']; off += 1000
                if off >= d.get('count', 0): break
            if ok and rows: write_json(fn, rows); log('  catalog refreshed', f, len(rows))
            elif os.path.exists(fn): os.utime(fn, None); log('  catalog refresh failed, kept old', f)
        cat[f] = json.load(open(fn)) if os.path.exists(fn) else []
        log('  catalog', f, len(cat[f]))
    return cat

def job_fred_bulk(job):
    fred = Fred(); cat = fred_catalog(fred)
    todo = []; held = 0; fd = SRC['fred'].get('fresh_days', 7)
    for f in FREQS:
        od = os.path.join(WH, 'fred_bulk', f); os.makedirs(od, exist_ok=True)
        for r in cat[f]:
            p = os.path.join(od, r['id'] + '.csv.gz')
            if fresh(p, 24 * fd): held += 1
            else: todo.append((r['id'], p))
    log('  fred bulk: keys', len(fred.keys), 'to fetch', len(todo), 'held', held)
    q = queue.Queue()
    for x in todo: q.put(x)
    done = [0, 0, 0, 0]; t0 = time.time()
    def worker(k):
        while True:
            try: sid, p = q.get_nowait()
            except queue.Empty: return
            d = fred.get('series/observations', k, series_id=sid, limit=100000)
            if d and 'observations' in d:
                obs = [(o['date'], o['value']) for o in d['observations'] if o.get('value') not in (None, '.', '')]
                write_csv(p, ['date', 'value'], obs)
                with fred.lk: done[1] += 1
            elif d and d.get('error') == 400:
                with fred.lk: done[2] += 1
            else:
                with fred.lk: done[3] += 1
            with fred.lk:
                done[0] += 1
                if done[0] % 500 == 0: log('  fred bulk %d/%d written %d bad400 %d failed %d %.1f min' % (done[0], len(todo), done[1], done[2], done[3], (time.time() - t0) / 60))
    nth = min(len(fred.keys), int(SRC['fred'].get('threads', 4)))
    th = [threading.Thread(target=worker, args=(fred.keys[i],), daemon=True) for i in range(nth)]
    for t in th: t.start()
    for t in th: t.join()
    log('  fred bulk done: attempted', done[0], 'written', done[1], 'bad400', done[2], 'failed (retried next cycle)', done[3], '%.1f min' % ((time.time() - t0) / 60))

def obs_all_vintages(fred, k, sid, vdates):
    """Every observation-vintage row of a series. FRED refuses a real-time window that holds more than 2,000 vintage
    dates (every daily series does: 63 series failed on this until 17 Sep 2026). Such a series is asked for in contiguous
    windows of 1,900 vintage dates, and a row that was cut at a window's edge is joined again (same date, same value,
    real-time periods that touch)."""
    def pull(rs, re_):
        rows, off = [], 0
        while True:
            d = fred.get('series/observations', k, series_id=sid, realtime_start=rs, realtime_end=re_, output_type=1, limit=100000, offset=off)
            if not d or 'observations' not in d: return None
            rows += d['observations']; off += 100000
            if off >= d.get('count', 0): return rows
    if len(vdates) <= 2000: return pull('1776-07-04', '9999-12-31')
    out = []; n = 1900
    for i in range(0, len(vdates), n):
        rs = '1776-07-04' if i == 0 else vdates[i]
        re_ = '9999-12-31' if i + n >= len(vdates) else (date.fromisoformat(vdates[i + n]) - timedelta(days=1)).isoformat()
        r = pull(rs, re_)
        if r is None: return None
        out += r
    out.sort(key=lambda o: (o['date'], o['realtime_start']))
    merged = []
    for o in out:
        p = merged[-1] if merged else None
        if (p and p['date'] == o['date'] and p['value'] == o['value'] and p['realtime_end'] != '9999-12-31'
                and date.fromisoformat(o['realtime_start']) == date.fromisoformat(p['realtime_end']) + timedelta(days=1)):
            p['realtime_end'] = o['realtime_end']
        else: merged.append(dict(o))
    return merged

def job_fred_vintages(job):
    fred = Fred(); vd = os.path.join(WH, 'fred_vintages'); os.makedirs(vd, exist_ok=True)
    src = os.path.join(DATA_ROOT, SRC['fred']['leg_series'])
    ids = sorted(set(open(src).read().split())) if os.path.exists(src) else []
    write_text(os.path.join(vd, '_leg_series.txt'), '\n'.join(ids))
    fd = SRC['fred'].get('vintage_fresh_days', 14)
    todo = [s for s in ids if not fresh(os.path.join(vd, s + '.csv.gz'), 24 * fd)]
    log('  fred vintages: series', len(ids), 'to fetch', len(todo))
    q = queue.Queue()
    for s in todo: q.put(s)
    done = [0]; t0 = time.time()
    def worker(k):
        while True:
            try: sid = q.get_nowait()
            except queue.Empty: return
            vdd = fred.get('series/vintagedates', k, series_id=sid, limit=10000)
            if not vdd or 'vintage_dates' not in vdd:
                log('  vintages', sid, 'no vintage dates', (vdd or {}).get('error', ''))
                with fred.lk: done[0] += 1
                continue
            rows = obs_all_vintages(fred, k, sid, vdd['vintage_dates'])
            if rows is None: log('  vintages', sid, 'failed')
            else:
                write_csv(os.path.join(vd, sid + '.csv.gz'), ['realtime_start', 'realtime_end', 'date', 'value'], [[o['realtime_start'], o['realtime_end'], o['date'], o['value']] for o in rows])
                write_json(os.path.join(vd, sid + '.vintagedates.json'), vdd['vintage_dates'])
            with fred.lk:
                done[0] += 1
                if done[0] % 100 == 0: log('  fred vintages %d/%d %.1f min' % (done[0], len(todo), (time.time() - t0) / 60))
    th = [threading.Thread(target=worker, args=(k,), daemon=True) for k in fred.keys[:min(len(fred.keys), int(SRC['fred'].get('threads', 4)))]]
    for t in th: t.start()
    for t in th: t.join()
    log('  fred vintages done', done[0], '%.1f min' % ((time.time() - t0) / 60))

# ------------------------------------------------------------------ registry / driver

def job_page_links(job):
    """For data files whose address changes (it carries a date or a month): fetch the page, take the links matching a
    pattern, download the match (first, last or all). Each dated file is kept, so weekly files accumulate as vintages.
    Registry: pages = [{page, pattern, out_prefix, take: first|last|all, nimble, render, fresh_hours}]. Added 17 Sep 2026."""
    d = os.path.join(WH, job['dir'])
    for p in job['pages']:
        marker = os.path.join(d, p['out_prefix'] + '.lastfetch')
        if fresh(marker, p.get('fresh_hours')):
            log('  fresh', p['out_prefix']); continue
        if p.get('nimble'):
            h = nimble_fetch(p['page'], render=bool(p.get('render')))
        else:
            b = http_get(p['page']); h = b.decode('utf-8', 'ignore') if b else None
        if not h:
            log('  FAIL page', p['page'][:100]); continue
        seen = []
        for l in re.findall(p['pattern'], h, flags=re.I):
            l = html.unescape(l)
            if l not in seen: seen.append(l)
        if not seen:
            log('  no link matched', p['out_prefix']); continue
        take = seen if p.get('take') == 'all' else [seen[-1] if p.get('take') == 'last' else seen[0]]
        ok = 0
        for l in take:
            u = urllib.parse.urljoin(p['page'], l).replace(' ', '%20')
            base = urllib.parse.unquote(u.split('?')[0].split('/')[-1])
            name = p['out_prefix'] + '__' + re.sub(r'[^A-Za-z0-9._-]', '_', base)[:120]
            out = os.path.join(d, name)
            if os.path.exists(out) and os.path.getsize(out) > 100:
                ok += 1; continue
            b = http_get(u)
            if b is None or len(b) < 100:
                log('  FAIL', name); continue
            write_bytes(out, b); log('  saved', name, len(b), 'bytes'); ok += 1
        if ok: write_text(marker, datetime.now().isoformat())

def job_sec_items(job):
    """SEC EDGAR full-text search: every 8-K that reports a given item number, by filing date. Item 2.05 (costs of exit
    or disposal: the filing a listed company owes within four business days of committing to a layoff or a plant
    closing), 2.06 (material impairments), 1.03 (bankruptcy or receivership), 2.04 (a triggered acceleration of a debt),
    3.01 (notice of delisting). The filing date is public the same day and is never revised, so the counts are
    real time by construction. The item numbering begins 23 Aug 2004. One filing-level file per item, keyed by accession
    number, plus a daily count of original 8-Ks (amendments are kept in the filing file and left out of the count).
    Incremental: a month that closed more than 35 days ago is fetched once; later months are fetched again each run.
    A request budget per run (max_requests) spreads the first backfill over several cycles. The search finds the
    phrase "Item N.NN" and the item list of each hit is then checked, so a filing whose text never prints the phrase
    is missed (declared bound). Added 17 Sep 2026."""
    d = os.path.join(WH, job['dir']); os.makedirs(d, exist_ok=True)
    marker = os.path.join(d, 'sec_items.lastfetch')
    if fresh(marker, job.get('fresh_hours')):
        log('  fresh sec_items'); return
    hdr = ['adsh', 'file_date', 'form', 'items', 'period_ending', 'ciks', 'display_names', 'sics', 'biz_states', 'inc_states']
    budget = int(job.get('max_requests', 700)); today = date.today(); complete = True
    for it in job['items']:
        item = it['item']; tag = item.replace('.', '')
        out = os.path.join(d, 'sec_8k_item%s_filings.csv' % tag)
        donef = os.path.join(d, 'sec_8k_item%s_months_done.txt' % tag)
        rows = {}
        if os.path.exists(out):
            for r in read_csv_rows(out): rows[r['adsh']] = [r.get(k, '') for k in hdr]
        done = set(open(donef).read().split()) if os.path.exists(donef) else set()
        y, m = [int(x) for x in it.get('start', '2004-08').split('-')]
        n0 = len(rows); fetched = 0
        while (y, m) <= (today.year, today.month):
            mkey = '%04d-%02d' % (y, m)
            end = date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1)
            closed = (today - end).days > 35
            if not (closed and mkey in done):
                if budget <= 0:
                    complete = False; break
                frm = 0; okm = True
                while True:
                    u = ('https://efts.sec.gov/LATEST/search-index?q=%s&forms=8-K&dateRange=custom&startdt=%s-01&enddt=%s&from=%d'
                         % (urllib.parse.quote('"Item %s"' % item), mkey, end.isoformat(), frm))
                    j = http_json(u, headers={'Accept': 'application/json'}); budget -= 1; time.sleep(0.25)
                    if not j or 'hits' not in j:
                        okm = False; break
                    hits = j['hits'].get('hits', [])
                    for h in hits:
                        s = h.get('_source', {})
                        if item not in (s.get('items') or []): continue
                        a = s.get('adsh') or h.get('_id', '').split(':')[0]
                        if not a: continue
                        rows[a] = [a, s.get('file_date', ''), s.get('form', ''), ' '.join(s.get('items') or []), s.get('period_ending', '') or '',
                                   ' '.join(s.get('ciks') or []), ' | '.join(s.get('display_names') or []), ' '.join(s.get('sics') or []),
                                   ' '.join(s.get('biz_states') or []), ' '.join(s.get('inc_states') or [])]
                    tot = (j['hits'].get('total') or {}).get('value', 0)
                    frm += 100
                    if not hits or frm >= tot or frm >= 10000 or budget <= 0: break
                if okm and frm < 10000 and (frm >= tot or not hits):
                    fetched += 1
                    if closed: done.add(mkey)
                elif not okm:
                    log('  sec item', item, mkey, 'FAIL (retried next run)'); complete = False
                else:
                    complete = False
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
        allrows = sorted(rows.values(), key=lambda r: (r[1], r[0]))
        write_csv(out, hdr, allrows); write_text(donef, '\n'.join(sorted(done)) + '\n')
        daily = {}
        for r in allrows:
            if r[2] == '8-K' and r[1]: daily[r[1]] = daily.get(r[1], 0) + 1
        write_series(os.path.join(d, 'sec_8k_item%s_daily_count.csv' % tag), daily, quiet=True)
        log('  sec item', item, 'months fetched', fetched, 'filings', len(allrows), '(+%d)' % (len(allrows) - n0), 'budget left', budget)
    if complete: write_text(marker, datetime.now().isoformat())

def job_chicagofed(job):
    """Chicago Fed data products: the labor market indicators (with the real-time unemployment forecast), CARTS weekly
    retail, the CFNAI with its three real-time workbooks, the NFCI with its revisions table, and the survey of economic
    conditions. Each product has a keyless JSON manifest that lists its files (found 17 Sep 2026 behind the script-built
    pages). Every data file (csv, xlsx, xls, json, zip, txt) is saved; when a file's content changes a dated copy is kept
    under vintages/, so a real-time record of each product builds from the first day."""
    d0 = os.path.join(WH, job['dir'])
    for prod in job['products']:
        d = os.path.join(d0, prod); marker = os.path.join(d, '_lastfetch')
        if fresh(marker, job.get('fresh_hours')):
            log('  fresh', prod); continue
        j = http_json(job.get('base', 'https://data.chicagofed.org/cfed-drm-chicago/') + prod)
        urls = [v for v in ((j or {}).get('data') or {}).values() if isinstance(v, str) and v.startswith('http')]
        keep = [u for u in urls if re.search(r'\.(csv|xlsx|xls|json|zip|txt)$', u.split('?')[0], re.I)]
        if not keep:
            log('  FAIL manifest', prod); continue
        n = ch = 0
        for u in keep:
            name = re.sub(r'[^A-Za-z0-9._-]', '_', u.split('?')[0].split('/')[-1])
            b = http_get(u)
            if not b:
                log('  FAIL', prod, name); continue
            out = os.path.join(d, name); n += 1
            old = open(out, 'rb').read() if os.path.exists(out) else None
            if old != b:
                write_bytes(out, b); ch += 1
                write_bytes(os.path.join(d, 'vintages', TODAY() + '__' + name), b)
        log('  chicagofed', prod, 'files', n, 'changed', ch)
        if n: write_text(marker, datetime.now().isoformat())

def job_kalshi(job):
    """Kalshi event contracts (a regulated US exchange; public market data, no key): the daily price of each contract in
    the listed series, e.g. "Will there be a recession in 2026?" settled on the NBER. A price is a market's probability,
    dated the day it traded and never revised: a comparator for the rule, not an input. One CSV per market (daily candles
    from the market's opening), one markets.json per series. A settled market already held is not fetched again."""
    base = 'https://api.elections.kalshi.com/trade-api/v2'
    d0 = os.path.join(WH, job['dir']); marker = os.path.join(d0, '_lastfetch')
    if fresh(marker, job.get('fresh_hours')):
        log('  fresh kalshi'); return
    def ts(x):
        try: return int(datetime.fromisoformat(x.replace('Z', '+00:00')).timestamp())
        except Exception: return None
    nser = 0
    for ser in job['series']:
        d = os.path.join(d0, ser); markets = []; cur = ''
        for _ in range(40):
            j = http_json('%s/markets?series_ticker=%s&limit=200%s' % (base, ser, '&cursor=' + cur if cur else '')); time.sleep(0.25)
            if not j: break
            markets += j.get('markets', []); cur = j.get('cursor') or ''
            if not cur: break
        if not markets:
            log('  kalshi', ser, 'no markets'); continue
        write_json(os.path.join(d, 'markets.json'), markets); nser += 1; nm = 0
        for m in markets:
            t = m.get('ticker'); out = os.path.join(d, re.sub(r'[^A-Za-z0-9._-]', '_', t) + '_daily.csv')
            closed = m.get('status') not in ('active', 'open', 'initialized', 'unopened')
            if closed and os.path.exists(out): continue
            a = ts(m.get('open_time') or '') or 0
            b = min(int(time.time()), (ts(m.get('close_time') or '') or int(time.time())) + 86400)
            rows = []
            while a < b:
                e = min(b, a + 4000 * 86400)
                c = http_json('%s/series/%s/markets/%s/candlesticks?start_ts=%d&end_ts=%d&period_interval=1440' % (base, ser, t, a, e), quiet=True); time.sleep(0.25)
                for k in (c or {}).get('candlesticks', []):
                    pr = k.get('price') or {}
                    rows.append([datetime.fromtimestamp(k['end_period_ts'], timezone.utc).date().isoformat(), pr.get('close_dollars', ''), pr.get('mean_dollars', ''),
                                 (k.get('yes_bid') or {}).get('close_dollars', ''), (k.get('yes_ask') or {}).get('close_dollars', ''), k.get('volume_fp', ''), k.get('open_interest_fp', '')])
                a = e
            if rows:
                write_csv(out, ['date', 'close', 'mean', 'yes_bid_close', 'yes_ask_close', 'volume', 'open_interest'], rows); nm += 1
        log('  kalshi', ser, 'markets', len(markets), 'written', nm)
    if nser: write_text(marker, datetime.now().isoformat())

def job_polymarket(job):
    """Polymarket event contracts (public market data, no key): the daily price of the "Yes" side of every market in the
    events whose address contains one of the listed words (default: recession), open or closed. Closed markets keep their
    history (e.g. "US recession in 2025?", January 2025 to its close), so the record of what a market believed on each
    day of 2022, 2024 and 2025 is recoverable. A comparator for the rule, not an input. A closed market already held is
    not fetched again."""
    d = os.path.join(WH, job['dir']); marker = os.path.join(d, '_lastfetch')
    if fresh(marker, job.get('fresh_hours')):
        log('  fresh polymarket'); return
    events = {}
    for q in job.get('queries', ['recession']):
        j = http_json('https://gamma-api.polymarket.com/public-search?q=%s&limit_per_type=100&events_status=all' % urllib.parse.quote(q)); time.sleep(0.5)
        for e in (j or {}).get('events', []):
            slug = e.get('slug') or ''
            if any(w in slug for w in job.get('slug_words', ['recession'])) and not slug.startswith('what-will'): events[slug] = e
    if not events:
        log('  polymarket: no events'); return
    write_json(os.path.join(d, 'events.json'), list(events.values())); n = 0
    for slug, e in sorted(events.items()):
        for m in e.get('markets') or []:
            try: tok = json.loads(m.get('clobTokenIds') or '[]')[0]
            except Exception: continue
            name = re.sub(r'[^A-Za-z0-9._-]', '_', (m.get('slug') or slug))[:150]
            out = os.path.join(d, name + '_daily.csv')
            if m.get('closed') and os.path.exists(out): continue
            h = http_json('https://clob.polymarket.com/prices-history?market=%s&interval=max&fidelity=1440' % tok, quiet=True); time.sleep(0.4)
            rows = {}
            for k in (h or {}).get('history', []):
                rows[datetime.fromtimestamp(k['t'], timezone.utc).date().isoformat()] = k['p']
            if rows: write_series(out, rows, quiet=True); n += 1
    log('  polymarket events', len(events), 'markets written', n)
    write_text(marker, datetime.now().isoformat())

def _feed_text(x):
    x = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', x or '', flags=re.S)
    return html.unescape(re.sub(r'<[^>]+>', ' ', x)).strip()

def job_feeds(job):
    """First-print archive (17 Sep 2026). Statistical agencies, central banks and trade bodies announce every release in a
    feed (RSS, Atom or RDF). Each feed is read often; every item is written once to index.csv (first seen, published,
    title, link), and the page or PDF it links to is fetched once and kept. What a source said on the day it said it is
    then on disk for good, whatever the source later revises or takes down. No AI: a feed is a list, and a list can be
    walked. Registry: feeds = [{name, url, title_regex (optional: fetch only matching items; all are indexed),
    fetch_links (default true), max_items (default 12 a cycle)}]."""
    d0 = os.path.join(WH, job['dir'])
    for fd in job['feeds']:
        name = fd['name']; d = os.path.join(d0, name); marker = os.path.join(d, '_lastfetch')
        if fresh(marker, fd.get('fresh_hours', job.get('fresh_hours', 3))): continue
        b = http_get(fd['url'], quiet=True, retries=2)
        if not b or b'<' not in b[:300]:
            log('  FAIL feed', name, LAST_CODE[0]); continue
        x = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', b.decode('utf-8', 'ignore'), flags=re.S)
        blocks = [m.group(0) for m in re.finditer(r'<(item|entry)\b.*?</\1>', x, flags=re.S | re.I)]
        if not blocks:
            log('  feed has no items', name); continue
        idx = os.path.join(d, 'index.csv'); hdr = ['first_seen', 'published', 'title', 'link', 'file', 'tries']
        rows = {}
        if os.path.exists(idx):
            for r in read_csv_rows(idx): rows[r['link']] = [r.get(k, '') for k in hdr]
        new = 0
        for blk in blocks:
            t = re.search(r'<title[^>]*>(.*?)</title>', blk, flags=re.S | re.I)
            l = re.search(r'<link[^>]*>\s*(https?://[^<\s]+)\s*</link>', blk, flags=re.I) or re.search(r'<link[^>]*href="([^"]+)"', blk, flags=re.I) \
                or re.search(r'<guid[^>]*>\s*(https?://[^<\s]+)\s*</guid>', blk, flags=re.I)
            p = re.search(r'<(pubDate|dc:date|updated|published)[^>]*>(.*?)</\1>', blk, flags=re.S | re.I)
            if not l: continue
            link = html.unescape(l.group(1).strip())
            if link not in rows:
                rows[link] = [datetime.now().isoformat(timespec='seconds'), _feed_text(p.group(2)) if p else '', _feed_text(t.group(1))[:300] if t else '', link, '', '0']; new += 1
        vd = os.path.join(d, 'feed_vintages'); write_bytes(os.path.join(vd, TODAY() + '__feed.xml.gz'), b)
        got = 0; rx = re.compile(fd['title_regex'], re.I) if fd.get('title_regex') else None
        if fd.get('fetch_links', True):
            for link, r in rows.items():
                if got >= fd.get('max_items', 12): break
                if r[4] or int(r[5] or 0) >= 3: continue
                if rx and not rx.search(r[2]): continue
                r[5] = str(int(r[5] or 0) + 1)
                body = http_get(link, quiet=True, retries=2, timeout=90); time.sleep(0.5)
                if not body or len(body) < 200 or len(body) > 25 * 1048576: continue
                ext = '.pdf' if body[:4] == b'%PDF' else '.html.gz'
                fn = '%s__%s__%s%s' % (r[0][:10], hashlib.sha1(link.encode()).hexdigest()[:10], re.sub(r'[^A-Za-z0-9]+', '-', r[2])[:70].strip('-'), ext)
                write_bytes(os.path.join(d, 'items', fn), body); r[4] = 'items/' + fn; got += 1
        write_csv(idx, hdr, sorted(rows.values()))
        write_text(marker, datetime.now().isoformat())
        log('  feed', name, 'items', len(blocks), 'new', new, 'fetched', got, 'held', sum(1 for r in rows.values() if r[4]))

def http_stream_gz_capped(url, out, cap_bytes, headers=None, timeout=300):
    """Stream into out (.gz) but give up past cap_bytes. Returns bytes, -1 when over the cap, None on failure."""
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tmp = out + '.tmp'; LAST_CODE[0] = None
    h = {'User-Agent': UA, 'Accept': '*/*'}; h.update(headers or {})
    try:
        n = 0
        with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout) as r, gzip.open(tmp, 'wb', compresslevel=5) as f:
            LAST_CODE[0] = r.status
            while True:
                chunk = r.read(1 << 20)
                if not chunk: break
                n += len(chunk)
                if n > cap_bytes: break
                f.write(chunk)
        if n > cap_bytes:
            os.remove(tmp); return -1
        os.replace(tmp, out); return n
    except urllib.error.HTTPError as e:
        LAST_CODE[0] = e.code
    except Exception as e:
        log('  ERR', type(e).__name__, str(e)[:80], redact(url)[:140])
    try: os.remove(tmp)
    except OSError: pass
    return None

def job_nonce_post(job):
    """A file that exists only behind a one-time token. Added 18 September 2026 for Georgia's layoff notices, whose
    table is served by a request carrying a nonce that the page mints afresh each load and that expires. The page is
    read, every token on it is tried in turn, and the first answer that carries records is kept. Written generally
    because several state sites work this way."""
    d = os.path.join(WH, job['dir'])
    for spec in job.get('requests', []):
        out = os.path.join(d, spec['out'])
        if fresh(out, spec.get('fresh_hours', job.get('fresh_hours'))):
            log('  fresh', spec['out']); continue
        page = http_get(spec['page'])
        if not page:
            log('  FAIL page', spec['page'][:90]); continue
        toks = list(dict.fromkeys(re.findall(spec.get('token_pattern', r'nonce["\']?\s*[:=]\s*["\']([a-z0-9]{10})["\']'),
                                             page.decode('utf-8', 'ignore'))))
        got = None
        for t in toks[:8]:
            form = dict(spec.get('form', {})); form[spec.get('token_field', 'nonce')] = t
            body = urllib.parse.urlencode(form).encode()
            b = http_get(spec['endpoint'], data=body, quiet=True,
                         headers={'Content-Type': 'application/x-www-form-urlencoded',
                                  'X-Requested-With': 'XMLHttpRequest', 'Referer': spec['page']})
            if b and spec.get('expect', 'recordsTotal') in b.decode('utf-8', 'ignore')[:4000]:
                got = b; break
        if got is None:
            log('  FAIL', spec['out'], 'no token of', len(toks), 'was accepted'); continue
        write_bytes(out, got); log('  saved', spec['out'], len(got), 'bytes')
        keep_vintage(job, {'out': spec['out']}, out)


def job_state_check(job):
    """Coverage and validation of the state panel (collection 215). Completeness at each series' own cadence,
    duplicate periods, impossible values, freshness against the publisher's rhythm, and whether two sources that
    measure related things agree. Added 18 September 2026; it found on its first run that the insured-rate column of
    the weekly claims file had been read from the wrong field."""
    import subprocess
    base = os.path.join(DATA_ROOT, '215_state_coverage_and_gaps_2026-09-18')
    for script in ('state_coverage.py', 'state_validate.py'):
        p = os.path.join(base, 'code', script)
        if not os.path.exists(p): continue
        try:
            r = subprocess.run([sys.executable, p], capture_output=True, timeout=1800, cwd=base)
            tail = (r.stdout or b'').decode(errors='ignore').strip().split('\n')[-3:]
            for line in tail: log('  ' + line[:160])
        except Exception as e:
            log('  state check EXC', script, type(e).__name__, str(e)[:120])


def job_derive_extra(job):
    """The two-column series the new sources do not publish (see code/derive_extra.py). Added 18 September 2026:
    forty jobs added this week write a row per establishment, county, retailer or notice, and nothing downstream
    reads that shape."""
    import derive_extra
    derive_extra.LOG[0] = log
    derive_extra.main()


def job_discover(job):
    """The collector's own search, across every open-data portal in the country at once (see code/discover.py).

    Added 18 September 2026 after Anthony's judgement that the machine was not searching hard enough. The old sweep
    asked one portal at a time from a list somebody had written; this asks the index that holds all of them, keeps
    what matches, and refuses what a portal only claims is current."""
    import discover
    discover.LOG[0] = log
    held = set()
    for j in SRC['jobs']:
        for f in j.get('files', []):
            m = re.search(r'/resource/([a-z0-9]{4}-[a-z0-9]{4})\.', f['url'])
            if m: held.add(m.group(1))
    try:
        import fetch_engine as _fe
    except Exception:
        _fe = None
    discover.run(WH, held_ids=held, engine=_fe,
                 datasets_per_pass=int(job.get('datasets_per_pass', 40)),
                 mb_per_pass=int(job.get('mb_per_pass', 400)),
                 folder_cap_gib=int(job.get('folder_cap_gib', 30)),
                 stale_years=int(job.get('stale_years', 3)),
                 terms_per_pass=int(job.get('terms_per_pass', 12)))


def job_socrata_sweep(job):
    """Discovery without AI (17 Sep 2026). Most American states, counties and cities publish their data on Socrata
    portals, and one public catalog searches them all. Each cycle a few keywords from the registry's list are searched;
    every dataset whose NAME passes the relevance pattern (and not the exclusion pattern) is written to catalog.csv; then,
    within a budget, datasets not yet held - or changed at the source since they were fetched - are downloaded whole as
    CSV. State weekly claims by county and industry, WARN lists, business filings, tax receipts, caseloads, permits and
    traffic counts arrive this way, from portals no one had to find by hand. Budgets: max_downloads and max_mb a cycle,
    max_dataset_mb each, max_total_gib for the folder. A dated copy is kept when a core labour dataset changes."""
    d = os.path.join(WH, job['dir']); sp = os.path.join(d, 'state.json'); cp = os.path.join(d, 'catalog.csv')
    marker = os.path.join(d, '_lastfetch')
    if fresh(marker, job.get('fresh_hours', 0.9)): return
    try: st = json.load(open(sp))
    except Exception: st = {'kw_pos': 0, 'datasets': {}}
    hdr = ['id', 'domain', 'name', 'updatedAt', 'keyword', 'first_seen', 'permalink', 'description']
    cat = {}
    if os.path.exists(cp):
        for r in read_csv_rows(cp): cat[r['id']] = [r.get(k, '') for k in hdr]
    rel = re.compile(job['relevance_regex'], re.I); neg = re.compile(job.get('exclude_regex', r'$^'), re.I)
    core = re.compile(job.get('core_regex', r'unemploy|jobless|claims|layoff|\bWARN\b'), re.I)
    kws = job['keywords']; k = job.get('keywords_per_cycle', 5); found = 0
    for i in range(k):
        kw = kws[(st['kw_pos'] + i) % len(kws)]
        for off in (0, 100):
            j = http_json('https://api.us.socrata.com/api/catalog/v1?only=datasets&limit=100&offset=%d&q=%s' % (off, urllib.parse.quote(kw)), quiet=True); time.sleep(0.4)
            res = (j or {}).get('results', [])
            for r in res:
                rs = r.get('resource', {}); nm = rs.get('name') or ''; did = rs.get('id')
                if not did or not rel.search(nm) or neg.search(nm): continue
                dom = (r.get('metadata') or {}).get('domain', '')
                if did not in cat: found += 1
                first = cat[did][5] if did in cat else TODAY()
                cat[did] = [did, dom, nm[:200], rs.get('updatedAt', ''), kw, first, r.get('permalink', ''), re.sub(r'\s+', ' ', rs.get('description') or '')[:300]]
            if len(res) < 100: break
    st['kw_pos'] = (st['kw_pos'] + k) % len(kws)
    write_csv(cp, hdr, sorted(cat.values(), key=lambda r: (r[1], r[2])))
    total = sum(v.get('bytes', 0) for v in st['datasets'].values()); ndl = 0; mb = 0.0
    capd = job.get('max_dataset_mb', 60) * 1048576
    order = sorted(cat.values(), key=lambda r: (0 if core.search(r[2]) else 1, r[5]))
    for did, dom, nm, upd, kw, first, perma, desc in order:
        if ndl >= job.get('max_downloads', 25) or mb >= job.get('max_mb', 300) or total > job.get('max_total_gib', 25) * 2**30 or LOW_DISK[0]: break
        s0 = st['datasets'].get(did, {})
        if s0.get('updatedAt') == upd and s0.get('status') in ('ok', 'too_big', 'fail3'): continue
        out = os.path.join(d, 'datasets', re.sub(r'[^A-Za-z0-9.-]', '_', dom), '%s__%s.csv.gz' % (did, re.sub(r'[^A-Za-z0-9]+', '-', nm)[:80].strip('-')))
        n = http_stream_gz_capped('https://%s/api/views/%s/rows.csv?accessType=DOWNLOAD' % (dom, did), out, capd); time.sleep(0.5); ndl += 1
        if n is None:
            f = s0.get('fails', 0) + 1
            st['datasets'][did] = {'updatedAt': upd if f >= 3 else '', 'status': 'fail3' if f >= 3 else 'fail', 'fails': f, 'bytes': s0.get('bytes', 0)}
        elif n == -1:
            st['datasets'][did] = {'updatedAt': upd, 'status': 'too_big', 'bytes': 0}
        else:
            mb += n / 1048576; gz = os.path.getsize(out); total += gz - s0.get('bytes', 0)
            st['datasets'][did] = {'updatedAt': upd, 'status': 'ok', 'bytes': gz, 'fetched': TODAY(), 'file': os.path.relpath(out, d)}
            if core.search(nm) and gz < 15 * 1048576:
                vd = os.path.join(os.path.dirname(out), 'vintages'); os.makedirs(vd, exist_ok=True)
                shutil.copyfile(out, os.path.join(vd, TODAY() + '__' + os.path.basename(out)))
    write_json(sp, st); write_text(marker, datetime.now().isoformat())
    held = sum(1 for v in st['datasets'].values() if v.get('status') == 'ok')
    log('  socrata: catalog', len(cat), 'new', found, 'downloads', ndl, '%.0f MB' % mb, 'held', held, 'of', len(cat), 'folder %.1f GiB' % (total / 2**30))

def job_sec_phrases(job):
    """What listed companies were telling the SEC, week by week (17 Sep 2026). EDGAR full-text search (2001 on, no key)
    counts the 8-K filings of each week that contain a phrase: "workforce reduction", "reduction in force", "plant
    closure", "going concern", "covenant waiver" and the like. One request per phrase per week returns the count; the
    filing date is public the same day and is never revised, so each series is real time by construction and spans
    2001, 2007-09, 2020 and 2024. Weeks end on Saturday, as the claims weeks do. A week closed more than ten days ago
    is asked once; the last weeks are asked again each run. A request budget spreads the first backfill over about a day
    of hourly cycles. Output: sec_phrase_<slug>_weekly_count.csv (date = the week's Saturday)."""
    d = os.path.join(WH, job['dir']); os.makedirs(d, exist_ok=True)
    marker = os.path.join(d, 'sec_phrases.lastfetch')
    if fresh(marker, job.get('fresh_hours')):
        log('  fresh sec_phrases'); return
    budget = int(job.get('max_requests', 500)); today = date.today(); complete = True
    y0, m0, d0 = [int(x) for x in job.get('start', '2001-01-06').split('-')]
    first = date(y0, m0, d0)
    while first.weekday() != 5: first += timedelta(days=1)
    for ph in job['phrases']:
        slug = re.sub(r'[^a-z0-9]+', '_', ph.lower()).strip('_')
        out = os.path.join(d, 'sec_phrase_%s_weekly_count.csv' % slug)
        have = read_series(out); n0 = len(have); w = first
        while w <= today + timedelta(days=6):
            k = w.isoformat(); closed = (today - w).days > 10
            if not (closed and k in have):
                if budget <= 0:
                    complete = False; break
                u = ('https://efts.sec.gov/LATEST/search-index?q=%s&forms=%s&dateRange=custom&startdt=%s&enddt=%s'
                     % (urllib.parse.quote('"%s"' % ph), job.get('forms', '8-K'), (w - timedelta(days=6)).isoformat(), min(w, today).isoformat()))
                j = http_json(u, headers={'Accept': 'application/json'}, quiet=True); budget -= 1; time.sleep(0.2)
                if j and 'hits' in j: have[k] = str((j['hits'].get('total') or {}).get('value', 0))
                else: complete = False
            w += timedelta(days=7)
        write_series(out, have, quiet=True)
        log('  sec phrase', repr(ph), 'weeks', len(have), '(+%d)' % (len(have) - n0), 'budget left', budget)
        if budget <= 0: complete = False
    if complete: write_text(marker, datetime.now().isoformat())

def job_ecb_rtd(job):
    """The ECB's real-time database (dataflow RTD), keyless: every value as it stood at each publication, with the
    publication timestamp (VALID_FROM) attached. Found 17 Sep 2026. It carries euro-area unemployment, industrial
    production, new car registrations, money and trade, and the unemployment rate of the United States and Japan, with
    vintages from January 2001. A third international real-time source beside the OECD revisions database and the
    Bundesbank's. The whole dataflow cannot be asked for at once (400), so the key list is read first and each key's
    history fetched in turn; a key already held and unchanged costs one request. Output: one csv.gz per series key."""
    d = os.path.join(WH, job['dir']); marker = os.path.join(d, '_lastfetch')
    if fresh(marker, job.get('fresh_hours')):
        log('  fresh ecb_rtd'); return
    base = 'https://data-api.ecb.europa.eu/service/data/RTD'
    b = http_get(base + '?detail=serieskeysonly&format=csvdata&lastNObservations=1', headers={'Accept': 'text/csv'}, quiet=True)
    if not b:
        log('  FAIL ecb_rtd key list', LAST_CODE[0]); return
    keys = [l.split(',')[0] for l in b.decode('utf-8', 'ignore').splitlines()[1:] if l.startswith('RTD.')]
    freqs = set(job.get('freqs', ['M', 'Q']))
    keys = [k for k in keys if k.split('.')[1] in freqs]
    write_text(os.path.join(d, '_keys.txt'), '\n'.join(sorted(keys)))
    # Resume where the last run stopped, and spend at most max_keys_per_run: the whole set at 180 s a key blocked the
    # cycle for two hours on 17 Sep 2026. Keys already held and fresh are skipped outright.
    pos_f = os.path.join(d, '_pos.txt')
    try: pos = int(open(pos_f).read().strip())
    except Exception: pos = 0
    keys = sorted(keys); budget = int(job.get('max_keys_per_run', 40))
    order = keys[pos:] + keys[:pos]
    n = ch = 0
    for k in order:
        out = os.path.join(d, re.sub(r'[^A-Za-z0-9._-]', '_', k) + '.csv.gz')
        if fresh(out, job.get('key_fresh_hours', 400)) or fresh(out + '.nodata', 24 * 30):
            continue
        if n >= budget:
            log('  ecb_rtd: budget of %d keys spent; the rest follow next run' % budget); break
        h = http_get('%s/%s?includeHistory=true&format=csvdata' % (base, k[4:]), headers={'Accept': 'text/csv'}, quiet=True,
                     timeout=job.get('timeout', 45), retries=1)
        time.sleep(0.2)
        if h is not None and LAST_CODE[0] == 200 and len(h) < 200:
            # the service answers 200 with a header and no rows for a key it does not carry; that is an answer,
            # not a failure, and marking it stops the same retry storm found in the queue collector (18 Sep 2026)
            write_text(out + '.nodata', datetime.now().isoformat()); n += 1; continue
        if not h or len(h) < 200:
            log('  FAIL', k, LAST_CODE[0]); continue
        n += 1
        old = None
        if os.path.exists(out):
            try:
                with gzip.open(out, 'rb') as f: old = f.read()
            except OSError: old = None
        if old != h: write_bytes(out, h); ch += 1
    try:
        write_text(pos_f, str((keys.index(k) + 1) % len(keys)))
    except Exception: pass
    held = len(glob.glob(os.path.join(d, 'RTD.*.csv.gz')))
    log('  ecb_rtd keys', len(keys), 'held', held, 'fetched this run', n, 'changed', ch)
    if held >= len(keys): write_text(marker, datetime.now().isoformat())

def job_audit(job):
    """The quality gate (18 Sep 2026): recompute every series' true first and last observation, its count and its
    share of repeated values, and say which ones have stopped being data. Nothing checked this before, so a source
    that kept answering 200 while its content froze looked like a success every cycle. Writes logs/AUDIT.csv,
    AUDIT_flags.csv and AUDIT.txt; raises a notification when the flagged count rises above notify_over."""
    import subprocess
    r = subprocess.run([sys.executable, os.path.join(CODE, 'audit_warehouse.py')], capture_output=True, timeout=job.get('timeout', 3600))
    out = (r.stdout or b'').decode('utf-8', 'ignore')
    for line in out.splitlines()[:6]:
        if line.strip(): log('  audit', line.strip()[:150])
    flags = os.path.join(LOGS, 'AUDIT_flags.csv')
    n = max(0, sum(1 for _ in open(flags)) - 1) if os.path.exists(flags) else 0
    log('  audit: %d series flagged' % n)
    if n > job.get('notify_over', 0):
        try:
            subprocess.run(['/usr/bin/osascript', '-e',
                            'display notification "%d series flagged - see logs/AUDIT.txt" with title "Bristow-Hall data audit"' % n], timeout=20)
        except Exception: pass

JOBS = {'job_nonce_post': job_nonce_post, 'job_state_check': job_state_check, 'job_derive_extra': job_derive_extra, 'job_discover': job_discover, 'job_dated_files': job_dated_files, 'job_audit': job_audit, 'job_ecb_rtd': job_ecb_rtd, 'job_sec_phrases': job_sec_phrases, 'job_feeds': job_feeds, 'job_socrata_sweep': job_socrata_sweep, 'job_polymarket': job_polymarket, 'job_kalshi': job_kalshi, 'job_chicagofed': job_chicagofed, 'job_sec_items': job_sec_items, 'job_page_links': job_page_links, 'job_files': job_files, 'job_github': job_github, 'job_tsa': job_tsa, 'job_nyfed': job_nyfed, 'job_fedwire': job_fedwire, 'job_pola': job_pola,
        'job_treasurydirect': job_treasurydirect, 'job_fema': job_fema, 'job_cdc': job_cdc, 'job_dts': job_dts, 'job_eia': job_eia,
        'job_cboe_pc': job_cboe_pc, 'job_nimble': job_nimble, 'job_fred_bulk': job_fred_bulk, 'job_fred_vintages': job_fred_vintages}

def run_job(job):
    t0 = time.time(); name = job['name']; log('== job', name, 'start')
    try:
        JOBS[job.get('func', 'job_files')](job); status = 'ok'
    except Exception as e:
        status = 'EXC ' + type(e).__name__
        log('== job', name, 'EXC', type(e).__name__, str(e)[:200]); log(traceback.format_exc()[-1500:])
    log('== job', name, status, '%.1f min' % ((time.time() - t0) / 60))
    return status

def manifest():
    try:
        sys.path.insert(0, CODE); import manifest as m
        n = m.build(); log('== manifest', n, 'files')
    except Exception as e:
        log('== manifest EXC', type(e).__name__, str(e)[:200])

def reload_sources():
    """sources.json is re-read at the start of every cycle so jobs can be added/changed without a restart."""
    global SRC
    try:
        SRC = json.load(open(os.path.join(CODE, 'sources.json')))
    except Exception as e:
        log('== sources.json reload failed, keeping the loaded registry:', type(e).__name__, str(e)[:120])

def sleep_until(hours):
    """Wall-clock wait in one-minute slices (17 Sep 2026). time.sleep() does not count the time a Mac spends asleep, so
    a plain six-hour sleep could last days on a laptop; in slices, a cycle that fell due during sleep starts within a
    minute of the machine waking."""
    due = time.time() + hours * 3600
    while time.time() < due: time.sleep(min(60, max(1, due - time.time())))

def online(tries=6):
    """True once a TLS port answers. After a wake the network can take a minute; a cycle run offline would mark
    nothing fresh but would waste the hour."""
    for k in range(tries):
        for host in ('api.stlouisfed.org', 'www.federalreserve.gov', '1.1.1.1'):
            try:
                socket.create_connection((host, 443), timeout=6).close(); return True
            except OSError: pass
        time.sleep(20)
    return False

_STATUS = {}
def write_status(summary, minutes, nxt_hours):
    """logs/STATUS.txt: one screen that says whether the collector is healthy. No AI needed to read it."""
    try:
        du = shutil.disk_usage(WH); now = time.strftime('%Y-%m-%d %H:%M:%S')
        for name, st in summary:
            r = _STATUS.setdefault(name, {'last_ok': '', 'last_fail': '', 'fails_in_a_row': 0})
            if st == 'ok': r['last_ok'] = now; r['fails_in_a_row'] = 0
            else: r['last_fail'] = now + ' ' + st; r['fails_in_a_row'] += 1
        L = ['Standing collector (collection 191) - status written ' + now,
             'pid %d | last cycle %.1f min | next cycle in %.1f h | disk free %.0f GiB%s' % (os.getpid(), minutes, nxt_hours, du.free / 2**30, '  ** LOW DISK: vintages and FRED bulk paused **' if LOW_DISK[0] else ''),
             '', '%-24s %-20s %s' % ('job', 'last ok', 'last failure')]
        for name in sorted(_STATUS):
            r = _STATUS[name]; L.append('%-24s %-20s %s' % (name, r['last_ok'], r['last_fail'] + (' (x%d)' % r['fails_in_a_row'] if r['fails_in_a_row'] > 1 else '')))
        if FE is not None:
            n304, nbody = FE.savings()
            L += ['', 'fetch engine: %d requests answered "not changed" (no bytes), %d bodies fetched' % (n304, nbody)]
            bad = FE.health_report(25)
            if bad:
                L += ['', 'addresses failing, with the reason and when they are asked for again:',
                      '%-78s %5s %-22s %s' % ('address', 'fails', 'next try', 'reason')]
                for url, fails, err, nxt, ok, win in bad:
                    L.append('%-78s %5d %-22s %s' % (url[:78], fails,
                             time.strftime('%Y-%m-%d %H:%M', time.localtime(nxt)) if nxt else '-', (err or '')[:60]))
        write_text(os.path.join(LOGS, 'STATUS.txt'), '\n'.join(L) + '\n')
        bad = sorted(n for n, r in _STATUS.items() if r['fails_in_a_row'] == 6)
        if bad or (LOW_DISK[0] and time.strftime('%H') == '09'):
            msg = ('Low disk: vintages and bulk pulls paused. ' if LOW_DISK[0] else '') + ('Failing six cycles in a row: ' + ', '.join(bad) if bad else '')
            try:
                import subprocess
                subprocess.run(['/usr/bin/osascript', '-e', 'display notification "%s" with title "Bristow-Hall data collector"' % msg.replace('"', "'")], timeout=20)
            except Exception: pass
    except Exception as e:
        log('== status EXC', type(e).__name__, str(e)[:120])

_MANIFEST_EVERY = [0]


def write_manifest():
    """MANIFEST.csv at the root of the collection: every file held, which job put it there, the address it came from,
    its size and when it last changed. Anthony's data rule asks that every collection carry one; this keeps it current
    without anyone remembering to run anything (18 September 2026)."""
    # Walking ninety thousand files and stat-ing each of them twice an hour is the largest fixed cost in a cycle and
    # the answer barely changes. Written every sixth cycle, and whenever the collector has just started (18 Sep 2026).
    _MANIFEST_EVERY[0] += 1
    if _MANIFEST_EVERY[0] % 6 != 1:
        return
    try:
        path = os.path.join(DATA_ROOT, os.path.basename(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'MANIFEST.csv')
        url_of = {}
        for job in SRC['jobs']:
            for f in job.get('files', []):
                url_of[(job.get('dir', job['name']), f['out'])] = f['url']
        rows = []
        for dp, dn, fn in os.walk(WH):
            for f in fn:
                if f.startswith('.'): continue
                p = os.path.join(dp, f)
                rel = os.path.relpath(p, WH)
                top = rel.split(os.sep)[0]
                try: st = os.stat(p)
                except OSError: continue
                rows.append([rel, top, st.st_size,
                             datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%d %H:%M'),
                             redact(url_of.get((top, f), ''))])
        rows.sort()
        write_csv(path, ['file', 'job', 'bytes', 'last_changed', 'source_address'], rows)
        log('== manifest file written:', len(rows), 'files ->', path)
    except Exception as e:
        log('== manifest EXC', type(e).__name__, str(e)[:150])


def write_board():
    """The shared board (_CLAIMS/DATA-BOARD.md): what every chat needs in order not to collect the same thing twice.
    Written at the end of each cycle so it is never stale. A fault here must never end a cycle."""
    try:
        b = os.path.join(DATA_ROOT, '_CLAIMS', 'board.py')
        if os.path.exists(b):
            import subprocess
            subprocess.run([sys.executable, b], capture_output=True, timeout=180)
    except Exception as e:
        log('== board EXC', type(e).__name__, str(e)[:120])


def cycle(names=None):
    t0 = time.time(); summary = []; reload_sources()
    try: LOW_DISK[0] = shutil.disk_usage(WH).free < 2**30 * SRC.get('low_disk_gib', 12)
    except Exception: pass
    if LOW_DISK[0]: log('== LOW DISK: under %s GiB free; vintages and FRED bulk are paused' % SRC.get('low_disk_gib', 12))
    todo = [j for j in SRC['jobs']
            if (names is None or j['name'] in names) and (names is not None or j.get('enabled', True))]
    workers = int(SRC.get('cycle_workers', 4))
    if workers > 1 and len(todo) > 1:
        # Jobs write to separate folders and each source has its own rate rule, so a cycle need not be a queue. Four
        # at a time turned a pass over fifty-four jobs from minutes into well under one (17 September 2026).
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = [(j['name'], ex.submit(run_job, j)) for j in todo]
            for name, f in futs:
                try: summary.append((name, f.result()))
                except Exception as e: summary.append((name, 'EXC ' + type(e).__name__))
    else:
        for job in todo:
            summary.append((job['name'], run_job(job)))
    manifest()
    log('== cycle done %.1f min: ' % ((time.time() - t0) / 60) + ', '.join('%s=%s' % s for s in summary))
    return summary, (time.time() - t0) / 60

_LOCK = os.path.join(LOGS, 'collector.lock')
def pid_alive(pid):
    try: os.kill(pid, 0); return True
    except ProcessLookupError: return False
    except PermissionError: return True
    except Exception: return False

def acquire_lock():
    if os.path.exists(_LOCK):
        try: pid = int(open(_LOCK).read().split()[0])
        except Exception: pid = None
        if pid and pid != os.getpid() and pid_alive(pid):
            print('collector.lock held by live pid %d; exiting' % pid, flush=True); sys.exit(3)
    open(_LOCK, 'w').write('%d %s\n' % (os.getpid(), time.strftime('%Y-%m-%d %H:%M:%S')))
    def _rm():
        try:
            if int(open(_LOCK).read().split()[0]) == os.getpid(): os.remove(_LOCK)
        except Exception: pass
    atexit.register(_rm)

def main():
    mode = ARGS[0] if ARGS else 'once'
    if mode == 'list':
        for j in SRC['jobs']: print('%-16s %-20s enabled=%s' % (j['name'], j.get('func', 'job_files'), j.get('enabled', True)))
        return
    acquire_lock()
    log('#### collector start pid', os.getpid(), 'mode', mode, 'force' if FORCE else '')
    if mode == 'loop':
        # The FRED pull (bulk + vintages, hours long) runs in its own thread so the small sources -- the ones the live
        # rule's daily refresh reads -- keep their six-hour cadence whatever FRED is doing (16 September 2026).
        FREDJOBS = set(SRC.get('fred_jobs', ['fred_bulk', 'fred_vintages']))
        SLOWJOBS = set(SRC.get('slow_jobs', []))   # heavy sources; their own thread, so the hourly pass stays quick
        def _fred_loop():
            while True:
                try:
                    reload_sources()
                    for job in SRC['jobs']:
                        if job['name'] == 'fred_bulk' and LOW_DISK[0]: log('== fred_bulk skipped: low disk'); continue
                        if job['name'] in FREDJOBS and job.get('enabled', True): run_job(job)
                except Exception as e:
                    log('== fred thread EXC', type(e).__name__, str(e)[:200])
                hrs = SRC.get('fred_sleep_hours', 6); log('== fred thread sleeping %.1f h' % hrs); sleep_until(hrs)
        def _slow_loop():
            """The heavy sources (whole databases, real-time archives) on their own clock, added 17 Sep 2026 after
            ecb_rtd held the hourly cycle for two hours. They are large and rarely change; the small sources the live
            rule reads must not wait behind them."""
            time.sleep(120)
            while True:
                try:
                    reload_sources()
                    for job in SRC['jobs']:
                        if job['name'] in SLOWJOBS and job.get('enabled', True): run_job(job)
                except Exception as e:
                    log('== slow thread EXC', type(e).__name__, str(e)[:200])
                hrs = SRC.get('slow_sleep_hours', 6); log('== slow thread sleeping %.1f h' % hrs); sleep_until(hrs)
        def _fast_loop():
            """The sources the live rule itself reads, on a short clock. An hourly pass can be an hour late to a
            release that lands at 8:30; these are asked for every few minutes, and cost a round trip each when nothing
            has changed because the request is conditional (17 September 2026)."""
            FAST = set(SRC.get('fast_jobs', ['dol', 'release_pdfs']))
            mins = float(SRC.get('fast_sleep_minutes', 10))
            time.sleep(60)
            while True:
                try:
                    reload_sources()
                    for job in SRC['jobs']:
                        if job['name'] in FAST and job.get('enabled', True): run_job(job)
                except Exception as e:
                    log('== fast thread EXC', type(e).__name__, str(e)[:200])
                sleep_until(mins / 60.0)
        if SRC.get('fast_jobs', ['dol', 'release_pdfs']): threading.Thread(target=_fast_loop, daemon=True).start()
        threading.Thread(target=_fred_loop, daemon=True).start()
        if SLOWJOBS: threading.Thread(target=_slow_loop, daemon=True).start()
        while True:
            # Nothing inside a cycle may end the loop. A fault in one job is already caught in run_job; this catches a
            # fault in the cycle itself (a broken sources.json, a full disk, a clock jump) so that the collector waits
            # and tries again rather than exiting and waiting for launchd to notice (17 September 2026).
            try:
                if not online():
                    log('== offline: no cycle; trying again in 5 min'); sleep_until(5 / 60); continue
                reload_sources()
                names = {j['name'] for j in SRC['jobs'] if j['name'] not in FREDJOBS and j['name'] not in SLOWJOBS and j.get('enabled', True)}
                summary, minutes = cycle(names)
                hrs = SRC.get('loop_sleep_hours', 1); write_status(summary, minutes, hrs); write_manifest(); write_board(); log('== sleeping %.1f h' % hrs)
            except Exception as e:
                log('== cycle EXC', type(e).__name__, str(e)[:300], '| the loop holds and tries again')
                log(traceback.format_exc()[-1200:]); hrs = 0.25
            sleep_until(hrs)
    elif mode == 'once':
        cycle()
    else:
        known = {j['name'] for j in SRC['jobs']}
        bad = [a for a in ARGS if a not in known]
        if bad: print('unknown job(s):', bad, '; known:', sorted(known)); sys.exit(2)
        cycle(set(ARGS))

if __name__ == '__main__':
    main()
