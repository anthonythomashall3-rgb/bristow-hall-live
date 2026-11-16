#!/usr/bin/env python3
"""THE STATE INPUTS FROM THE PUBLISHER, IN ONE PASS (speed program 1052, step 1 of the live-tools release run; 16 November 2026). No AI.

code/state_inputs_refresh_1052.py and code/state_extra_refresh_1052.py fetch 205 FRED series one by one (about 3.5 minutes together),
and FRED posts the BLS State release about three hours after the BLS: a live-tools run at the release read the old month. Every one
of those series is a BLS series FRED republishes unchanged:
    <ST>UR   = LASST<fips>0000000000003  (State unemployment rate, SA)      <ST>URN  = LAUST<fips>0000000000003 (NSA)
    <ST>NA   = SMS<fips>000000000000001  (State payrolls, SA, thousands)     <ST>NAN  = SMU<fips>000000000000001 (NSA)
    CPIAUCSL = CUSR0000SA0
This runs the two scripts UNCHANGED (their own main(), the same file logic, the same guards, the same dated copies) with one thing
replaced: the bytes their fredgraph request returns come from the BLS API v2 (all 205 series in about 25 requests, 50 series and 20
years each), in fredgraph's own layout. A series the BLS did not return, or whose BLS history starts after the held file's first
month, goes to FRED exactly as before. The two scripts run side by side. Parity (the BLS series against FRED's on every date):
ops/live_tools/state_fast_parity.py.
    python3 ops/live_tools/state_fast.py inputs|extra|both"""
import os, sys, io, json, time, datetime, threading, importlib.util
CODE = '/Users/anthonyhall/Projects/Onset Detector Data/1052_stress_map_fix_parse_collect_2026-11-12/code'
FIPS = {'AL': '01', 'AK': '02', 'AZ': '04', 'AR': '05', 'CA': '06', 'CO': '08', 'CT': '09', 'DE': '10', 'DC': '11', 'FL': '12', 'GA': '13', 'HI': '15', 'ID': '16',
        'IL': '17', 'IN': '18', 'IA': '19', 'KS': '20', 'KY': '21', 'LA': '22', 'ME': '23', 'MD': '24', 'MA': '25', 'MI': '26', 'MN': '27', 'MS': '28', 'MO': '29',
        'MT': '30', 'NE': '31', 'NV': '32', 'NH': '33', 'NJ': '34', 'NM': '35', 'NY': '36', 'NC': '37', 'ND': '38', 'OH': '39', 'OK': '40', 'OR': '41', 'PA': '42',
        'RI': '44', 'SC': '45', 'SD': '46', 'TN': '47', 'TX': '48', 'UT': '49', 'VT': '50', 'VA': '51', 'WA': '53', 'WV': '54', 'WI': '55', 'WY': '56'}
BLS_OF = {'CPIAUCSL': 'CUSR0000SA0'}
for _st, _f in FIPS.items():
    BLS_OF[_st + 'UR'] = 'LASST%s0000000000003' % _f; BLS_OF[_st + 'URN'] = 'LAUST%s0000000000003' % _f
    BLS_OF[_st + 'NA'] = 'SMS%s000000000000001' % _f; BLS_OF[_st + 'NAN'] = 'SMU%s000000000000001' % _f
SPANS = [(1939, 1958), (1959, 1978), (1979, 1998), (1999, 2018), (2019, datetime.date.today().year)]
_BUNDLE = {}; _LOCK = threading.Lock(); REC = dict(bls=0, fred=0, why={})


def bls_key():
    k = os.environ.get('BLS_API_KEY', '').strip()
    return k or None


def _fetch_span(ids, y0, y1, key=None):
    """{BLS id: {date: value text}} for one span, through the shared BLS layer (data/105.../workspace/s2/bls_fetch.py: the key, a second
    key, API v1, the BLS flat files - each where it was proven equal to the API); a series none of them answers goes to FRED in the
    scripts themselves, as before"""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', '105_bristow_hall_system_2026-09-08', 'workspace', 's2'))
    import bls_fetch
    d, served = bls_fetch.fetch(list(ids), y0, y1, chain=('bls_v2_key1', 'bls_v2_key2', 'bls_v1', 'bls_flat'))
    for s, src in served.items():
        if src != 'bls_v2_key1': REC['why'].setdefault('served by ' + src, 0); REC['why']['served by ' + src] += 1
    got = {}
    for s, rows in d.items():
        r = got.setdefault(s, {})
        for y, p, v, _ in rows:
            if v in ('-', ''): continue
            r['%s-%s-01' % (y, p[1:])] = v
    REC['bls_requests'] = REC.get('bls_requests', 0) + (len(ids) + 49) // 50
    return got


