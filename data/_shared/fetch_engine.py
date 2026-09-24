#!/usr/bin/env python3
"""A fetch engine for the Bristow-Hall collectors: never raises, never gives up, and asks for as little as possible.

Written 17 September 2026 to replace bare urllib calls in the standing collector (collection 191) and the queue
collector. Three things it does that a plain GET does not.

1. It asks for less. Every URL's ETag and Last-Modified are remembered, and when a file already on disk is asked for
   again the request carries If-None-Match and If-Modified-Since. A source that has not changed answers 304 with an
   empty body: no bytes cross the wire, and the cycle costs a round trip instead of a download. Connections are kept
   alive and reused per host.

2. It does not give up on one refusal. A failed fetch walks a ladder of ways to get the same bytes, in rising cost:
   the plain request again with a different browser identity; the same request through curl, whose TLS handshake
   differs from Python's and passes hosts that refuse urllib; curl with a complete browser header set; the newest
   Internet Archive capture of that exact address (which also answers when the source itself is down); the archive's
   index, for the newest capture that returned 200; the text proxy r.jina.ai; and last, and only when a key exists and
   a budget is left, Nimble. Whichever rung worked is remembered and tried first next time, so the ladder costs
   nothing once a source is known.

3. It never raises and never spins. Every path is wrapped; the caller gets bytes, NOT_MODIFIED, or None. A URL that
   keeps failing is put on a widening schedule (10 minutes, then 20, 40 ... to a day) so a dead address cannot spend
   a cycle's time, and every failure is recorded with its reason so the ledger can say what is broken and why.

State lives in one SQLite file beside this module (WAL, so several collectors may use it at once). Nothing here
writes into the warehouse; the caller decides where bytes land.
"""
import os, re, ssl, time, json, random, sqlite3, subprocess, threading, urllib.request, urllib.error, urllib.parse
from email.utils import formatdate, parsedate_to_datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, 'fetch_state.sqlite')
NOT_MODIFIED = b''                      # sentinel: distinguished from None by `is NOT_MODIFIED`
LOG = [None]                            # the caller may set LOG[0] to its own log function

AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:131.0) Gecko/20100101 Firefox/131.0',
]
BROWSER = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9', 'Accept-Encoding': 'gzip, deflate',
    'Sec-Fetch-Dest': 'document', 'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Site': 'none',
    'Upgrade-Insecure-Requests': '1',
}
HARD = (400, 401, 405, 410, 422, 451)   # arguing with these is pointless; 403 and 404 get the ladder
BACKOFF = [600, 1200, 2400, 4800, 9600, 19200, 38400, 86400]   # seconds after 1st, 2nd ... failure
# 24 Sep 2026 (ops-0924): 'bh_nimble' - our own browser fetcher (_shared/bh_nimble.py: real Chrome on this machine,
# exact bytes, no quota) - comes straight after curl, ahead of the archive copies and the paid Nimble, which stays last
LADDER = ['plain', 'agent', 'curl', 'curl_browser', 'bh_nimble', 'wayback_now', 'wayback_cdx', 'jina', 'nimble']
# addresses whose bytes are a file, not a page: the text-only rungs (jina, and Nimble, which wraps what it gets in
# JSON text) cannot return such a file byte for byte, so they are never used for one
BINARY = re.compile(r'(?i)\.(xlsx?|xlsm|xlsb|zip|gz|tgz|bz2|xz|7z|pdf|parquet|dta|sas7bdat|sav|xpt|docx?|pptx?|'
                    r'png|jpe?g|gif|tiff?|mat|h5|nc|feather|arrow|db|sqlite)(\?|#|$)')

_lock = threading.Lock()
_openers = {}
_nimble_used = [0]
LAST = threading.local()          # LAST.code: the code of the most recent attempt, for callers that switch on it
NIMBLE_BUDGET = int(os.environ.get('NIMBLE_BUDGET', '100'))   # per process per UTC day (was 25 per process, for ever)
NIMBLE_DAILY = int(os.environ.get('NIMBLE_DAILY', '120'))     # per machine per UTC day, counted in the state file
_nimble_day = [None]


