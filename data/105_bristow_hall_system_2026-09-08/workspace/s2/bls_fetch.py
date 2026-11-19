# -*- coding: utf-8 -*-
"""ONE BLS FETCH LAYER FOR EVERY JOB, WITH ITS FALLBACKS (speed program 1052; Anthony 16 Nov 2026 04:02 PT: hitting the BLS daily limit
must never stop live updating). No AI. Standard library only.

    fetch(ids, y0, y1)  ->  ({series id: [(year, 'Mmm', value text, footnote codes)]}, {series id: the source that served it})

Every series asked goes down this chain until a source answers for it; a refusal (the daily threshold, any error) moves to the next:
  1  bls_v2_key1   BLS API v2 with BLS_API_KEY (50 series, 20 years a request)
  2  bls_v2_key2   BLS API v2 with BLS_API_KEY_2, when that secret exists
  3  bls_v1        BLS API v1, no key (25 series, 10 years a request; its own allowance per address)
  4  bls_flat      the BLS flat files at download.bls.gov/pub/time.series/<survey>/ (ln, ce, sm, la, cu, jt), downloaded whole once per
                   run with a User-Agent carrying a contact address (BLS_CONTACT: the BLS refuses anonymous agents) and parsed
  5  fred          FRED (fredgraph), for a series with a FRED id registered by the job (register_fred); marked, and the source gate still
                   verifies every published figure
A fallback (3-5) serves a series only if the parity record (ops/state/bls_fallback_parity.json, written by `python3 s2/bls_fetch.py
parity`: the fallback against the BLS API v2 on the last 24 months of every series the jobs use) lists that series' survey for it as
equal. Never mixed silently: the source that served each series is returned, kept in SERVED and printed with the run.

Usage is cut and counted: each request is answered once per run (BLS_CACHE_DIR, shared by the scripts of one run, 30 minutes); requests
carry 50 series; every API request is counted per key and per Eastern day in $BLS_USAGE (default ops/state/bls_usage.json) and the phone
hears once a day when a key passes 80% of its 500 (ALERT_NTFY_TOPIC or NTFY_TOPIC)."""
import os, io, re, sys, json, time, hashlib, datetime, threading, urllib.request, urllib.error

V2 = 'https://api.bls.gov/publicAPI/v2/timeseries/data/'
V1 = 'https://api.bls.gov/publicAPI/v1/timeseries/data/'
FLATURL = 'https://download.bls.gov/pub/time.series/%s/%s'
DAILY = 500
HERE = os.path.dirname(os.path.abspath(__file__)); WS = os.path.dirname(HERE); ROOT = os.path.abspath(os.path.join(WS, '..', '..', '..'))
USAGE = os.environ.get('BLS_USAGE') or os.path.join(ROOT, 'ops', 'state', 'bls_usage.json')
PARITY_FILE = os.path.join(ROOT, 'ops', 'state', 'bls_fallback_parity.json')
CACHE_DIR = os.environ.get('BLS_CACHE_DIR') or os.path.join(os.environ.get('RUNNER_TEMP') or '/tmp', 'bls_cache')
_LOCK = threading.RLock(); _FLAT = {}; SERVED = {}; LOG = []
FRED_OF = {}
CHAIN = ('bls_v2_key1', 'bls_v2_key2', 'bls_v1', 'bls_flat', 'fred')


def register_fred(m):
    """the FRED id of BLS series a job knows (FRED republishes them unchanged): {BLS id: FRED id}"""
    FRED_OF.update(m)


def _env(name):
    v = os.environ.get(name, '').strip()
    if v: return v
    env = os.path.join(os.path.expanduser('~'), 'mnt', 'Onset Detector Data', 'onset-detector-new-2026-08-23', 'live_data', 'config', 'local.env')
    try:
        for ln in open(env):
            if ln.startswith(name + '='): return ln.strip().split('=', 1)[1].strip().strip('"').strip("'")
    except Exception: pass
    return ''


def _redact(s):
    s = str(s)
    for k in (_env('BLS_API_KEY'), _env('BLS_API_KEY_2'), _env('BLS_CONTACT')):
        if k: s = s.replace(k, '[redacted]')
    return s


def _eastern_day():
    from zoneinfo import ZoneInfo
    return datetime.datetime.now(ZoneInfo('America/New_York')).date().isoformat()


