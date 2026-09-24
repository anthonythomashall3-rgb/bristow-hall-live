"""THE CLAIMS FRONTIER, SECOND PASS (4 September 2026) - the cheap side, worked to its end.

§8y established the rule: speed is bought on the CLAIMS side or not at all.  Leg U (the insured unemployment rate)
was the first purchase.  This asks what is LEFT on that side.

Which peaks can a claims leg still help?  Only those where the route's call IS the claims call - where the second
condition was already met when the claims field spoke.  With leg U in the route those are:

    1948 (+10)  1953 (+51)  1957 (-11)  1960 (-70)  1970 (+31)  1990 (+51)  2020 (+26)

and of them only 1953 and 1990 are later than the route's median of 30 days, both called by leg A, the monthly
state diffusion published the 20th.  1953 needs a weekly file that does not exist before 1967 (the 1946-83 panel
of §8w begins in July 1960).  1990 does not: the national weekly file reaches 1967.  So the target is precise -
a weekly claims object that speaks before 20 September 1990 and never speaks in a quiet period.

Candidates, all on the route's own real-time seasonal factors (DOL_national_weekly_claims_sa_rt.csv) and on the
insured rate: initial claims and continued claims as gaps from a trailing minimum and as k-month changes, and the
insured rate at smoothings and lines the leave-one-out grid did not already choose.  Each is run as an EXTRA PEAK
LEG in the version-43 route; the test is Rule 18's (unanimous folds) and Rule 21's (no quiet-period call of its
own, in its whole history).

Output claims_frontier2.log.
"""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0, '/home/claude'); sys.path.insert(0, '/home/claude/lab/weekly')
import numpy as np, pandas as pd
import bristow_rule_v3 as B, american_chronology as AC

PK, TR = AC.PK, AC.TR
PEAKS13 = list(PK) + [pd.Timestamp('2023-07-01')]; TROUGH13 = list(TR) + [pd.Timestamp('2024-08-01')]
log = open('/home/claude/lab/weekly/claims_frontier2.log', 'w')
def P(*a): print(*a); print(*a, file=log, flush=True)

PL, TL = AC.legs(safe=True, with_S=True, with_U=True)
G = AC.sahm_rt(); VR = AC.vacancy_gap_rt(2, 6)
SECOND = [dict(name='vacancy(2,6)', gap=VR, line=0.36, pub_day=30)]

N = pd.read_csv('/home/claude/lab/weekly/DOL_national_weekly_claims_sa_rt.csv', index_col=0, parse_dates=True)
ic = np.log(N['ic_sa_rt']) * 100.0; cc = np.log(N['cc_sa_rt']) * 100.0
iur = pd.read_csv('/home/claude/archive/data/fred/IURSA.csv'); iur.columns = ['d', 'v']
iur = iur.set_index(pd.to_datetime(iur['d']))['v'].astype(float).dropna()

def gap_calls(s, line, back=52, quiet=26, pub=5, smooth=1):
    m = s.rolling(smooth).mean(); gap = (m - m.rolling(back, min_periods=26).min()).dropna()
    out = []; below = 0
    for t, v in gap.items():
        if v >= line:
            if below >= quiet: out.append((t + pd.Timedelta(days=pub), pd.Timestamp(t.year, t.month, 1)))
            below = 0
        else: below += 1
    return out

def chg_calls(s, line, weeks, quiet=26, pub=5):
    gap = (s - s.shift(weeks)).dropna(); out = []; below = 0
    for t, v in gap.items():
        if v >= line:
            if below >= quiet: out.append((t + pd.Timedelta(days=pub), pd.Timestamp(t.year, t.month, 1)))
            below = 0
        else: below += 1
    return out

def quiet_calls(calls):
    ex = []
    for pub, d in calls:
        if not any(p - pd.DateOffset(months=9) <= pub <= t + pd.DateOffset(months=18) for p, t in zip(PEAKS13, TROUGH13)):
            ex.append(f'{pub:%Y-%m-%d}')
    return ex