def log(*a):
    if LOG[0]:
        try: LOG[0](*a); return
        except Exception: pass
    print(' '.join(str(x) for x in a), flush=True)


# ------------------------------------------------------------------ state
def _db():
    c = sqlite3.connect(DB, timeout=30)
    c.execute('PRAGMA journal_mode=WAL')
    c.execute('CREATE TABLE IF NOT EXISTS cache (url TEXT PRIMARY KEY, etag TEXT, lastmod TEXT, seen REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS health (url TEXT PRIMARY KEY, fails INT DEFAULT 0, last_err TEXT, '
              'next_try REAL DEFAULT 0, last_ok REAL DEFAULT 0, winner TEXT, n_ok INT DEFAULT 0, n_304 INT DEFAULT 0)')
    return c


def _get_row(table, url):
    try:
        with _lock, _db() as c:
            r = c.execute('SELECT * FROM %s WHERE url=?' % table, (url,)).fetchone()
            if not r: return {}
            cols = [d[0] for d in c.execute('SELECT * FROM %s LIMIT 0' % table).description]
            return dict(zip(cols, r))
    except Exception:
        return {}


def _set(table, url, **kw):
    if not kw: return
    try:
        with _lock, _db() as c:
            c.execute('INSERT OR IGNORE INTO %s (url) VALUES (?)' % table, (url,))
            c.execute('UPDATE %s SET %s WHERE url=?' % (table, ','.join(k + '=?' for k in kw)),
                      tuple(kw.values()) + (url,))
    except Exception:
        pass


def quarantined(url):
    """True when this address has failed enough times that it is not due yet. Never permanent: the wait tops out at a day."""
    h = _get_row('health', url)
    return bool(h.get('next_try', 0) and time.time() < h['next_try'])


def note_ok(url, rung, code):
    _set('health', url, fails=0, last_err='', next_try=0, last_ok=time.time(), winner=rung,
         **({'n_304': (_get_row('health', url).get('n_304') or 0) + 1} if code == 304 else
            {'n_ok': (_get_row('health', url).get('n_ok') or 0) + 1}))


def note_fail(url, why):
    h = _get_row('health', url); n = (h.get('fails') or 0) + 1
    _set('health', url, fails=n, last_err=str(why)[:200], next_try=time.time() + BACKOFF[min(n, len(BACKOFF)) - 1])


def health_report(limit=40):
    """Rows for the status file: what is broken, why, and when it will be asked for again."""
    try:
        with _lock, _db() as c:
            return c.execute('SELECT url, fails, last_err, next_try, last_ok, winner FROM health WHERE fails>0 '
                             'ORDER BY fails DESC LIMIT ?', (limit,)).fetchall()
    except Exception:
        return []


def savings():
    """(requests answered 304, requests that carried a body) since the state file was made."""
    try:
        with _lock, _db() as c:
            return c.execute('SELECT COALESCE(SUM(n_304),0), COALESCE(SUM(n_ok),0) FROM health').fetchone()
    except Exception:
        return (0, 0)


# ------------------------------------------------------------------ transport
def _opener(host):
    """One opener per host, so its connection is kept alive and reused across a cycle."""
    with _lock:
        o = _openers.get(host)
        if o is None:
            ctx = ssl.create_default_context()
            o = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx),
                                            urllib.request.HTTPRedirectHandler())
            _openers[host] = o
        return o


def _headers(url, extra=None, agent=None, browser=False, conditional=None):
    h = {'User-Agent': agent or AGENTS[0], 'Accept': '*/*', 'Accept-Encoding': 'gzip, deflate'}
    if browser:
        h.update(BROWSER)
        p = urllib.parse.urlparse(url)
        h['Referer'] = '%s://%s/' % (p.scheme or 'https', p.netloc)
    if conditional:
        h.update(conditional)
    h.update(extra or {})
    return h


