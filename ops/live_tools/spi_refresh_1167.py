#!/usr/bin/env python3
"""THE STATE PRODUCTION INDEX, REFRESHED (collection 1167, limit 3 of Paper 3; 24 November 2026). No AI.

The State grade's third dimension (production) reads 1032 data/spi/spi_state_monthly_benchmarked_1167.csv. Each run:
  1. the index's monthly inputs are refreshed from 2019 on: State jobs in manufacturing, mining and logging, and utilities (BLS State
     series, not seasonally adjusted), national jobs in the same three industries (BLS CES) - all through the shared BLS layer - and
     national industrial production of the same industries (Federal Reserve G.17, through FRED);
  2. the index is rebuilt by the collection's own two scripts, unchanged (spi_1167.py, then spi_bench_1167.py: the Denton benchmark to
     BEA real output of the three industries by State), in the working copy 1032 data/spi/work;
  3. the file is replaced only if every check below holds; otherwise the held file stays and the step says why (exit code 1).
Checks: a refreshed series agrees with the held one on months both hold that are more than 36 months old (median relative difference
under 0.1%; else that series keeps its held values); every State is in the new index; its last month is not earlier than the held one;
on 1979-2018 the new and held monthly log changes correlate at 0.99 or more in every State.
    python3 ops/live_tools/spi_refresh_1167.py"""
import os, sys, json, time, subprocess, urllib.request, datetime, numpy as np, pandas as pd
P = '/Users/anthonyhall/Projects/Onset Detector Data'; D = os.path.join(P, '1032_state_recession_indicator_all_states_dc_2026-11-09')
WORK = os.path.join(D, 'data', 'spi', 'work'); FRED = os.path.join(WORK, 'data', 'l3', 'fred')
LIVE = os.path.join(D, 'data', 'spi', 'spi_state_monthly_benchmarked_1167.csv'); Y0 = 2019
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIPS = {'AL': '01', 'AK': '02', 'AZ': '04', 'AR': '05', 'CA': '06', 'CO': '08', 'CT': '09', 'DE': '10', 'FL': '12', 'GA': '13', 'HI': '15', 'ID': '16',
        'IL': '17', 'IN': '18', 'IA': '19', 'KS': '20', 'KY': '21', 'LA': '22', 'ME': '23', 'MD': '24', 'MA': '25', 'MI': '26', 'MN': '27', 'MS': '28', 'MO': '29',
        'MT': '30', 'NE': '31', 'NV': '32', 'NH': '33', 'NJ': '34', 'NM': '35', 'NY': '36', 'NC': '37', 'ND': '38', 'OH': '39', 'OK': '40', 'OR': '41', 'PA': '42',
        'RI': '44', 'SC': '45', 'SD': '46', 'TN': '47', 'TX': '48', 'UT': '49', 'VT': '50', 'VA': '51', 'WA': '53', 'WV': '54', 'WI': '55', 'WY': '56'}
BLS_OF = {'MANEMP': 'CES3000000001', 'USMINE': 'CES1021000001', 'CES4422000001': 'CES4422000001'}
for _s, _f in FIPS.items():
    BLS_OF[_s + 'MFGN'] = 'SMU%s000003000000001' % _f; BLS_OF[_s + 'NRMNN'] = 'SMU%s000001000000001' % _f
    BLS_OF['SMU%s000004322000001' % _f] = 'SMU%s000004322000001' % _f
FRED_ONLY = ['IPMAN', 'IPMINE', 'IPUTIL', 'INDPRO']
def say(*a): print(time.strftime('%H:%M:%S'), *a, flush=True)

def held(fid):
    f = os.path.join(FRED, fid + '.csv')
    if not os.path.exists(f): return None
    x = pd.read_csv(f); return pd.Series(pd.to_numeric(x.iloc[:, 1], errors='coerce').values, index=pd.to_datetime(x.iloc[:, 0])).dropna()

def write(fid, s):
    tmp = os.path.join(FRED, fid + '.csv.tmp')
    with open(tmp, 'w') as fh:
        fh.write('observation_date,%s\n' % fid); fh.writelines('%s,%s\n' % (d.strftime('%Y-%m-%d'), ('%.10g' % v)) for d, v in s.items())
    os.replace(tmp, os.path.join(FRED, fid + '.csv'))

