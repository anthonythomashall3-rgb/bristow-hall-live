"""A factor-free weekly state breadth leg (3 September 2026, night, fourth pass) - what the Paper 2 chat's
round-2 work showed and this route can use without fitting.

Leg C (speed_final.py) reads the Department's weekly state file with real-time seasonal factors and
so cannot report before 1991 (five years of factors).  The Paper 2 chat read the same file
year-over-year - the 8-week sum of each state's continued claims against the same eight weeks a year
earlier - which needs no factor and reaches July 1990 from a file that begins in February 1986.  Here
the same idea is built as a leg of THIS route: the share of states whose 8-week continued claims
stand `x` log points above a year earlier, read at the route's own line, fifty per cent, for `k`
consecutive weeks; the call is published 9 days after the week (the Department's release for the
state detail); the date is the month of the first week of the run.  `x` and `k` are chosen
leave-one-peak-out on the four peaks the file covers (1990, 2001, 2007, 2020), each fold reporting
its choice, with 2023 and every other episode listed.  Output breadth_yoy.log.
"""
import sys, warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd

d = pd.read_csv('/home/claude/lab/dol/ar539.csv', low_memory=False)
d['week'] = pd.to_datetime(d['c2'], errors='coerce')
d = d[d['week'].notna() & d['st'].notna()]
d = d[~d['st'].isin(['PR', 'VI'])]
CW = d.pivot_table(index='week', columns='st', values='c8', aggfunc='first').sort_index()
IC = d.pivot_table(index='week', columns='st', values='c3', aggfunc='first').sort_index()
CW = CW.apply(pd.to_numeric, errors='coerce'); IC = IC.apply(pd.to_numeric, errors='coerce')
# regularize to a weekly Saturday grid
CW = CW.resample('W-SAT').last(); IC = IC.resample('W-SAT').last()
print(f'weekly state file: {CW.index.min():%Y-%m-%d} to {CW.index.max():%Y-%m-%d}, {CW.shape[1]} states')

PK = ['1990-07', '2001-03', '2007-12', '2020-02']; TR = ['1991-03', '2001-11', '2009-06', '2020-04']
def mon(t): return pd.Timestamp(t.year, t.month, 1)
def month_end(m): return pd.Timestamp(m + '-01') + pd.offsets.MonthEnd(0)

def breadth(X, x, weeks=8):
    S = X.rolling(weeks).sum(); Y = np.log(S) - np.log(S.shift(52))
    return ((Y >= x / 100.0).sum(axis=1) / Y.notna().sum(axis=1) * 100.0).dropna()

def calls(Bx, k, line=50.0, quiet_weeks=26, pub_days=9):
    """episodes: the first week of a run of `k` weeks at or above the line, after at least `quiet_weeks` below it"""
    out = []; below = 0; run = 0; start = None
    for t, v in Bx.items():
        if v >= line:
            run += 1
            if run == 1: start = t
            if run == k and below >= quiet_weeks:
                out.append((t + pd.Timedelta(days=pub_days), mon(start)))
            if run >= k: below = 0
        else:
            run = 0; below += 1
    return out

def score(cl, start='1987-06-01'):
    cl = [c for c in cl if c[0] >= pd.Timestamp(start)]
    hits = {}; used = set()
    for i, (p, q) in enumerate(zip(PK, TR)):
        c = [(j, pub, dt) for j, (pub, dt) in enumerate(cl) if pd.Timestamp(p + '-01') - pd.DateOffset(months=6) <= pub <= pd.Timestamp(q + '-01') + pd.DateOffset(months=3)]
        if c:
            j, pub, dt = min(c, key=lambda z: z[1]); hits[i] = ((pub - month_end(p)).days, (dt.year - int(p[:4])) * 12 + dt.month - int(p[5:])); used.add(j)
    other = [(pub.strftime('%Y-%m-%d'), dt.strftime('%Y-%m')) for j, (pub, dt) in enumerate(cl) if j not in used]
    return hits, other

grid = [(x, k) for x in (5, 10, 15, 20, 25, 30) for k in (1, 2, 4)]
res = {}
for x, k in grid:
    Bx = breadth(CW, x); cl = calls(Bx, k); hits, other = score(cl)
    res[(x, k)] = (hits, other)
    o23 = [o for o in other if o[0] >= '2022-01-01']; o_pre = [o for o in other if o[0] < '2022-01-01']
    print(f'continued claims, x={x:2d} log points, k={k}: peaks {len(hits)}/4 ' + ' '.join(f'{PK[i]}:{hits[i][0]:+4d}d/{hits[i][1]:+d}' for i in sorted(hits)) + f'   other before 2022: {o_pre}   2022 on: {o23}')

print('\nleave-one-peak-out: choose (x, k) on the other three - fewest other calls before 2022, then the fastest median lag - and read the left-out peak')
picks = []
for i in range(4):
    best = None
    for (x, k), (hits, other) in res.items():
        hh = {j: v for j, v in hits.items() if j != i}
        if len(hh) < 3: continue
        o_pre = [o for o in other if o[0] < '2022-01-01']
        key = (len(o_pre), np.median([v[0] for v in hh.values()]), max(v[0] for v in hh.values()), x)
        if best is None or key < best[0]: best = (key, (x, k))
    key, (x, k) = best; hits, other = res[(x, k)]
    picks.append((x, k))
    print(f'  leave out {PK[i]}: picks x={x}, k={k} (other calls before 2022: {key[0]}, median {key[1]:.0f} d); the left-out peak: ' + (f'{hits[i][0]:+d} d, date {hits[i][1]:+d}' if i in hits else 'NOT called'))
print('  every fold the same:', len(set(picks)) == 1, set(picks))
x, k = picks[0]
Bx = breadth(CW, x); cl = calls(Bx, k)
print(f'\nthe leg at the folds\' choice (x={x}, k={k}), every call: {[(p.strftime("%Y-%m-%d"), dt.strftime("%Y-%m")) for p, dt in cl]}')
print('the breadth around July 1990 (weekly, per cent):', Bx['1990-05':'1990-09'].round(0).tolist())
print('the breadth around 2023 (monthly maxima):', Bx['2022-10':'2024-06'].resample('ME').max().round(0).tolist())
print('\nthe same on initial claims (for the record):')
for x, k in ((10, 4), (20, 4), (30, 4)):
    Bi = breadth(IC, x); cl = calls(Bi, k); hits, other = score(cl)
    print(f'initial claims, x={x}, k={k}: peaks {len(hits)}/4 ' + ' '.join(f'{PK[i]}:{hits[i][0]:+4d}d' for i in sorted(hits)) + f'   other: {other[:8]} ({len(other)})')