def _decompress(raw, enc):
    if not raw: return raw
    try:
        if enc == 'gzip':
            import gzip as _g, io as _io
            return _g.GzipFile(fileobj=_io.BytesIO(raw)).read()
        if enc == 'deflate':
            import zlib
            try: return zlib.decompress(raw)
            except Exception: return zlib.decompress(raw, -zlib.MAX_WBITS)
    except Exception:
        return raw
    return raw


def _urlopen(url, headers, timeout, data=None, method=None):
    """One attempt. Returns (bytes|NOT_MODIFIED|None, code, response headers). Raises nothing."""
    try:
        req = urllib.request.Request(url, headers=headers, data=data, method=method)
        with _opener(urllib.parse.urlparse(url).netloc).open(req, timeout=timeout) as r:
            body = _decompress(r.read(), (r.headers.get('Content-Encoding') or '').lower())
            return body, getattr(r, 'status', 200), dict(r.headers)
    except urllib.error.HTTPError as e:
        hdr = {}
        try: hdr = dict(e.headers)
        except Exception: pass
        # the error object holds a socket: it must be closed, or a job with many 404s exhausts the process's file
        # descriptors ("Too many open files", seen on the state permit backfill, 17 September 2026)
        try: e.read(200)
        except Exception: pass
        try: e.close()
        except Exception: pass
        if e.code == 304: return NOT_MODIFIED, 304, hdr
        return None, e.code, hdr
    except Exception as e:
        return None, type(e).__name__, {}


def _curl(url, timeout, browser=False, headers=None):
    """The same request through curl. Its TLS handshake differs from Python's, which is enough for many hosts.

    24 Sep 2026 (ops-0924): the HTTP status is now read (-w) and only a 2xx body is returned. Before, curl without
    --fail exits 0 on a 404 or a 500 and hands back the server's error page, and any error page over 4 KB (or without
    the refusal words) was accepted as the data: the way 404 pages came to be saved as data (ask 30, ISM)."""
    import tempfile
    fd, tmp = tempfile.mkstemp(prefix='fe_curl_', suffix='.part')
    os.close(fd)
    cmd = ['curl', '-sSL', '--compressed', '--max-time', str(int(timeout)), '-A', random.choice(AGENTS), '-o', tmp,
           '-w', '%{http_code}']
    if browser:
        for k, v in BROWSER.items():
            if k != 'Accept-Encoding': cmd += ['-H', '%s: %s' % (k, v)]
        p = urllib.parse.urlparse(url); cmd += ['-H', 'Referer: %s://%s/' % (p.scheme or 'https', p.netloc)]
    for k, v in (headers or {}).items():
        cmd += ['-H', '%s: %s' % (k, v)]
    cmd.append(url)
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout + 30)
        try:
            code = int((r.stdout or b'0').decode('ascii', 'ignore').strip()[-3:] or 0)
        except ValueError:
            code = 0
        if r.returncode != 0:
            return None, ('curl%d' % r.returncode) if not code or code < 400 else code
        if 200 <= code < 300:
            with open(tmp, 'rb') as f:
                body = f.read()
            return (body, 200) if body else (None, 'curl-empty')
        return None, code or 'curl-nocode'
    except Exception as e:
        return None, type(e).__name__
    finally:
        try: os.unlink(tmp)
        except Exception: pass


def _wayback_now(url, timeout):
    """The newest capture of this exact address, unrewritten (the id_ form gives the bytes as they were served)."""
    b, code, _ = _urlopen('http://web.archive.org/web/2id_/' + url, _headers(url, browser=True), timeout)
    return (b, 200) if b else (None, code)