def _count(keyname, n=1):
    """n more requests on `keyname` today (Eastern day); an alert once a day at 80% of a key's allowance"""
    day = _eastern_day()
    with _LOCK:
        try: U = json.load(open(USAGE))
        except Exception: U = {}
        if U.get('day') != day: U = {'day': day, 'requests': {}, 'alerted': {}, 'refused': {}}
        U['requests'][keyname] = U['requests'].get(keyname, 0) + n
        c = U['requests'][keyname]
        if keyname.startswith('bls_v2') and c >= 0.8 * DAILY and not U['alerted'].get(keyname):
            U['alerted'][keyname] = True
            _alert('BLS key %s: %d of its %d requests today counted here (80%%); the fallbacks take over when it is refused' % (keyname, c, DAILY))
        _save_usage(U)
        return c


def _refused(keyname, why):
    with _LOCK:
        try: U = json.load(open(USAGE))
        except Exception: U = {}
        if U.get('day') != _eastern_day(): U = {'day': _eastern_day(), 'requests': {}, 'alerted': {}, 'refused': {}}
        first = keyname not in U.setdefault('refused', {})
        U['refused'][keyname] = _redact(why)[:200]
        _save_usage(U)
    if first: _alert('BLS %s refused today (%s); the next source in the chain serves' % (keyname, _redact(why)[:120]))


def _save_usage(U):
    try:
        os.makedirs(os.path.dirname(USAGE), exist_ok=True); tmp = USAGE + '.%d.tmp' % os.getpid()
        json.dump(U, open(tmp, 'w'), indent=1); os.replace(tmp, USAGE)
    except OSError: pass


def _refused_today(keyname):
    try:
        U = json.load(open(USAGE)); return U.get('day') == _eastern_day() and keyname in (U.get('refused') or {})
    except Exception: return False


def _alert(msg):
    LOG.append('ALERT ' + msg); print('bls_fetch: ' + msg, flush=True)
    topic = os.environ.get('ALERT_NTFY_TOPIC') or os.environ.get('NTFY_TOPIC')
    if not topic: return
    try: urllib.request.urlopen(urllib.request.Request('https://ntfy.sh/' + topic, data=msg.encode(), headers={'Title': 'Bristow-Hall: BLS allowance'}), timeout=20).read()
    except Exception: pass


class Refused(RuntimeError):
    """the source refused (the daily threshold, a bad or missing key): the chain moves on and the source is not asked again today"""


def _ua():
    c = _env('BLS_CONTACT')
    return 'bristow-hall-live data reader (https://github.com/anthonythomashall3-rgb/bristow-hall-live%s)' % ('; ' + c if c else '')


def _cache(name, fn, fresh=False):
    """the answer of one request, once per run (shared by the scripts of the run through CACHE_DIR, 30 minutes); fresh: ask again (a
    release-time poll must see the new month the moment it is out), and keep the new answer for the rest of the run"""
    h = hashlib.sha256(name.encode()).hexdigest()[:24]; p = os.path.join(CACHE_DIR, h + '.json')
    try:
        if not fresh and time.time() - os.path.getmtime(p) < 1800: return {k: [tuple(r) for r in v] for k, v in json.load(open(p)).items()}
    except Exception: pass
    out = fn()
    try:
        os.makedirs(CACHE_DIR, exist_ok=True); tmp = p + '.%d.tmp' % os.getpid(); json.dump(out, open(tmp, 'w')); os.replace(tmp, p)
    except OSError: pass
    return out


def survey(sid):
    return sid[:2].lower()