def run(extra=None):
    legs = dict(PL) if extra is None else {**PL, 'X': extra}
    turns = B.american_chronology(legs, TL, sahm=G, second=SECOND)
    hit = {}; other = []
    for t in [x for x in turns if x['kind'] == 'peak']:
        c = [i for i, (p, q) in enumerate(zip(PK, TR)) if p - pd.DateOffset(months=6) <= t['date'] <= q]
        if c: hit[PK[c[0]]] = (t['published'] - AC.month_end(PK[c[0]])).days
        else: other.append(f"{t['published']:%Y-%m-%d}")
    return hit, other

base, base_other = run()
P('THE CLAIMS FRONTIER, SECOND PASS')
P(f'  version 43: median {np.median(list(base.values())):.0f} d, worst {max(base.values())}, '
  f'within a month {sum(0 <= v <= 30 for v in base.values())}/12, other {base_other}')
P('  the peaks a claims leg can still help (the call IS the claims call): ' +
  ', '.join(f'{p:%Y-%m}:{v:+d}' for p, v in base.items() if v in (10, 51, -11, -70, 31, 26)))

CAND = {}
for sm in (1, 2, 4):
    for ln in (20, 25, 30, 35, 40, 45, 50):
        CAND[f'initial claims, {sm}-week mean {ln} log points over its 52-week low'] = gap_calls(ic, ln, smooth=sm)
    for ln in (10, 15, 20, 25, 30):
        CAND[f'continued claims, {sm}-week mean {ln} log points over its 52-week low'] = gap_calls(cc, ln, smooth=sm)
for wk in (13, 26):
    for ln in (8, 10, 12, 15, 20, 25):
        CAND[f'continued claims, {wk}-week change {ln} log points'] = chg_calls(cc, ln, wk)
        CAND[f'initial claims, {wk}-week change {ln} log points'] = chg_calls(ic, ln, wk)
for sm in (1, 2, 4):
    for ln in (0.35, 0.40, 0.45, 0.55, 0.60, 0.70):
        CAND[f'the insured rate, {sm}-week mean {ln:.2f} points over its 52-week low'] = gap_calls(iur, ln, smooth=sm)

P(f'\n{len(CAND)} candidates. Rule 21 first: a candidate with ANY quiet-period call of its own is dropped before it')
P('is even run in the route.')
kept = {}
for nm, calls in CAND.items():
    q = quiet_calls(calls)
    if q: continue
    kept[nm] = calls
P(f'  {len(kept)} of {len(CAND)} make no quiet-period call in their whole history.')

P('\nIn the route (an extra peak leg; the second condition unchanged and still guarding every call):')
rows = []
for nm, calls in kept.items():
    hit, other = run(calls)
    if len(hit) < 12 or len(other) > 1: continue
    gain = {f'{p:%Y-%m}': base[p] - hit[p] for p in hit if hit[p] < base[p]}
    rows.append((np.median(list(hit.values())), max(hit.values()), -sum(0 <= v <= 30 for v in hit.values()), nm, hit, other, gain))
for med, wo, nin, nm, hit, other, gain in sorted(rows)[:20]:
    P(f'  {nm:66s} median {med:5.0f}  worst {wo:4d}  within a month {-nin:2d}  gains {gain if gain else "none"}')
if not rows: P('  nothing: every survivor leaves the route exactly where it was.')
else:
    med, wo, nin, nm, hit, other, gain = sorted(rows)[0]
    P(f'\nTHE BEST: {nm}')
    P(f'  median {np.median(list(base.values())):.0f} -> {med:.0f}, worst {max(base.values())} -> {wo}, '
      f'within a month {sum(0 <= v <= 30 for v in base.values())} -> {-nin}, other calls {other}')
    P('  ' + '  '.join(f'{p:%Y-%m}:{v:+d}' for p, v in hit.items()))
log.close()