def _wayback_cdx(url, timeout):
    """The archive's index, for the newest capture that answered 200. Slower; used when the shortcut above fails."""
    q = urllib.parse.urlencode({'url': url, 'output': 'text', 'fl': 'timestamp', 'filter': 'statuscode:200',
                                'limit': '-1'})
    b, code, _ = _urlopen('http://web.archive.org/cdx/search/cdx?' + q, _headers(url), timeout)
    if not b: return None, code
    ts = b.decode('utf-8', 'ignore').split()
    if not ts: return None, 'no-capture'
    b, code, _ = _urlopen('http://web.archive.org/web/%sid_/%s' % (ts[-1], url), _headers(url, browser=True), timeout)
    return (b, 200) if b else (None, code)


def _jina(url, timeout):
    """r.jina.ai renders a page and returns its text, keyless. Text only, so it is a last resort before Nimble.
    24 Sep 2026: never for a file (its 'text' of a spreadsheet or PDF is not the file), and its report that the
    source itself answered an error ('Target URL returned error 404') is a failure, not data."""
    if BINARY.search(url):
        return None, 'jina-binary'
    b, code, _ = _urlopen('https://r.jina.ai/' + url, _headers(url), timeout)
    if b and re.search(rb'(?i)target url returned error (\d{3})', b[:3000]):
        m = re.search(rb'(?i)target url returned error (\d{3})', b[:3000])
        return None, int(m.group(1))
    return (b, 200) if b else (None, code)


_BHN = [None]


def _bh_nimble(url, timeout, headers=None):
    """Our own browser fetcher (_shared/bh_nimble.py): real Chrome on this machine - through the machine's BH Nimble
    service when it is running, else a private browser for this one fetch. Exact bytes for a file; the rendered page
    for a web page; a check page ('checking your browser') that does not clear, a captcha or an HTTP error is a
    failure. No quota and no key. Set BH_NIMBLE=0 to leave it out."""
    if os.environ.get('BH_NIMBLE', '1') == '0':
        return None, 'bhn-off'
    try:
        if _BHN[0] is None:
            import importlib.util
            spec = importlib.util.spec_from_file_location('bh_nimble', os.path.join(HERE, 'bh_nimble.py'))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _BHN[0] = mod
        return _BHN[0].get(url, timeout=timeout, headers=headers)
    except Exception as e:
        return None, 'bhn-' + type(e).__name__


def _nimble_allowed():
    """24 Sep 2026 (ops-0924): Nimble is capped per day for the whole machine, and the per-process cap starts again each
    day. With only a per-process cap, a collector running as a loop spent its 25 in its first hours and then refused
    Nimble for as long as it ran: on 24 Sep 500 addresses sat at 'nimble-budget' on the old Mac (393 of them STB's
    weekly railroad files, 53 the ECB's, 40 the Mississippi budget office's). The free plan is 5,000 requests a month;
    120 a day per machine stays inside it."""
    day = time.strftime('%Y-%m-%d', time.gmtime())
    if _nimble_day[0] != day:
        _nimble_day[0] = day; _nimble_used[0] = 0
    if _nimble_used[0] >= NIMBLE_BUDGET:
        return False
    try:
        with _lock, _db() as c:
            c.execute('CREATE TABLE IF NOT EXISTS nimble_usage (day TEXT PRIMARY KEY, n INT DEFAULT 0)')
            r = c.execute('SELECT n FROM nimble_usage WHERE day=?', (day,)).fetchone()
            if r and r[0] >= NIMBLE_DAILY:
                return False
            c.execute('INSERT OR IGNORE INTO nimble_usage (day, n) VALUES (?, 0)', (day,))
            c.execute('UPDATE nimble_usage SET n = n + 1 WHERE day=?', (day,))
    except Exception:
        pass                              # the per-process cap still holds
    return True


