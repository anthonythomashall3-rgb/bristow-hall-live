"""THE CLAIMS FRONTIER, THIRD PASS - under version 44 (4 September 2026).

§8z declared the claims side exhausted and it was right AT THE TIME, for a reason that has now changed.  Under
version 43 a claims leg could only help a peak where the route's call WAS the claims call; at November 1973,
July 1981 and December 2007 the call was held by the second condition, so a faster claims object bought nothing
there and the frontier looked closed.

Version 44 moved the second condition forward at all three.  The route's calls are now:

    1948 +10(claims)  1953 +51(claims)  1957 -11(claims)  1960 -70(claims)  1969 +31(claims)
    1973 +41(claims)  1980 -13(second)  1981 +90(claims)  1990 +51(claims)  2001 +30(second)
    2007  -3(claims)  2020 +26(claims)

Ten of the twelve are now CLAIMS-BOUND.  Every day the claims field can be brought forward at 1953, 1973, 1981 or
1990 is now a day off the route's own call, where before it was absorbed by the wait for confirmation.  So the
frontier is reopened and re-priced.

THE RULE, unchanged and not relaxed: a candidate is dropped before it is run in the route if it makes ANY call in
a quiet period in its whole history (Rule 21).  The hazard budget freed by the symmetric window is NOT spent -
version 44 stands at one false episode in 292 years and nothing here may raise it.

Output claims_frontier3.log.
"""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0, '/home/claude'); sys.path.insert(0, '/home/claude/lab/weekly'); sys.path.insert(0, '/home/claude/lab/rt')
import numpy as np, pandas as pd
import bristow_rule_v3 as B, american_chronology as AC
PK, TR = AC.PK, AC.TR
P13 = list(PK) + [pd.Timestamp('2023-07-01')]; T13 = list(TR) + [pd.Timestamp('2024-08-01')]
log = open('/home/claude/lab/weekly/claims_frontier3.log', 'w')
def P(*a): print(*a); print(*a, file=log, flush=True)
PL, TL = AC.legs(safe=True, with_S=True, with_U=True)
G = AC.sahm_rt(); S44 = AC.second_v44(); HZ = AC.HORIZON_V44
N = pd.read_csv('/home/claude/lab/weekly/DOL_national_weekly_claims_sa_rt.csv', index_col=0, parse_dates=True)
cc = np.log(N['cc_sa_rt']) * 100.0; ic = np.log(N['ic_sa_rt']) * 100.0
iur = pd.read_csv('/home/claude/archive/data/fred/IURSA.csv'); iur.columns = ['d', 'v']
iur = iur.set_index(pd.to_datetime(iur['d']))['v'].astype(float).dropna()
def gap_calls(s, line, back=52, quiet=26, pub=5, smooth=1):
    m = s.rolling(smooth).mean(); g = (m - m.rolling(back, min_periods=26).min()).dropna()
    out = []; below = 0
    for t, v in g.items():
        if v >= line:
            if below >= quiet: out.append((t + pd.Timedelta(days=pub), pd.Timestamp(t.year, t.month, 1)))
            below = 0
        else: below += 1
    return out
def chg_calls(s, line, weeks, quiet=26, pub=5):
    g = (s - s.shift(weeks)).dropna(); out = []; below = 0
    for t, v in g.items():
        if v >= line:
            if below >= quiet: out.append((t + pd.Timedelta(days=pub), pd.Timestamp(t.year, t.month, 1)))
            below = 0
        else: below += 1
    return out
def qcalls(c):
    return [f'{p:%Y-%m-%d}' for p, d in c
            if not any(a - pd.DateOffset(months=9) <= p <= b + pd.DateOffset(months=18) for a, b in zip(P13, T13))]