def spans(which):
    """{'y0-y1': {BLS id: {date: value text}}} for the asked spans, each read once per run (shared through $SF_BUNDLE by both scripts).
    The BLS key's daily allowance (500 requests) is shared by every job: a run with no new month asks only the newest span (5 requests)."""
    with _LOCK:
        f = os.environ.get('SF_BUNDLE')
        if not _BUNDLE and f and os.path.exists(f) and time.time() - os.path.getmtime(f) < 1800:
            _BUNDLE.update(json.load(open(f)))
        want = ['%d-%d' % s for s in which]; miss = [s for s in which if '%d-%d' % s not in _BUNDLE]
        if miss:
            ids = sorted(set(BLS_OF.values())); key = bls_key()
            for y0, y1 in miss: _BUNDLE['%d-%d' % (y0, y1)] = _fetch_span(ids, y0, y1, key)
            if f:
                tmp = f + '.tmp'; json.dump(_BUNDLE, open(tmp, 'w')); os.replace(tmp, f)
        return {k: _BUNDLE[k] for k in want}


def bundle():
    """every span (the whole history)"""
    return spans(SPANS)


def _series(b, which):
    out = {}
    for sp in spans(which).values(): out.update(sp.get(b, {}))
    return sorted(out.items())


def fredgraph_from_bls(url, start=None, held_path=None):
    """the bytes FRED's fredgraph.csv?id=<SID> would return, built from the BLS API, from `start` (the held file's first month: the held file
    is FRED's whole series, so FRED's own first month; the BLS can reach further back, e.g. DCURN); None when the BLS has no such series.
    With held_path: when the BLS's newest span carries exactly the held file's months and values (no new month, no revision in it), the held
    file itself is handed back (the script then finds it identical) and the older spans are not asked."""
    if 'fredgraph.csv?id=' not in url: return None
    sid = url.split('id=')[1].split('&')[0]
    b = BLS_OF.get(sid)
    if not b: return None
    if held_path and os.path.exists(held_path):
        recent = _series(b, [SPANS[-1]])
        if recent:
            y0 = '%d-01-01' % SPANS[-1][0]
            held = [ln.split(',') for ln in open(held_path).read().splitlines()[1:] if ln[:10] >= y0]
            try:
                same = len(held) == len(recent) and all(h[0][:10] == r[0] and float(h[1]) == float(r[1]) for h, r in zip(held, recent))
            except (ValueError, IndexError):
                same = False
            if same:
                REC['unchanged'] = REC.get('unchanged', 0) + 1
                txt = open(held_path).read().splitlines()
                return ('observation_date,%s\n' % sid + ''.join(ln + '\n' for ln in txt[1:])).encode()
    rows = [r for r in _series(b, SPANS) if start is None or r[0] >= start]
    if not rows: return None
    return ('observation_date,%s\n' % sid + ''.join('%s,%s\n' % r for r in rows)).encode()


def _load(name):
    sys.path.insert(0, CODE)
    spec = importlib.util.spec_from_file_location(name, os.path.join(CODE, name + '.py'))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def _first_held(path):
    try:
        with open(path) as f: f.readline(); return f.readline().split(',')[0][:10]
    except Exception: return None


def run_inputs():
    m = _load('state_inputs_refresh_1052')
    real = m.fetch; real_csv = m.refresh_csv
    cur = {}
    def refresh_csv(path, sid, flat):
        cur['path'] = path; return real_csv(path, sid, flat)
    def fetch(url, fresh_days=0):
        held = _first_held(cur.get('path', ''))
        b = fredgraph_from_bls(url, held, cur.get('path'))
        if b is not None:
            first = b.split(b'\n', 2)[1][:10].decode()
            if held is not None and first == held:
                REC['bls'] += 1; return b, None
            REC['why'][url.split('id=')[1]] = 'BLS history starts %s, the held file %s: FRED' % (first, held)
        REC['fred'] += 1; return real(url, fresh_days)
    m.fetch = fetch; m.refresh_csv = refresh_csv
    sys.argv = [m.__file__]; return m.main()


def run_extra():
    m = _load('state_extra_refresh_1052')
    real = m.get; real_fr = m.fred_replace
    cur = {}
    def fred_replace(path, sid):
        cur['path'] = path; return real_fr(path, sid)
    def get(url, tries=3):
        held = _first_held(cur.get('path', ''))
        b = fredgraph_from_bls(url, held, cur.get('path'))
        if b is not None:
            first = b.split(b'\n', 2)[1][:10].decode()
            if held is not None and first == held:
                REC['bls'] += 1; return b
            REC['why'][url.split('id=')[1]] = 'BLS history starts %s, the held file %s: FRED' % (first, held)
        REC['fred'] += 1; return real(url, tries)
    m.get = get; m.fred_replace = fred_replace
    sys.argv = [m.__file__]; return m.main()


if __name__ == '__main__':
    what = (sys.argv[1:] or ['both'])[0]
    t0 = time.time()
    try:
        if what == 'bundle': spans([SPANS[-1]]); rc = 0; print('state_fast: the newest span read (%d requests)' % REC.get('bls_requests', 0))
        elif what == 'inputs': rc = run_inputs()
        elif what == 'extra': rc = run_extra()
        else: raise SystemExit('inputs | extra')
    finally:
        print('state_fast %s: %d series from the BLS API, %d from FRED, %.0f s; %s' % (what, REC['bls'], REC['fred'], time.time() - t0, json.dumps(REC['why'])[:400]), flush=True)
    sys.exit(rc or 0)
