"""CONSTRUCTION EMPLOYMENT AS THE SECOND CONDITION - the monthly tier's one survivor, put through the §8y battery.

`lab/data/second_screen_monthly.py` screened the 1,328 FRED monthly series that begin on or before January 1951
and are still published, under the specification §8y wrote: exposure at or below 5.8 per cent, no more than 0.2
points added to the OR of the shipped pair, and no reading at its line inside any of the three disturbance
windows.  Of 216 settings that move a wall, all but a handful are FOOD AND FARM PRICE indexes moving on the 1973
commodity shock - a spike that is not a statement about employment and fails Rule 20's requirement of a
structural reason.  One survivor has both the numbers and the mechanism:

    ALL EMPLOYEES, CONSTRUCTION (FRED USCONS, 1939-), the month's level 135,000 below its trailing six-month
    maximum, on the employment report (published the first Friday of the month after).

The mechanism is the one Leamer put in a sentence - housing leads the cycle - but read through EMPLOYMENT, which
is the committee's own object, rather than through starts or permits, which are not.  That matters for the reason
§8y refused housing starts: starts are an activity series that halves in a credit squeeze without anyone losing a
job (October 1966), while construction PAYROLLS in 1966 did not fall.  This script tests whether that difference
is real.
"""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0, '/home/claude'); sys.path.insert(0, '/home/claude/lab/weekly'); sys.path.insert(0, '/home/claude/lab/rt')
import numpy as np, pandas as pd
import bristow_rule_v3 as B, american_chronology as AC, alfred

PK, TR = AC.PK, AC.TR
P13 = list(PK) + [pd.Timestamp('2023-07-01')]; T13 = list(TR) + [pd.Timestamp('2024-08-01')]
log = open('/home/claude/lab/weekly/uscons_test.log', 'w')
def P(*a): print(*a); print(*a, file=log, flush=True)
def quiet(idx):
    q = pd.Series(True, index=idx)
    for p, t in zip(P13, T13): q[(idx >= p - pd.DateOffset(months=9)) & (idx <= t + pd.DateOffset(months=18))] = False
    return q
def exp_s(o, line):
    h = (o >= line)
    return (h[::-1].rolling(1, min_periods=1).max()[::-1].astype(bool) | h.rolling(7, min_periods=1).max().astype(bool))
def expo(o, line):
    o = o.dropna(); return float(exp_s(o, line)[quiet(o.index)].mean() * 100)

PL, TL = AC.legs(safe=True, with_S=True, with_U=True)
G = AC.sahm_rt(); VR = AC.vacancy_gap_rt(2, 6)
BASE = [dict(name='vacancy(2,6)', gap=VR, line=0.36, pub_day=30)]

cur = pd.read_csv('/home/claude/archive/data/fred/USCONS.csv'); cur.columns = ['d', 'v']
cur = cur.set_index(pd.to_datetime(cur['d']))['v'].astype(float).dropna()
try:
    fp = alfred.first_prints('USCONS'); v0 = alfred.vintages('USCONS')[0]
    S = pd.concat([cur[cur.index < fp.index.min()], fp]).sort_index()
    P(f'USCONS: first prints from the ALFRED vintage of {v0:%Y-%m-%d}; current vintage before that.')
except Exception as e:
    S = cur; P(f'USCONS: no ALFRED vintages here ({e}); read on the current vintage - RECORD THIS AS A LIMIT.')
def fall(k, back): m = S.rolling(k).mean(); return (m.shift(1).rolling(back).max() - m).dropna()

def route(second):
    t = B.american_chronology(PL, TL, sahm=G, second=second)
    hit = {}; err = {}; other = []
    for x in [y for y in t if y['kind'] == 'peak']:
        c = [i for i, (p, q) in enumerate(zip(PK, TR)) if p - pd.DateOffset(months=6) <= x['date'] <= q]
        if c:
            hit[PK[c[0]]] = (x['published'] - AC.month_end(PK[c[0]])).days
            err[PK[c[0]]] = (x['date'].year - PK[c[0]].year) * 12 + (x['date'].month - PK[c[0]].month)
        else: other.append(f"{x['published']:%Y-%m-%d}")
    return hit, err, other
b, be, bo = route(BASE)
P(f'\nversion 43 base: median {np.median(list(b.values())):.0f} d, worst {max(b.values())}, within a month '
  f'{sum(0 <= v <= 30 for v in b.values())}/12, mae {np.mean([abs(x) for x in be.values()]):.2f}, other {bo}')