def route(extra=None):
    legs = dict(PL) if extra is None else {**PL, 'V': extra}
    t = B.american_chronology(legs, TL, sahm=G, second=S44, horizon_months=HZ)
    hit = {}; err = {}; other = []
    for x in [y for y in t if y['kind'] == 'peak']:
        c = [i for i, (p, q) in enumerate(zip(PK, TR)) if p - pd.DateOffset(months=6) <= x['date'] <= q]
        if c:
            hit[PK[c[0]]] = (x['published'] - AC.month_end(PK[c[0]])).days
            err[PK[c[0]]] = (x['date'].year - PK[c[0]].year) * 12 + (x['date'].month - PK[c[0]].month)
        else: other.append(f"{x['published']:%Y-%m-%d}")
    return hit, err, other
b, be, bo = route()
P(f'version 44: median {np.median(list(b.values())):.0f} d, worst {max(b.values())}, '
  f'inside the month {sum(v <= 0 for v in b.values())}/12, mae {np.mean([abs(x) for x in be.values()]):.2f}, other {bo}')
P('  ' + '  '.join(f'{p:%Y-%m}:{v:+d}' for p, v in b.items()))
CAND = {}
for sm in (1, 2, 3, 4, 8):
    for ln in (15, 20, 25, 30, 35, 40, 45, 50, 55, 60):
        CAND[f'initial claims, {sm}-week mean {ln} log points over its 52-week low'] = gap_calls(ic, ln, smooth=sm)
    for ln in (8, 10, 12, 15, 18, 20, 25, 30, 35):
        CAND[f'continued claims, {sm}-week mean {ln} log points over its 52-week low'] = gap_calls(cc, ln, smooth=sm)
    for ln in (0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.70, 0.80):
        CAND[f'the insured rate, {sm}-week mean {ln:.2f} points over its 52-week low'] = gap_calls(iur, ln, smooth=sm)
for wk in (8, 13, 20, 26, 39):
    for ln in (6, 8, 10, 12, 15, 20, 25, 30):
        CAND[f'continued claims, {wk}-week change {ln} log points'] = chg_calls(cc, ln, wk)
        CAND[f'initial claims, {wk}-week change {ln} log points'] = chg_calls(ic, ln, wk)
P(f'\n{len(CAND)} candidates. Rule 21 first: any candidate with a quiet-period call of its own is dropped unrun.')
kept = {n: c for n, c in CAND.items() if not qcalls(c)}
P(f'  {len(kept)} of {len(CAND)} make no quiet-period call in their whole history.')
rows = []
for n, c in kept.items():
    hit, err, other = route(c)
    if len(hit) < 12 or other != bo: continue
    gain = {f'{p:%Y-%m}': b[p] - hit[p] for p in hit if hit[p] < b[p]}
    if not gain: continue
    rows.append((np.median(list(hit.values())), max(hit.values()), -sum(v <= 0 for v in hit.values()),
                 np.mean([abs(x) for x in err.values()]), n, hit, err, gain))
P(f'\n{len(rows)} candidates make the route faster without adding a call anywhere:')
for med, wo, nin, mae, n, hit, err, gain in sorted(rows)[:20]:
    P(f'  {n:64s} median {med:5.0f} worst {wo:5d} inside {-nin:2d} mae {mae:.2f}  gains {gain}')
if not rows:
    P('  none: under version 44 the claims side is still exhausted, and the frontier is closed for the same reason as before.')
else:
    med, wo, nin, mae, n, hit, err, gain = sorted(rows)[0]
    P(f'\nTHE BEST: {n}')
    P(f'  median {np.median(list(b.values())):.0f} -> {med:.0f}, worst {max(b.values())} -> {wo}, '
      f'inside the month {sum(v <= 0 for v in b.values())} -> {-nin}, mae {np.mean([abs(x) for x in be.values()]):.2f} -> {mae:.2f}')
    P('  ' + '  '.join(f'{p:%Y-%m}:{v:+d}[{err[p]:+d}]' + (f'(was {b[p]:+d})' if v != b[p] else '') for p, v in hit.items()))
log.close()