def _nimble(url, timeout, render=True):
    """Nimble, capped per process per day and per machine per day (_nimble_allowed). A key is read from the environment
    or from live_data/config/local.env."""
    if _nimble_used[0] >= NIMBLE_BUDGET and _nimble_day[0] == time.strftime('%Y-%m-%d', time.gmtime()):
        return None, 'nimble-budget'
    k = os.environ.get('NIMBLE_API_KEY')
    if not k:
        for p in (os.path.join(os.path.dirname(HERE), 'onset-detector-new-2026-08-23', 'live_data', 'config', 'local.env'),
                  os.path.join(HERE, '..', 'live_data', 'config', 'local.env')):
            try:
                for line in open(p):
                    if line.startswith('NIMBLE_API_KEY'): k = line.split('=', 1)[1].strip().strip('"\''); break
            except Exception: pass
            if k: break
    if not k: return None, 'nimble-nokey'
    if BINARY.search(url): return None, 'nimble-binary'   # it answers in JSON text: a file cannot come back byte for byte
    if not _nimble_allowed(): return None, 'nimble-budget'
    _nimble_used[0] += 1
    textfile = bool(re.search(r'(?i)(\.(csv|txt|json|xml|tsv|dat|prn)(\?|#|$))|[?&](format|file_type|output)=(csv|json|xml|txt)', url))
    body = json.dumps({'url': url, 'format': 'html', 'render': bool(render) and not textfile, 'country': 'US'}).encode()
    b, code, _ = _urlopen('https://api.webit.live/api/v1/realtime/web',
                          {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + k}, timeout, data=body)
    if not b:
        return None, code
    # 24 Sep 2026 (ops-0924): Nimble answers with JSON ({"status": ..., "status_code": ..., "html_content": ...}); until
    # today that JSON itself was handed back as the data. Now the page is taken out of it, and the source's own
    # status is honoured.
    try:
        j = json.loads(b)
    except Exception:
        return None, 'nimble-notjson'
    st = j.get('status_code') or j.get('statusCode') or 200
    try: st = int(st)
    except Exception: st = 200
    if st >= 400: return None, st
    page = j.get('html_content') or j.get('content') or ''
    if not page or j.get('status') not in (None, 'success'):
        return None, 'nimble-' + str(j.get('status') or 'empty')[:30]
    # a JSON or text file rendered by Nimble's browser comes back inside the browser's plain-text viewer
    # (<html><head>...</head><body><pre>...</pre></body></html>): the file is the <pre>'s text
    m = re.match(r'(?is)^\s*<html><head>(?:<meta[^>]*>)?(?:<style>.*?</style>)?</head><body><pre[^>]*>(.*)</pre>'
                 r'(?:<div class="json-formatter-container"></div>)?</body></html>\s*$', page)
    if m:
        import html as _html
        return _html.unescape(m.group(1)).encode('utf-8'), 200
    return page.encode('utf-8'), 200


# ------------------------------------------------------------------ the engine
ERRPAGE = re.compile(rb'(?is)(40[0-9]|50[0-9])\s*(forbidden|not found|error|unavailable)|access denied|request blocked|are you a robot|enable javascript and cookies')


def looks_like_error(b):
    """A body a host returns with status 200 that is really a refusal. A short page saying 403, a robot check, or an
    empty shell: treated as a failure so that the ladder goes on instead of saving a refusal as data."""
    return bool(b) and len(b) < 4000 and bool(ERRPAGE.search(b[:4000]))


_FMT = re.compile(r'(?i)[?&](?:format|file_type|filetype|output|outputformat|type)=(csv|json|xlsx|pdf|txt|tsv)(?:&|$)')