def splice(fid, new, why):
    """held months before the fetched span kept; fetched months replace or extend the rest; refused if the overlap disagrees"""
    h = held(fid)
    if h is None or new is None or not len(new): why[fid] = 'nothing fetched (held kept)'; return False
    old = pd.Timestamp.today().normalize() - pd.DateOffset(months=36); j = h.index.intersection(new.index); j = j[j < old]
    if len(j):
        rel = float(np.median(np.abs(new[j].values / h[j].values - 1)))
        if rel >= 0.001: why[fid] = 'overlap disagrees (median relative difference %.4f; held kept)' % rel; return False
    s = pd.concat([h[h.index < new.index[0]], new]).sort_index(); s = s[~s.index.duplicated(keep='last')]
    if s.equals(h): return False
    write(fid, s); return True

def bls(ids):
    sys.path.insert(0, os.path.join(REPO, 'data', '105_bristow_hall_system_2026-09-08', 'workspace', 's2')); import bls_fetch
    d, served = bls_fetch.fetch(list(ids), Y0, datetime.date.today().year, chain=('bls_v2_key1', 'bls_v2_key2', 'bls_v1', 'bls_flat'))
    out = {}
    for sid, rows in d.items():
        r = {pd.Timestamp('%s-%s-01' % (y, p[1:])): float(v) for y, p, v, _ in rows if p != 'M13' and v not in ('', '-')}
        if r: out[sid] = pd.Series(r).sort_index()
    return out, served

def fred(fid):
    url = 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=%s&cosd=%d-01-01' % (fid, Y0)
    for k in range(2):
        try:
            b = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=60).read().decode()
            x = [ln.split(',') for ln in b.strip().splitlines()[1:]]
            s = pd.Series({pd.Timestamp(a): float(v) for a, v in x if v not in ('', '.')}).sort_index()
            if len(s): return s
        except Exception as e: err = e; time.sleep(5)
    return None

def main():
    if not os.path.isdir(FRED): say('no working copy at', WORK); return 1
    why = {}; changed = 0
    want = {fid: sid for fid, sid in BLS_OF.items() if held(fid) is not None}
    got, served = bls(sorted(set(want.values())))
    for fid, sid in want.items(): changed += splice(fid, got.get(sid), why)
    for fid in FRED_ONLY: changed += splice(fid, fred(fid), why)
    say('series refreshed: %d changed of %d; not refreshed: %d' % (changed, len(want) + len(FRED_ONLY), len(why)))
    for k, v in sorted(why.items()): say('  ', k, v)
    for sc in ('spi_1167.py', 'spi_bench_1167.py'):
        r = subprocess.run([sys.executable, '-I', os.path.join(WORK, 'code', sc), WORK], capture_output=True, text=True)
        if r.returncode: say(sc, 'failed:', r.stderr[-800:]); return 1
    new = pd.read_csv(os.path.join(WORK, 'data', 'l3', 'spi_state_monthly_benchmarked_1167.csv'), index_col=0, parse_dates=True)
    old = pd.read_csv(LIVE, index_col=0, parse_dates=True); bad = []
    for st in old.columns:
        if st not in new.columns or new[st].dropna().empty: bad.append(st + ' missing'); continue
        if new[st].dropna().index[-1] < old[st].dropna().index[-1]: bad.append(st + ' ends earlier')
        a = np.log(new[st]).diff(); b = np.log(old[st]).diff(); j = a.dropna().index.intersection(b.dropna().index); j = j[(j >= '1979-01-01') & (j <= '2018-12-01')]
        if len(j) > 24 and float(np.corrcoef(a[j], b[j])[0, 1]) < 0.99: bad.append(st + ' history changed')
    if bad: say('checks failed (held file kept):', '; '.join(bad)); return 1
    if new.round(4).equals(old.round(4)): say('index unchanged, through', str(new.index[-1])[:7]); return 0
    tmp = LIVE + '.tmp'; new.to_csv(tmp); os.replace(tmp, LIVE)
    say('index replaced: %s..%s, %d States (held ended %s)' % (str(new.index[0])[:7], str(new.index[-1])[:7], new.shape[1], str(old.index[-1])[:7]))
    json.dump(dict(at=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), through=str(new.index[-1])[:7], served=sorted(set(served.values())), not_refreshed=why),
              open(os.path.join(D, 'data', 'spi', 'spi_refresh_1167.json'), 'w'), indent=1)
    return 0

if __name__ == '__main__':
    sys.exit(main())