# ------------------------------------------------------------------------------------------------------------- 1-3 the API
def _api(version, keyname, key, ids, y0, y1, latest=False, fresh=False):
    url = V2 if version == 2 else V1
    per, span = (50, 20) if version == 2 else (25, 10)
    out = {}
    spans = [(None, None)] if latest else [(y, min(y + span - 1, y1)) for y in range(y0, y1 + 1, span)]
    for i in range(0, len(ids), per):
        for a, b in spans:
            body = {'seriesid': ids[i:i + per]}
            if latest: body['latest'] = True
            else: body.update(startyear=str(a), endyear=str(b))
            if key: body['registrationkey'] = key
            def one():
                last = None
                for t in range(3):
                    try:
                        _count(keyname)
                        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json', 'User-Agent': _ua()})
                        with urllib.request.urlopen(req, timeout=90) as r: J = json.load(r)
                    except Exception as e:
                        last = e; time.sleep(5 * (t + 1)); continue
                    if J.get('status') != 'REQUEST_SUCCEEDED':
                        msg = ' '.join(str(m) for m in (J.get('message') or [J.get('status')]))
                        if re.search(r'threshold|key|daily|exceed', msg, re.I): raise Refused(_redact(msg))
                        last = RuntimeError(_redact(msg)); time.sleep(5 * (t + 1)); continue
                    got = {s: [] for s in body['seriesid']}
                    for s in J['Results']['series']:
                        got[s['seriesID']] = [(int(d['year']), d['period'], str(d['value']).strip(), ','.join(f.get('code', '') for f in d.get('footnotes', []) if f and f.get('code')))
                                              for d in s.get('data', []) if d['period'][:1] == 'M' and d['period'] != 'M13']
                    return got
                raise RuntimeError('BLS API v%d: %s' % (version, _redact(last)))
            got = _cache('api%d|%s|%s|%s|%s' % (version, ','.join(body['seriesid']), a, b, latest), one, fresh)
            for s, rows in got.items(): out.setdefault(s, []).extend(rows)
    return out


# ------------------------------------------------------------------------------------------------------------- 4 the flat files
_STATE_NAME = {'01': 'Alabama', '02': 'Alaska', '04': 'Arizona', '05': 'Arkansas', '06': 'California', '08': 'Colorado', '09': 'Connecticut', '10': 'Delaware',
               '11': 'DistrictOfColumbia', '12': 'Florida', '13': 'Georgia', '15': 'Hawaii', '16': 'Idaho', '17': 'Illinois', '18': 'Indiana', '19': 'Iowa',
               '20': 'Kansas', '21': 'Kentucky', '22': 'Louisiana', '23': 'Maine', '24': 'Maryland', '25': 'Massachusetts', '26': 'Michigan', '27': 'Minnesota',
               '28': 'Mississippi', '29': 'Missouri', '30': 'Montana', '31': 'Nebraska', '32': 'Nevada', '33': 'NewHampshire', '34': 'NewJersey', '35': 'NewMexico',
               '36': 'NewYork', '37': 'NorthCarolina', '38': 'NorthDakota', '39': 'Ohio', '40': 'Oklahoma', '41': 'Oregon', '42': 'Pennsylvania', '44': 'RhodeIsland',
               '45': 'SouthCarolina', '46': 'SouthDakota', '47': 'Tennessee', '48': 'Texas', '49': 'Utah', '50': 'Vermont', '51': 'Virginia', '53': 'Washington',
               '54': 'WestVirginia', '55': 'Wisconsin', '56': 'Wyoming'}


def _listing(s):
    if ('list', s) in _FLAT: return _FLAT[('list', s)]
    req = urllib.request.Request(FLATURL % (s, ''), headers={'User-Agent': _ua()})
    with urllib.request.urlopen(req, timeout=60) as r: t = r.read().decode('utf-8', 'replace')
    names = sorted(set(re.findall(r'(%s\.data\.[A-Za-z0-9.]+)' % s, t)))
    if not names: raise RuntimeError('BLS flat files: no listing for %s (the agent refused?)' % s)
    _FLAT[('list', s)] = names; return names


def flat_files(sid):
    """the flat file(s) that carry a series"""
    s = survey(sid)
    if s == 'ln': return ['ln.data.1.AllData']
    if s == 'cu': return ['cu.data.1.AllItems']
    if s == 'jt': return ['jt.data.1.AllItems']
    if s == 'la':
        return {'LASST': ['la.data.3.AllStatesS'], 'LAUST': ['la.data.2.AllStatesU'], 'LAUCN': ['la.data.64.County']}.get(sid[:5], [])
    if s == 'ce':
        if sid[5:11] == '000000' and sid[11:13] == '01':
            try: f = [n for n in _listing('ce') if n.startswith('ce.data.%sa.' % sid[3:5]) and n.endswith('Employment')]
            except Exception: f = []
            if f: return f
        return ['ce.data.0.AllCESSeries']
    if s == 'sm':
        nm = _STATE_NAME.get(sid[3:5])
        try: f = [n for n in _listing('sm') if nm and re.fullmatch(r'sm\.data\.\d+[a-z]?\.%s' % nm, n)]
        except Exception: f = []
        return f or ['sm.data.1.AllData']
    return []


