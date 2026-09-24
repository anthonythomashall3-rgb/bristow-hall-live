"""The trough clauses' drop floor (3 September 2026, night).

Under one call, one date, the first trough object to fire ends the downturn.  In 1970 the
initial-claims clauses (H monthly, I weekly) and the monthly continued-claims clause (J) fired
on the spring pause - claims dipped a log point or two in May-August 1970 and rose again to
their November peak - and would have ended the 1969-70 recession in May 1970, six months early;
only the weekly continued-claims clause K (drop 4 log points on the four-week mean) waited.
The clauses' `drop` (the fall from the running maximum that fires the call) is the parameter
that decides; here it is raised on each leg until the 1970 misfire is gone, and the leg's
record on the twelve committee troughs is read at every setting: which troughs it calls, the
lag in days from the trough month's last day, the date error in months, and every call that
matches no committee trough within six months.  The setting adopted is the LOWEST drop with no
1970 misfire - set by the negative, not by the twelve - and its speed is what it is.
Output trough_floor.log.
"""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0, '/home/claude'); sys.path.insert(0, '/home/claude/lab'); sys.path.insert(0, '/home/claude/lab/weekly'); sys.path.insert(0, '/home/claude/lab/fh')
import numpy as np, pandas as pd, bristow_rule_v3 as B
import union_troughs as T, legs_1948 as L, cc_trough_grid as C

TR = [pd.Timestamp(x) for x in ('1949-10', '1954-05', '1958-04', '1961-02', '1970-11', '1975-03', '1980-07', '1982-11', '1991-03', '2001-11', '2009-06', '2020-04')]
def md(a, b): return (a.year - b.year) * 12 + a.month - b.month
def month_end(t): return t + pd.offsets.MonthEnd(0)

def score(calls, label, start):
    calls = [(p, d) for p, d in calls if p >= pd.Timestamp(start)]
    hits = {}; used = set()
    for i, tr in enumerate(TR):
        if tr < pd.Timestamp(start) - pd.DateOffset(months=3): continue
        c = [(j, p, d) for j, (p, d) in enumerate(calls) if abs(md(d, tr)) <= 6 and j not in used]
        if c:
            j, p, d = min(c, key=lambda x: x[1]); hits[i] = ((p - month_end(tr)).days, md(d, tr)); used.add(j)
    other = [(p.strftime('%Y-%m-%d'), d.strftime('%Y-%m')) for j, (p, d) in enumerate(calls) if j not in used]
    n = sum(1 for tr in TR if tr >= pd.Timestamp(start) - pd.DateOffset(months=3))
    lags = [v[0] for v in hits.values()]; errs = [v[1] for v in hits.values()]
    mis70 = any(p.strftime('%Y-%m') in ('1970-06', '1970-07', '1970-08', '1970-09') for p, d in calls)
    print(f"  {label:28s} troughs {len(hits)}/{n}  lag median {np.median(lags) if lags else float('nan'):5.0f} worst {max(lags) if lags else '-':>4}  within 31 d {sum(1 for l in lags if l <= 31)}  exact {sum(1 for e in errs if e == 0)} within one {sum(1 for e in errs if abs(e) <= 1)}  1970 misfire {'YES' if mis70 else 'no '}  other {other}")

nat = L._nat_rt()
icm = np.log(nat['initial claims'].dropna()); ccm = np.log(nat['continued weeks claimed'].dropna())
print('H  monthly initial claims, the field (level_trough_calls; smooth 2, arm 50, published the 10th of the month after)')
for drop in (1.0, 2.0, 3.0, 5.0, 8.0, 12.0):
    calls = [(L.pub10(p - pd.DateOffset(months=1)), d) for p, d in B.level_trough_calls(icm, drop=drop)]
    score(calls, f'drop {drop:4.1f}', '1949-01-01')
print('J  monthly continued claims, the field')
for drop in (1.0, 2.0, 3.0, 5.0, 8.0, 12.0):
    calls = [(L.pub10(p - pd.DateOffset(months=1)), d) for p, d in B.level_trough_calls(ccm, drop=drop)]
    score(calls, f'drop {drop:4.1f}', '1949-01-01')
print('K  weekly continued claims (four-week mean, six falling weeks, arm 30; published five days after the week)')
D4 = C.series(4)
for delta in (4.0, 6.0, 8.0, 12.0, 16.0):
    score([(p, d) for p, d in C.calls(D4, 6, delta, 30.)], f'drop {delta:4.1f}', '1969-06-01')
print('I  weekly initial claims (eight-week mean, six falling weeks, arm 40, re-arm 13 weeks; published seven days after the week)')
def mo(t): return pd.Timestamp(t.year, t.month, 1)
src = open('/home/claude/lab/weekly/final_caller.py').read()
g = {'pd': pd, 'np': np, 'mo': mo, 'md': md}; exec("def trough_calls" + src.split("def trough_calls")[1].split("def sc(")[0], g)
N = (np.log(C.W['ic_sa_rt']) * 100.0).rolling(8).mean()
DI = pd.concat([N.rename('n'), (N - N.rolling(52, min_periods=26).min()).rename('g')], axis=1, sort=True).dropna()
for delta in (10.0, 15.0, 20.0, 25.0, 30.0):
    score(g['trough_calls'](DI, 6, delta, 40., 13), f'drop {delta:4.1f}', '1969-06-01')
print('\nthe 1970 path, monthly field (log points x100, real-time factors):')
print('  initial  ', (icm['1970-01':'1971-01'] * 100).round(1).values.tolist())
print('  continued', (ccm['1970-01':'1971-01'] * 100).round(1).values.tolist())
