#!/usr/bin/env python3
"""1150 (19 Nov 2026; no AI): the data behind the stress map's factor panel and county industry table. Run after stress_map_v2_1052.py --all.
Anthony, 19 Nov 2026: a county opens like a State (its unemployment and its industries), and the State view shows the factors the tool uses.
Reads (nothing new is computed; every number is a held input or an output of the map's own run):
  out/stress_map_v3_1_state_month.csv         State-month: labour_input (unemployment rate; before 1979-07 k x the insured rate), deviation_pp
  out/stress_map_v3_1_county_month.csv.gz     county-month: laus_ur, laus_lf, qcew_employment, deviation_pp
  1032 data/qcew_industry_county/<YEAR>.csv.gz   QCEW county jobs by industry (code/qcew_county_ind_refresh_1150.py)
  web/stress-map/index.html                   the built page (its month ranges and county list)
Writes web/stress-map/cf/<ST>.js (factors: the State's and each county's, one file per State), web/stress-map/ci/<fips>.js (jobs by
industry, one file per county) and out/stress_map_detail_1150.json (counts and the checks below). Deterministic: same inputs, same bytes.
Checks (exit 1 on a failure): 50 State files; a factor file for every county on the map; every county-month value written equals the value
in the county-month table; the industry total written equals the QCEW county total the map itself used wherever both are held."""
import os, re, sys, csv, gzip, json, glob, time
import numpy as np, pandas as pd
C = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); ROOT = os.path.dirname(C); OUT = os.path.join(C, 'out'); WEB = os.path.join(C, 'web', 'stress-map')
QD = os.path.join(ROOT, '1032_state_recession_indicator_all_states_dc_2026-11-09', 'data', 'qcew_industry_county')
CODES = ['10', 'gov', '1011', '1012', '1013', '1021', '1022', '1023', '1024', '1025', '1026', '1027', '1029']
NAMES = {'10': 'Total, all covered jobs', 'gov': 'Government', '1011': 'Natural resources and mining', '1012': 'Construction', '1013': 'Manufacturing', '1021': 'Trade, transportation, and utilities',
         '1022': 'Information', '1023': 'Financial activities', '1024': 'Professional and business services', '1025': 'Education and health services', '1026': 'Leisure and hospitality',
         '1027': 'Other services', '1029': 'Unclassified'}
def log(*a): print(time.strftime('%H:%M:%S'), *a, flush=True)
def ab(k): return int(k[:4]) * 12 + int(k[5:7]) - 1
def put(path, kind, key, obj):   # a script the page loads: __SMD.<kind>('<key>', {...}) (the page stays readable from disk)
    b = ('__SMD.%s(%s,%s);' % (kind, json.dumps(key), json.dumps(obj, separators=(',', ':')))).encode(); os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path) and open(path, 'rb').read() == b: return 0
    open(path + '.tmp1150', 'wb').write(b); os.replace(path + '.tmp1150', path); return 1