def _flat_read(fname, want):
    """{series id: [(year, period, value, footnotes)]} for the wanted series of one flat file (streamed; whole file read once per run)"""
    have = _FLAT.setdefault(fname, {})
    need = [w for w in want if w not in have]
    if need:
        needset = set(need); s = fname.split('.')[0]
        req = urllib.request.Request(FLATURL % (s, fname), headers={'User-Agent': _ua()})
        with urllib.request.urlopen(req, timeout=600) as r:
            for raw in io.TextIOWrapper(r, encoding='utf-8', errors='replace'):
                p = raw.split('\t')
                if len(p) < 4: continue
                k = p[0].strip()
                if k not in needset: continue
                per = p[2].strip()
                if per[:1] != 'M' or per == 'M13': continue
                have.setdefault(k, []).append((int(p[1]), per, p[3].strip(), p[4].strip() if len(p) > 4 else ''))
        for w in need: have.setdefault(w, [])
    return {w: have.get(w, []) for w in want}


def _flat(ids, y0, y1, latest=False):
    by = {}
    for i in ids:
        for f in flat_files(i)[:1] if not survey(i) == 'sm' else flat_files(i):
            by.setdefault(f, []).append(i)
    out = {}
    for f, ws in by.items():
        for k, rows in _flat_read(f, ws).items():
            if rows: out.setdefault(k, []).extend(rows)
    for k in list(out):
        rows = sorted(set(r for r in out[k] if (y0 is None or y0 <= r[0] <= (y1 or 9999))), key=lambda r: (r[0], r[1]), reverse=True)
        out[k] = rows[:1] if latest else rows
    return out


# ------------------------------------------------------------------------------------------------------------- 5 FRED
def _fred(ids, y0, y1, latest=False):
    out = {}
    for i in ids:
        f = FRED_OF.get(i)
        if not f: continue
        req = urllib.request.Request('https://fred.stlouisfed.org/graph/fredgraph.csv?id=' + f, headers={'User-Agent': 'Python-urllib'})
        with urllib.request.urlopen(req, timeout=60) as r: t = r.read().decode()
        rows = []
        for ln in t.splitlines()[1:]:
            d, v = (ln.split(',') + [''])[:2]
            if not re.match(r'\d{4}-\d\d-01$', d) or v in ('', '.'): continue
            y = int(d[:4])
            if y0 is None or y0 <= y <= y1: rows.append((y, 'M' + d[5:7], v, ''))
        rows.sort(reverse=True)
        out[i] = rows[:1] if latest else rows
    return out


# ------------------------------------------------------------------------------------------------------------- the chain
_PAR = None


def _parity():
    global _PAR
    if _PAR is None:
        try: _PAR = json.load(open(PARITY_FILE))
        except Exception: _PAR = {}
    return _PAR


def eligible(src, sid):
    """a fallback serves a series only where the parity record found it equal to the BLS API (v1 and the flat files by survey, FRED by
    series)"""
    if src in ('bls_v2_key1', 'bls_v2_key2'): return True
    P = _parity().get(src) or {}
    if src == 'fred': return bool(P.get('series', {}).get(sid))
    return bool(P.get('surveys', {}).get(survey(sid))) and not P.get('series_bad', {}).get(sid)


def fetch(ids, y0=None, y1=None, latest=False, chain=CHAIN, fresh=False):
    """({series: [(year, 'Mmm', value text, footnotes)], newest first}, {series: source}) for every series some source answered"""
    ids = list(dict.fromkeys(ids)); y1 = y1 or datetime.date.today().year; y0 = y0 or y1 - 1
    left = list(ids); data, served = {}, {}
    for src in chain:
        if not left: break
        try:
            if src in ('bls_v2_key1', 'bls_v2_key2'):
                key = _env('BLS_API_KEY' if src == 'bls_v2_key1' else 'BLS_API_KEY_2')
                if not key or _refused_today(src): continue
                got = _api(2, src, key, left, y0, y1, latest, fresh)
            else:
                use = [i for i in left if eligible(src, i)]
                if not use: continue
                if src == 'bls_v1':
                    if _refused_today(src): continue
                    got = _api(1, src, None, use, y0, y1, False, fresh)   # 10-year spans, several requests: the whole range asked
                    if latest: got = {k: sorted(v, key=lambda r: (r[0], r[1]), reverse=True)[:1] for k, v in got.items()}
                elif src == 'bls_flat':
                    if fresh: [_FLAT.pop(f, None) for i in use for f in flat_files(i)]
                    got = _flat(use, y0, y1, latest)
                else: got = _fred(use, y0, y1, latest)
        except Refused as e:
            _refused(src, e); LOG.append('%s refused: %s' % (src, _redact(e)[:160])); continue
        except Exception as e:
            LOG.append('%s failed: %s' % (src, _redact(e)[:160])); continue
        for k, rows in got.items():
            if k in left:
                data[k] = sorted(set(rows), key=lambda r: (r[0], r[1]), reverse=True); served[k] = src
        left = [i for i in left if i not in served]
    SERVED.update(served)
    by = {}
    for k, v in served.items(): by[v] = by.get(v, 0) + 1
    if any(v != 'bls_v2_key1' for v in served.values()) or left:
        print('bls_fetch: %d series - %s%s' % (len(ids), ', '.join('%d from %s' % (n, s) for s, n in sorted(by.items())),
                                               ('; %d unanswered' % len(left)) if left else ''), flush=True)
    return data, served


