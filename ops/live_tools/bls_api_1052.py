#!/usr/bin/env python3
"""LIVE TOOLS ON GITHUB (collection 1052, 15 Nov 2026; no AI): the BLS series the State page and the stress map read, kept current in the
runner from the BLS Public Data API v2 (api.bls.gov; the repository secret BLS_API_KEY). The BLS flat-file site (download.bls.gov) refuses
unnamed clients, so the runner does not read it.

It keeps, in the mirror of the Mac's folders, the same files the Mac's 191 standing collector keeps, in the same flat-file format
(series_id, year, period, value, footnote_codes; tab separated, gzip), reduced to the series the tools read:
  ces_all.txt.gz                  CES{ss}00000001             national payrolls by supersector, SA (12; stress map industry panel)
  state_metro_payrolls_all.txt.gz SMS{fips}00000{ss}00000001  State payrolls by supersector, SA (51 x 13; stress map; State payroll fallback)
  laus_all_states_sa.txt.gz       LASST{fips}0000000000003    State unemployment rates, SA (51; fallback of state_inputs_refresh_1052.py)
  laus_county.txt.gz              LAUCN{fips5}000000000{03,06} county unemployment rate and labour force (stress map county layer)
History comes from the seed (the Mac's flat files on the day of the port). Each run asks the API for the last WINDOW years of every series
(one request per 50 series; the API allows 20 years per request) and replaces those years of a series only when the API's newest month is
no earlier than the held one; every older row is kept as held (add-only below the window). County LAUS is asked only when its sentinel
series has a month newer than the file holds (or --county): it takes ~126 of the 500 requests a key may make in a day.
Writes $LT_OUT/bls_api_1052.json. Exit 0 unless --strict and a request failed."""
import os, sys, io, json, gzip, time, argparse, urllib.request, datetime as dt
ROOT = os.path.expanduser('~/Projects/Onset Detector Data')
W191 = os.path.join(ROOT, '191_standing_collector_2026-09-16/warehouse/bls_flat_files')
LAUS_HELD = os.path.join(ROOT, '1032_state_recession_indicator_all_states_dc_2026-11-09/data/laus_county/county_ur_lf_1990_2026.csv.gz')
API = 'https://api.bls.gov/publicAPI/v2/timeseries/data/'
FIPS = ['01', '02', '04', '05', '06', '08', '09', '10', '11', '12', '13', '15', '16', '17', '18', '19', '20', '21', '22', '23', '24', '25', '26', '27', '28', '29', '30',
        '31', '32', '33', '34', '35', '36', '37', '38', '39', '40', '41', '42', '44', '45', '46', '47', '48', '49', '50', '51', '53', '54', '55', '56']
SUPER = ['00', '10', '20', '15', '30', '40', '50', '55', '60', '65', '70', '80', '90']   # stress_map_v2_1052.SUPER codes
SENTINEL = 'LAUCN060370000000003'   # Los Angeles County unemployment rate
HDR = 'series_id\tyear\tperiod\tvalue\tfootnote_codes\n'
OUTD = os.environ.get('LT_OUT') or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
def log(*a): print(time.strftime('%H:%M:%S'), *a, flush=True)

def key():
    k = os.environ.get('BLS_API_KEY', '').strip()
    if not k: print('BLS_API_KEY is not set: the shared layer goes to its fallbacks')
    return k