def wrong_content(url, b):
    """24 Sep 2026 (ops-0924): True when the bytes contradict the file type the address asks for - a web page (an error,
    refusal or parked-domain page) where a spreadsheet, PDF, zip, gzip, CSV or JSON file should be. The content scan of
    that day found 470 such files kept as data, some as dated vintages. Checked on every rung, so the ladder goes on
    instead of saving the page. Old-style .xls is not judged (some publishers really serve HTML tables as .xls)."""
    try:
        path = urllib.parse.urlparse(url).path.lower()
    except Exception:
        return False
    ext = os.path.splitext(path)[1]
    m = _FMT.search(url)
    if not ext and m:
        ext = '.' + m.group(1).lower()
    head = b[:2048]
    lead = head.lstrip(b'\xef\xbb\xbf \t\r\n')[:300].lower()
    html = lead.startswith((b'<!doctype html', b'<html', b'<head', b'<body', b'<title', b'<!-- ')) or b'<html' in lead[:120]
    if ext in ('.xlsx', '.xlsm', '.xlsb', '.docx', '.pptx', '.zip'):
        return head[:2] != b'PK' and head[:4] != b'\xd0\xcf\x11\xe0'
    if ext == '.pdf':
        return b'%PDF' not in head[:1024]
    if ext in ('.gz', '.tgz'):
        return head[:2] != b'\x1f\x8b'
    if ext == '.json':
        return html or (lead[:1] not in (b'{', b'[', b'"') and bool(lead))
    if ext in ('.csv', '.tsv', '.txt', '.dat', '.prn'):
        return html
    return False


def _conditional(url, if_path):
    """Headers that ask the source to send nothing when nothing changed.

    Only ever sent when a copy is actually on disk. Asking conditionally for a file we do not hold earns a 304 and no
    bytes, which is how five Labor Department files and three Bureau of Economic Analysis archives were recorded as
    'unchanged' while the folder stayed empty (found and fixed 17 September 2026)."""
    h = {}
    # 24 Sep 2026 (ops-0924): with no if_path there is no copy to compare with either, so nothing is conditional. Before,
    # a cached ETag was sent anyway; the source answered 304 with no body; and callers that do not look for
    # NOT_MODIFIED took the empty body as the content - 191's GitHub job wrote Indeed's files as EMPTY files (and marked
    # them current), and every unchanged JSON listing read as an error.
    if if_path is None or not os.path.exists(if_path): return h
    c = _get_row('cache', url)
    if c.get('etag'): h['If-None-Match'] = c['etag']
    if c.get('lastmod'): h['If-Modified-Since'] = c['lastmod']
    elif if_path and os.path.exists(if_path):
        try: h['If-Modified-Since'] = formatdate(os.path.getmtime(if_path), usegmt=True)
        except Exception: pass
    return h


def _remember(url, hdr):
    kw = {'seen': time.time()}
    if hdr.get('ETag'): kw['etag'] = hdr['ETag']
    if hdr.get('Last-Modified'): kw['lastmod'] = hdr['Last-Modified']
    if len(kw) > 1: _set('cache', url, **kw)


def last_code():
    return getattr(LAST, 'code', None)