def series(ids, y0=None, y1=None, latest=False, chain=CHAIN, fresh=False):
    """{series: {'YYYY-MM': float}} (a month the BLS did not collect, printed '-', is left out)"""
    d, s = fetch(ids, y0, y1, latest, chain, fresh)
    out = {}
    for k, rows in d.items():
        m = {}
        for y, p, v, _ in rows:
            try: m['%d-%s' % (y, p[1:])] = float(v.replace(',', ''))
            except ValueError: pass
        out[k] = m
    return out


# ------------------------------------------------------------------------------------------------------------- parity
SUPER = ['00', '05', '06', '07', '08', '10', '15', '20', '30', '31', '32', '40', '41', '42', '43', '50', '55', '60', '65', '70', '80', '90']
FIPS = ['01', '02', '04', '05', '06', '08', '09', '10', '11', '12', '13', '15', '16', '17', '18', '19', '20', '21', '22', '23', '24', '25', '26', '27', '28',
        '29', '30', '31', '32', '33', '34', '35', '36', '37', '38', '39', '40', '41', '42', '44', '45', '46', '47', '48', '49', '50', '51', '53', '54', '55', '56']


def universe():
    """every BLS series the jobs read (the county LAUS sample: Los Angeles and 99 others spread over the States)"""
    u = {'CES0000000001', 'LNS14000000', 'LNS13000000', 'LNS13023621', 'JTS000000000000000JOL', 'JTS000000000000000QUR', 'CUSR0000SA0', 'CUUR0000SA0',
         'LAUCN060370000000003', 'LAUCN060370000000006'}
    for c in SUPER: u.add('CES%s00000001' % c)
    for f in FIPS:
        u.update({'LASST%s0000000000003' % f, 'LAUST%s0000000000003' % f, 'SMS%s000000000000001' % f, 'SMU%s000000000000001' % f})
        for c in SUPER: u.add('SMS%s00000%s00000001' % (f, c))
    for f in FIPS[::1][:50]:
        u.add('LAUCN%s0010000000003' % f)   # the first county of each State (001)
        u.add('LAUCN%s0030000000003' % f)
    return sorted(u)


def fred_map():
    """{BLS id: FRED id} for the series FRED republishes under its own name (the jobs' own maps)"""
    m = {'CES0000000001': 'PAYEMS', 'LNS14000000': 'UNRATE', 'LNS13000000': 'UNEMPLOY', 'LNS13023621': 'LNS13023621', 'JTS000000000000000JOL': 'JTSJOL',
         'JTS000000000000000QUR': 'JTSQUR', 'CUSR0000SA0': 'CPIAUCSL', 'CUUR0000SA0': 'CPIAUCNS', 'CES1000000001': 'USMINE', 'CES2000000001': 'USCONS',
         'CES3000000001': 'MANEMP', 'CES4000000001': 'USTPU', 'CES5000000001': 'USINFO', 'CES5500000001': 'USFIRE', 'CES6000000001': 'USPBS',
         'CES6500000001': 'USEHS', 'CES7000000001': 'USLAH', 'CES8000000001': 'USSERV', 'CES9000000001': 'USGOVT'}
    st = {'01': 'AL', '02': 'AK', '04': 'AZ', '05': 'AR', '06': 'CA', '08': 'CO', '09': 'CT', '10': 'DE', '11': 'DC', '12': 'FL', '13': 'GA', '15': 'HI', '16': 'ID',
          '17': 'IL', '18': 'IN', '19': 'IA', '20': 'KS', '21': 'KY', '22': 'LA', '23': 'ME', '24': 'MD', '25': 'MA', '26': 'MI', '27': 'MN', '28': 'MS', '29': 'MO',
          '30': 'MT', '31': 'NE', '32': 'NV', '33': 'NH', '34': 'NJ', '35': 'NM', '36': 'NY', '37': 'NC', '38': 'ND', '39': 'OH', '40': 'OK', '41': 'OR', '42': 'PA',
          '44': 'RI', '45': 'SC', '46': 'SD', '47': 'TN', '48': 'TX', '49': 'UT', '50': 'VT', '51': 'VA', '53': 'WA', '54': 'WV', '55': 'WI', '56': 'WY'}
    for f, a in st.items():
        m.update({'LASST%s0000000000003' % f: a + 'UR', 'LAUST%s0000000000003' % f: a + 'URN', 'SMS%s000000000000001' % f: a + 'NA', 'SMU%s000000000000001' % f: a + 'NAN'})
    return m