P('\n(1) THE GRID, with the employment report\'s own publication day (the first Friday: pub_day 7).')
P(f'    {"k":>2} {"back":>4} {"line":>8} {"expo":>5} {"OR":>6}  {"1973":>5} {"2007":>5} {"worst":>5} {"med":>4} {"mae":>5}  outside the thirteen')
IDX = pd.date_range('1949-01-01', '2026-07-01', freq='MS'); QM = quiet(IDX)
eS = exp_s(G, 0.5).reindex(IDX).fillna(False).astype(bool); eV = exp_s(VR, 0.36).reindex(IDX).fillna(False).astype(bool)
SH = float((eS | eV)[QM].mean() * 100)
cache = {}
for k in (1, 2, 3):
    for back in (6, 12):
        o = fall(k, back)
        for line in np.arange(60, 320, 15.0):
            e = expo(o, float(line))
            if e > 5.8: continue
            comb = float((eS | eV | exp_s(o, float(line)).reindex(IDX).fillna(False).astype(bool))[QM].mean() * 100)
            hit, err, other = route(BASE + [dict(name='cons', gap=o, line=float(line), pub_day=7)])
            if len(hit) < 12: continue
            cache[(k, back, float(line))] = (hit, err, other, e, comb)
            P(f'    {k:2d} {back:4d} {line:8.0f} {e:5.1f} {comb:6.2f}  {hit[pd.Timestamp("1973-11-01")]:5d} '
              f'{hit[pd.Timestamp("2007-12-01")]:5d} {max(hit.values()):5d} {np.median(list(hit.values())):4.0f} '
              f'{np.mean([abs(x) for x in err.values()]):5.2f}  {other if other else "none"}')
P(f'    (the shipped OR is {SH:.2f} per cent; a candidate that leaves it there adds no hazard at all)')

P('\n(2) LEAVE-ONE-RECESSION-OUT (no episode outside the thirteen; then the sum of the kept lags; ties to the higher line):')
picks = []
for p in PK:
    best = None
    for key, (hit, err, other, e, comb) in cache.items():
        if len(other) > 1: continue
        sc = (len(other), sum(v for q, v in hit.items() if q != p), sum(abs(v) for q, v in err.items() if q != p), -key[2])
        if best is None or sc < best[0]: best = (sc, key)
    if best is None: P(f'    leave out {p:%Y-%m}: nothing inside the gate'); continue
    key = best[1]; hit, err, other, e, comb = cache[key]; picks.append(key)
    P(f'    leave out {p:%Y-%m}: picks k={key[0]} back={key[1]:2d} line {key[2]:.0f}k (exposure {e:.1f}%, OR {comb:.2f}%); '
      f'held-out lag {hit[p]:+d} against {b[p]:+d}, date err {err[p]:+d} against {be[p]:+d}')
P(f'    every fold the same: {len(set(picks)) == 1} {set(picks)}')

if picks:
    k, back, line = picks[0]; o = fall(k, back)
    hit, err, other, e, comb = cache[(k, back, line)]
    P(f'\n(3) THE FOLDS\' CHOICE: {k}-month reading {line:.0f},000 below its trailing {back}-month maximum, exposure {e:.1f}%, OR {comb:.2f}%')
    P(f'    median {np.median(list(hit.values())):.0f} d (was {np.median(list(b.values())):.0f}), worst {max(hit.values())} (was {max(b.values())}), '
      f'within a month {sum(0 <= v <= 30 for v in hit.values())}/12 (was {sum(0 <= v <= 30 for v in b.values())}), '
      f'mae {np.mean([abs(x) for x in err.values()]):.2f} (was {np.mean([abs(x) for x in be.values()]):.2f}), other {other}')
    P('    ' + '  '.join(f'{p:%Y-%m}:{v:+d}[{err[p]:+d}] (was {b[p]:+d}[{be[p]:+d}])' for p, v in hit.items()))
    P('\n(4) THE THREE CLAIMS CALLS OUTSIDE THE THIRTEEN, on the window the tool actually uses:')
    sd = float(o[quiet(o.index)].std())
    P(f'    the object\'s quiet standard deviation {sd:.1f} thousand; the line {line:.0f}')
    for call, nm in ((pd.Timestamp('1951-09-20'), 'July 1951'), (pd.Timestamp('1952-04-10'), 'March 1952'), (pd.Timestamp('1967-04-20'), 'February 1967')):
        seg = o[call - pd.DateOffset(months=6): call + pd.DateOffset(months=12)]
        cal = o[call - pd.DateOffset(months=7): call + pd.DateOffset(months=12)]
        P(f'      {nm:15s} window {seg.index[0]:%Y-%m} to {seg.index[-1]:%Y-%m}: maximum {seg.max():8.1f} in {seg.idxmax():%Y-%m}, '
          f'margin {line - seg.max():+8.1f} ({(line - seg.max()) / sd:+.2f} sd)'
          + (f'   [one month earlier the window would carry {cal.max():.1f}]' if cal.max() > seg.max() else ''))
    P('\n(5) 1966, the case that refused housing starts. Starts halved; did construction PAYROLLS fall?')
    seg = o['1965-06':'1967-12']
    P('    ' + '  '.join(f'{t:%y-%m}:{v:.0f}' for t, v in seg.items()))
log.close()