def ints(a, mul): return [None if not np.isfinite(v) else int(round(v * mul)) for v in a]
def main():
    h = open(os.path.join(WEB, 'index.html'), encoding='utf-8').read()
    J = json.loads(re.search(r'<script id="data" type="application/json">(.*?)</script>', h, re.S).group(1).replace('<\\/', '</')); V = J['v2']
    c0 = ab(V['cstart']); cn = V['cn']; s0 = ab(J['start']); sn = J['n']; R = dict(run=time.strftime('%Y-%m-%dT%H:%M:%S%z'), fail=[])
    S = pd.read_csv(os.path.join(OUT, 'stress_map_v3_1_state_month.csv'), dtype={'month': str})
    CM = pd.read_csv(os.path.join(OUT, 'stress_map_v3_1_county_month.csv.gz'), dtype={'fips': str, 'month': str}, usecols=['fips', 'st', 'month', 'qcew_employment', 'laus_ur', 'laus_lf', 'deviation_pp'])
    CM['i'] = CM.month.map(ab) - c0; CM = CM[(CM.i >= 0) & (CM.i < cn)]
    # ---- factors, one file per State
    wrote = 0; nc = 0; tot_e = {}
    for st in sorted(J['states']):
        x = S[S.st == st]; u = np.full(sn, np.nan); p = np.full(sn, np.nan); ix = (x.month.map(ab) - s0).values; ok = (ix >= 0) & (ix < sn)
        u[ix[ok]] = pd.to_numeric(x.labour_input, errors='coerce').values[ok]; p[ix[ok]] = pd.to_numeric(x.deviation_pp, errors='coerce').values[ok]
        F = dict(start=V['cstart'], n=cn, state=dict(start=J['start'], u=ints(u, 100), p=ints(p, 100)), c={})
        for f, g in CM[CM.st == st].groupby('fips'):
            a = {k: np.full(cn, np.nan) for k in 'ulep'}; i = g.i.values
            a['u'][i] = g.laus_ur.values; a['l'][i] = g.laus_lf.values; a['e'][i] = g.qcew_employment.values; a['p'][i] = g.deviation_pp.values
            F['c'][f] = dict(u=ints(a['u'], 10), l=ints(a['l'], 1), e=ints(a['e'], 1), p=ints(a['p'], 100)); tot_e[f] = a['e']; nc += 1
        wrote += put(os.path.join(WEB, 'cf', st + '.js'), 'cf', st, F)
    R['factor_files'] = len(glob.glob(os.path.join(WEB, 'cf', '*.js'))); R['factor_files_changed'] = wrote; R['counties_with_factors'] = nc
    # every county on the map has factors
    import base64
    mapc = []
    for st, b in V['st'].items(): mapc += json.loads(gzip.decompress(base64.b64decode(b)))['order']
    miss = sorted(set(mapc) - set(tot_e)); R['map_counties'] = len(mapc); R['map_counties_without_factors'] = miss[:20]
    if R['factor_files'] != 50: R['fail'].append('factor files %d, not 50' % R['factor_files'])
    if miss: R['fail'].append('%d map counties without factors' % len(miss))
    # ---- jobs by industry, one file per county
    files = sorted(glob.glob(os.path.join(QD, '*.csv.gz'))); A = {}; last = -1
    for pth in files:
        with gzip.open(pth, 'rt', newline='') as f:
            rd = csv.reader(f); next(rd)
            for fips, own, ind, y, q, m1, m2, m3, disc in rd:
                if ind == '10': key = '10' if own == '0' else ('gov' if own in '123' else None)
                else: key = ind if own == '5' else None
                if key is None: continue
                b = int(y) * 12 + (int(q) - 1) * 3 - c0
                if b < 0 or b + 2 >= cn + 12: continue
                d = A.setdefault(fips, {}).setdefault(key, {})
                for k, v in enumerate((m1, m2, m3)):
                    if key == 'gov':   # federal + State + local; withheld in any one of them = withheld
                        o = d.get(b + k, 0); d[b + k] = None if (o is None or disc == 'N') else o + int(v)
                    else: d[b + k] = None if disc == 'N' else int(v)
                if key == '10': last = max(last, b + 2)
    n_i = min(cn, last + 1); R['industry_months'] = n_i; R['industry_last'] = '%d-%02d' % ((c0 + n_i - 1) // 12, (c0 + n_i - 1) % 12 + 1) if n_i > 0 else None
    wrote = 0; have = 0; cells = 0; held_cells = 0; cmp_n = 0; cmp_bad = 0; bad_ex = []
    for f in sorted(mapc):
        d = A.get(f)
        if not d: continue
        have += 1; v = {}
        for c in CODES:
            s = d.get(c)
            if not s: v[c] = None; continue
            arr = [s.get(i) for i in range(n_i)]; v[c] = arr if any(x is not None for x in arr) else None
            cells += n_i; held_cells += sum(x is not None for x in arr)
        t = v.get('10'); e = tot_e.get(f)
        if t is not None and e is not None:
            for i in range(min(n_i, cn)):
                if t[i] is not None and np.isfinite(e[i]):
                    cmp_n += 1
                    if int(round(e[i])) != t[i]:
                        cmp_bad += 1
                        if len(bad_ex) < 10: bad_ex.append([f, '%d-%02d' % ((c0 + i) // 12, (c0 + i) % 12 + 1), t[i], float(e[i])])
        wrote += put(os.path.join(WEB, 'ci', f + '.js'), 'ci', f, dict(start=V['cstart'], n=n_i, last=R['industry_last'], codes=CODES, names=NAMES, v=v))
    stale = sorted(set(os.path.basename(x)[:-3] for x in glob.glob(os.path.join(WEB, 'ci', '*.js'))) - set(mapc))
    R.update(industry_files=have, industry_files_changed=wrote, map_counties_without_industry=sorted(set(mapc) - set(A))[:40], n_without_industry=len(set(mapc) - set(A)),
             industry_cells=cells, industry_cells_held=held_cells, total_compared_with_map_input=cmp_n, total_differs=cmp_bad, total_differs_examples=bad_ex, files_not_on_the_map=stale[:10])
    if not files: R['fail'].append('no county industry file held')
    if cmp_n == 0: R['fail'].append('no industry total could be compared with the map input')
    R['ok'] = not R['fail']; json.dump(R, open(os.path.join(OUT, 'stress_map_detail_1150.json'), 'w'), indent=1); log(json.dumps({k: v for k, v in R.items() if not isinstance(v, list) or len(v) < 12}))
    return 0 if R['ok'] else 1
if __name__ == '__main__': sys.exit(main())