register_fred(fred_map())


def _last24(rows):
    m = {}
    for y, p, v, _ in rows:
        try: m['%d-%s' % (y, p[1:])] = float(v.replace(',', ''))
        except ValueError: pass
    ks = sorted(m)[-24:]
    return {k: m[k] for k in ks}


def parity():
    """each fallback against the BLS API v2 (key 1) on the last 24 months of every series the jobs use; writes PARITY_FILE"""
    U = universe(); y1 = datetime.date.today().year; y0 = y1 - 2
    base, served = fetch(U, y0, y1, chain=('bls_v2_key1', 'bls_v2_key2'))
    B = {k: _last24(v) for k, v in base.items() if v}
    rep = {'checked_utc': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'base': 'BLS API v2', 'series': len(B),
           'window': 'the last 24 months the API carries, per series'}
    def compare(name, got, ids):
        bad, eq, by = [], 0, {}
        for k in ids:
            if k not in B: continue
            g = _last24(got.get(k, [])); b = B[k]
            ok = bool(g) and all(g.get(m) == v for m, v in b.items())
            by.setdefault(survey(k), []).append(ok)
            if ok: eq += 1
            else: bad.append(k)
        return {'compared': eq + len(bad), 'equal': eq, 'surveys': {s: all(v) for s, v in by.items()}, 'series_bad': {k: True for k in bad},
                'bad_examples': bad[:20]}
    # v1: one request of up to 25 series per survey (its allowance is 25 requests a day per address)
    samp = {}
    for k in sorted(B): samp.setdefault(survey(k), []).append(k)
    v1 = {}
    for s, ks in samp.items():
        ks = ks[:25]
        try: v1.update(_api(1, 'bls_v1', None, ks, y1 - 2, y1))
        except Exception as e: rep.setdefault('errors', {})['bls_v1 ' + s] = _redact(e)[:200]
    rep['bls_v1'] = compare('bls_v1', v1, [k for ks in samp.values() for k in ks[:25]])
    try: fl = _flat(list(B), y0, y1)
    except Exception as e: fl = {}; rep.setdefault('errors', {})['bls_flat'] = _redact(e)[:200]
    rep['bls_flat'] = compare('bls_flat', fl, list(B))
    fr = {}
    for k in B:
        if k in FRED_OF:
            try: fr.update(_fred([k], y0, y1))
            except Exception as e: rep.setdefault('errors', {})['fred ' + k] = _redact(e)[:120]
    c = compare('fred', fr, [k for k in B if k in FRED_OF])
    c['series'] = {k: True for k in B if k in FRED_OF and k not in c['series_bad']}
    rep['fred'] = c
    os.makedirs(os.path.dirname(PARITY_FILE), exist_ok=True)
    json.dump(rep, open(os.environ.get('BLS_PARITY_OUT') or PARITY_FILE, 'w'), indent=1, sort_keys=True)
    for n in ('bls_v1', 'bls_flat', 'fred'):
        r = rep[n]; print('%-9s %d of %d series equal to the BLS API v2 on their last 24 months; surveys %s; not equal: %s' % (
            n, r['equal'], r['compared'], r['surveys'], r['bad_examples'][:8]))
    print('errors:', rep.get('errors')); print('API requests counted today:', json.load(open(USAGE)).get('requests') if os.path.exists(USAGE) else None)
    return rep


if __name__ == '__main__':
    if sys.argv[1:2] == ['parity']: parity()
    else: print(__doc__)