def ask(sids, y0, y1, k, latest=False):
    """one request's worth (<= 50 series): {sid: [(year, period, value, footnotes)]} and the 'no data' notes. Through the shared BLS layer
    (data/105.../workspace/s2/bls_fetch.py, 16 Nov 2026): the key, a second key, API v1, the BLS flat files, FRED - each used only where it
    was proven equal to the API; the source of every series is printed with the run. `k` is kept for the callers."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', '105_bristow_hall_system_2026-09-08', 'workspace', 's2'))
    import bls_fetch
    d, served = bls_fetch.fetch(list(sids), y0 or None, y1 or None, latest=latest, fresh=latest)
    if not d: raise RuntimeError('BLS: no source answered (%s)' % '; '.join(bls_fetch.LOG[-3:]))
    out = {s: [(int(y), p, v, fn) for y, p, v, fn in rows] for s, rows in d.items()}
    return out, ['%s: no data' % s for s in sids if not out.get(s)][:5]

def read_flat(path):
    rows = {}
    if not os.path.exists(path): return rows
    with gzip.open(path, 'rt', encoding='latin-1') as f:
        next(f, None)
        for line in f:
            q = line.rstrip('\n').split('\t')
            if len(q) < 4: continue
            rows.setdefault(q[0].strip(), []).append((int(q[1]), q[2].strip(), q[3].strip(), q[4].strip() if len(q) > 4 else ''))
    return rows

def write_flat(path, rows):
    buf = io.StringIO(); buf.write(HDR)
    for s in sorted(rows):
        for y, p, v, fn in sorted(rows[s], key=lambda r: (r[0], r[1])): buf.write(f'{s}\t{y}\t{p}\t{v}\t{fn}\n')
    tmp = path + '.tmp'; os.makedirs(os.path.dirname(path), exist_ok=True)
    with gzip.open(tmp, 'wt', encoding='latin-1', compresslevel=6) as f: f.write(buf.getvalue())
    os.replace(tmp, path)

def newest(rs): return max(((y, p) for y, p, v, fn in rs if v not in ('', '-')), default=(0, ''))

def refresh(name, sids, y0, y1, k, R):
    path = os.path.join(W191, name); held = read_flat(path); got = {}; msgs = []; nreq = 0
    for i in range(0, len(sids), 50):
        part, m = ask(sids[i:i + 50], y0, y1, k); got.update(part); msgs += m; nreq += 1
    changed = []; kept = []
    for s in sids:
        new = got.get(s) or []
        if not new: continue
        h = held.get(s, [])
        if h and newest(new) < newest([r for r in h if y0 <= r[0] <= y1]):
            kept.append(s); continue          # the API holds less than the file in the window: the held rows stay
        merged = [r for r in h if not (y0 <= r[0] <= y1)] + new
        if sorted(merged) != sorted(h): held[s] = merged; changed.append(s)
    if changed: write_flat(path, held)
    R[name] = dict(series=len(sids), requests=nreq, answered=sum(1 for s in sids if got.get(s)), changed=len(changed), kept_held=kept[:10],
                   newest=('%d-%s' % max((newest(held[s]) for s in sids if s in held), default=(0, ''))), messages=msgs[:5])
    log(name, R[name]); return bool(changed)

def county_fips():
    import pandas as pd
    return sorted(pd.read_csv(LAUS_HELD, dtype={'fips5': str}, usecols=['fips5']).fips5.unique())

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--window', type=int, default=5); ap.add_argument('--county', action='store_true', help='ask county LAUS even if the sentinel has no new month')
    ap.add_argument('--no-county', action='store_true'); ap.add_argument('--only', default=''); ap.add_argument('--strict', action='store_true'); a = ap.parse_args()
    k = key(); y1 = dt.date.today().year; y0 = y1 - a.window + 1; R = dict(run=time.strftime('%Y-%m-%dT%H:%M:%S%z'), window=[y0, y1]); ok = True
    jobs = [('ces_all.txt.gz', [f'CES{c}00000001' for c in SUPER if c != '15']),
            ('state_metro_payrolls_all.txt.gz', [f'SMS{f}00000{c}00000001' for f in FIPS for c in SUPER]),
            ('laus_all_states_sa.txt.gz', [f'LASST{f}0000000000003' for f in FIPS])]
    only = set(a.only.split(',')) if a.only else None
    for name, sids in jobs:
        if only and name not in only: continue
        try: R[name + '_changed'] = refresh(name, sids, y0, y1, k, R)
        except Exception as e: R[name] = dict(error=str(e)[:300]); ok = False; log(name, 'FAILED', e)
    if not a.no_county and (not only or 'laus_county.txt.gz' in only):
        try:
            cpath = os.path.join(W191, 'laus_county.txt.gz'); held = read_flat(cpath)
            if held.get(SENTINEL): hm = newest(held[SENTINEL])
            else:
                import pandas as pd
                m = str(pd.read_csv(LAUS_HELD, usecols=['month']).month.max()); hm = (int(m[:4]), 'M' + m[5:7])
            s, _ = ask([SENTINEL], 0, 0, k, latest=True); am = newest(s.get(SENTINEL, []))
            R['county_sentinel'] = dict(held='%d-%s' % hm, api='%d-%s' % am)
            if a.county or am > hm:
                fp = county_fips(); sids = [f'LAUCN{g}0000000003' for g in fp] + [f'LAUCN{g}0000000006' for g in fp]
                R['laus_county.txt.gz_changed'] = refresh('laus_county.txt.gz', sids, y0, y1, k, R)
            else: log('county LAUS: no new month (held %d-%s, API %d-%s); not asked' % (hm + am))
        except Exception as e: R['laus_county.txt.gz'] = dict(error=str(e)[:300]); ok = False; log('county FAILED', e)
    R['ok'] = ok; os.makedirs(OUTD, exist_ok=True); json.dump(R, open(os.path.join(OUTD, 'bls_api_1052.json'), 'w'), indent=1)
    return 1 if (a.strict and not ok) else 0

if __name__ == '__main__': sys.exit(main())