def smart_get(url, headers=None, timeout=120, if_path=None, alts=None, data=None, method=None,
              allow=None, min_bytes=1, quiet=False, respect_quarantine=True):
    """Get these bytes by whatever means work.

    Returns bytes, or NOT_MODIFIED when the source says nothing changed (compare with `is NOT_MODIFIED`), or None.
    `if_path` is a file already on disk whose date makes the request conditional. `alts` are other addresses for the
    same content, tried in order once the ladder is spent on the first. `allow` limits which rungs may be used
    (a POST, for example, may only be 'plain'). Raises nothing.
    """
    if data is not None or method not in (None, 'GET'):
        b, code, hdr = _urlopen(url, _headers(url, headers), timeout, data=data, method=method)
        if b: note_ok(url, 'plain', code)
        else: note_fail(url, code)
        return b
    if respect_quarantine and quarantined(url):
        return None
    rungs = [r for r in LADDER if not allow or r in allow]
    win = (_get_row('health', url) or {}).get('winner')
    # the rung that worked last time goes first - never the paid or text-only ones (24 Sep 2026: Yahoo's addresses,
    # won once by Nimble, then asked Nimble first every time and kept its HTML-wrapped answer)
    if win in rungs and win not in ('nimble', 'jina'): rungs = [win] + [r for r in rungs if r != win]
    cond = _conditional(url, if_path)

    for i, target in enumerate([url] + list(alts or [])):
        tried = []                            # (rung, code) of every failed attempt, for an honest reason
        for rung in rungs:
            b = code = None
            try:
                if rung == 'plain':
                    b, code, hdr = _urlopen(target, _headers(target, headers, conditional=cond if i == 0 else None), timeout)
                    if b is NOT_MODIFIED:
                        LAST.code = 304; note_ok(target, 'plain', 304)
                        if not quiet: log('    304', target[:110])
                        return NOT_MODIFIED
                    if b: _remember(target, hdr)
                elif rung == 'agent':
                    b, code, hdr = _urlopen(target, _headers(target, headers, agent=random.choice(AGENTS[1:]), browser=True), timeout)
                    if b is NOT_MODIFIED: return NOT_MODIFIED
                elif rung == 'curl':
                    b, code = _curl(target, timeout, headers=headers)
                elif rung == 'curl_browser':
                    b, code = _curl(target, timeout, browser=True, headers=headers)
                elif rung == 'bh_nimble':
                    b, code = _bh_nimble(target, min(timeout, 240), headers=headers)
                elif rung == 'wayback_now':
                    b, code = _wayback_now(target, timeout)
                elif rung == 'wayback_cdx':
                    b, code = _wayback_cdx(target, timeout)
                elif rung == 'jina':
                    b, code = _jina(target, min(timeout, 90))
                elif rung == 'nimble':
                    b, code = _nimble(target, min(timeout, 200))
            except Exception as e:
                b, code = None, type(e).__name__
            LAST.code = 304 if b is NOT_MODIFIED else (200 if b else code)
            if b and b is not NOT_MODIFIED and looks_like_error(b):
                b, code = None, 'refusal-page'
            if b and b is not NOT_MODIFIED and wrong_content(target, b):
                b, code = None, 'wrong-content'
            if b and b is not NOT_MODIFIED and len(b) >= min_bytes:
                LAST.rung = rung
                note_ok(target, rung, 200)
                if rung != 'plain' and not quiet:
                    log('    got it by', rung, '(%d bytes)' % len(b), target[:100])
                return b
            if b and b is not NOT_MODIFIED:
                code = 'short-%dB' % len(b)   # a body, but under min_bytes
            tried.append((rung, code))
        # 24 Sep 2026 (ops-0924): the reason recorded is the SOURCE's own answer when one was had (the first HTTP
        # status from a rung that asked the source itself), then every rung's result. Before, the last rung's note
        # was kept - 'nimble-budget' stood for 393 STB addresses whose real answer is 404.
        direct = [c for r, c in tried if r in ('plain', 'agent', 'curl', 'curl_browser', 'bh_nimble')
                  and isinstance(c, int) and c >= 400]
        lead = direct[0] if direct else (tried[-1][1] if tried else code)
        why = ('%s | %s' % (lead, ' '.join('%s:%s' % (r, c) for r, c in tried)))[:200]
        LAST.code = lead
        note_fail(target, why)
        if not quiet: log('    all', len(rungs), 'ways failed', str(lead), target[:110])
    return None


def fetch_many(items, worker, threads=4):
    """Run worker(item) over items in a small pool, in order of completion. Never raises; returns [(item, result)]."""
    if threads <= 1 or len(items) < 2:
        return [(it, _safe(worker, it)) for it in items]
    from concurrent.futures import ThreadPoolExecutor
    out = []
    with ThreadPoolExecutor(max_workers=threads) as ex:
        futs = {ex.submit(_safe, worker, it): it for it in items}
        for f, it in futs.items():
            out.append((it, f.result()))
    return out


def _safe(fn, arg):
    try: return fn(arg)
    except Exception as e:
        log('    worker EXC', type(e).__name__, str(e)[:120]); return None


if __name__ == '__main__':
    import sys
    for u in sys.argv[1:]:
        b = smart_get(u, respect_quarantine=False)
        print(u, '->', 'NOT MODIFIED' if b is NOT_MODIFIED else (len(b) if b else 'FAILED'))
    n304, nok = savings()
    print('answered 304:', n304, '| bodies fetched:', nok)
