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


def bundle():
    """{BLS id: [(date 'YYYY-MM-01', value text as the BLS prints it)]} for every series above, once per process"""
    with _LOCK:
        if _BUNDLE: return _BUNDLE
        f = os.environ.get('SF_BUNDLE')
        if f and os.path.exists(f) and time.time() - os.path.getmtime(f) < 1800:   # read once by 'bundle' for both scripts (this run)
            _BUNDLE.update({k: [tuple(r) for r in v] for k, v in json.load(open(f)).items()}); return _BUNDLE
        import urllib.request
        ids = sorted(set(BLS_OF.values())); key = bls_key(); got = {}
        for i in range(0, len(ids), 50):
            for y0, y1 in SPANS:
                body = {'seriesid': ids[i:i + 50], 'startyear': str(y0), 'endyear': str(y1)}
                if key: body['registrationkey'] = key
                for t in range(3):
                    try:
                        req = urllib.request.Request('https://api.bls.gov/publicAPI/v2/timeseries/data/', data=json.dumps(body).encode(),
                                                     headers={'Content-Type': 'application/json', 'User-Agent': 'bristow-hall live tools'})
                        d = json.load(urllib.request.urlopen(req, timeout=60))
                        if d.get('status') != 'REQUEST_SUCCEEDED': raise RuntimeError(d.get('status'))
                        break
                    except Exception:
                        if t == 2: d = {'Results': {'series': []}}
                        time.sleep(5 * (t + 1))
                for s in d['Results']['series']:
                    rows = got.setdefault(s['seriesID'], {})
                    for o in s['data']:
                        p = o['period']
                        if p[:1] != 'M' or p == 'M13' or o['value'] in ('-', ''): continue
                        rows['%s-%s-01' % (o['year'], p[1:])] = o['value']
        for k, v in got.items(): _BUNDLE[k] = sorted(v.items())
        if f:
            tmp = f + '.tmp'; json.dump(_BUNDLE, open(tmp, 'w')); os.replace(tmp, f)
        return _BUNDLE


def fredgraph_from_bls(url):
    """the bytes FRED's fredgraph.csv?id=<SID> would return, built from the BLS API; None when the BLS has no such series"""
    if 'fredgraph.csv?id=' not in url: return None
    sid = url.split('id=')[1].split('&')[0]
    b = BLS_OF.get(sid)
    if not b: return None
    rows = bundle().get(b)
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
        b = fredgraph_from_bls(url)
        if b is not None:
            first = b.split(b'\n', 2)[1][:10].decode()
            held = _first_held(cur.get('path', ''))
            if held is None or first <= held:
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
        b = fredgraph_from_bls(url)
        if b is not None:
            first = b.split(b'\n', 2)[1][:10].decode(); held = _first_held(cur.get('path', ''))
            if held is None or first <= held:
                REC['bls'] += 1; return b
            REC['why'][url.split('id=')[1]] = 'BLS history starts %s, the held file %s: FRED' % (first, held)
        REC['fred'] += 1; return real(url, tries)
    m.get = get; m.fred_replace = fred_replace
    sys.argv = [m.__file__]; return m.main()


if __name__ == '__main__':
    what = (sys.argv[1:] or ['both'])[0]
    t0 = time.time()
    try:
        if what == 'bundle': bundle(); rc = 0; print('state_fast bundle: %d BLS series' % len(_BUNDLE))
        elif what == 'inputs': rc = run_inputs()
        elif what == 'extra': rc = run_extra()
        else: raise SystemExit('inputs | extra')
    finally:
        print('state_fast %s: %d series from the BLS API, %d from FRED, %.0f s; %s' % (what, REC['bls'], REC['fred'], time.time() - t0, json.dumps(REC['why'])[:400]), flush=True)
    sys.exit(rc or 0)
