"""STAGE 5 OF THE SECOND-CONDITION HUNT (4 September 2026): the two LABOUR candidates, put through the same battery.

Stage 4 refused housing starts: it moves both walls, but it raises the second condition's combined window exposure
from 7.2 to 11.8 per cent (a 1.65x multiplier on the route's hazard), its 2007 gain lives on a two-point knife edge
(36-37 works, 38 does not), and it clears the February 1967 claims call by less than one standard deviation - and
only because the tool's window opens on 20 October 1966, twenty days after the reading that would have confirmed
it.  Rule 21 refuses that trade.

Two candidates remain from stage 3, both labour objects, both moving the 1973 wall only:

  RATE-GAP   the unemployment rate itself in the route's own gap form - the one-month reading 0.60 points above
             its trailing six-month minimum - rather than Sahm's three-month/twelve-month form.  THE SAME DATA the
             shipped condition already reads, first prints genuine from March 1960 (ALFRED's first UNRATE vintage),
             so it adds no new series and no new revision risk.  1973: +120 -> +69 days.
  FLOW       the unemployed less than five weeks as a per cent of the labour force, two-month mean 0.30 points
             above its trailing twelve-month minimum: the FLOW into unemployment, where Sahm's object is the stock
             it accumulates to.  Quiet window exposure 0.0 per cent.  1973: +120 -> +69 days.  ALFRED has no
             vintages for UEMPLT5, so it can only be read on the current vintage - which is a real-time claim this
             program does not make lightly, and the reason it is reported separately below.

Output second_hunt3.log.
"""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0, '/home/claude'); sys.path.insert(0, '/home/claude/lab/weekly'); sys.path.insert(0, '/home/claude/lab/rt')
import numpy as np, pandas as pd
import bristow_rule_v3 as B, american_chronology as AC, alfred

PK, TR = AC.PK, AC.TR
PEAKS13 = list(PK) + [pd.Timestamp('2023-07-01')]; TROUGH13 = list(TR) + [pd.Timestamp('2024-08-01')]
log = open('/home/claude/lab/weekly/second_hunt3.log', 'w')
def P(*a): print(*a); print(*a, file=log, flush=True)
def quiet(idx, post=18):
    q = pd.Series(True, index=idx)
    for p, t in zip(PEAKS13, TROUGH13): q[(idx >= p - pd.DateOffset(months=9)) & (idx <= t + pd.DateOffset(months=post))] = False
    return q
def exp_series(o, line, per_month=1):
    o = o.dropna(); hit = (o >= line)
    return (hit[::-1].rolling(max(1, per_month), min_periods=1).max()[::-1].astype(bool) |
            hit.rolling(6 * per_month + 1, min_periods=1).max().astype(bool))
def exposure(o, line, per_month=1):
    o = o.dropna(); return float(exp_series(o, line, per_month)[quiet(o.index)].mean() * 100)

PL, TL = AC.legs(safe=True, with_S=True, with_U=True)
G = AC.sahm_rt(); VR = AC.vacancy_gap_rt(2, 6)
BASE = [dict(name='vacancy(2,6)', gap=VR, line=0.36, pub_day=30)]
def rise(s, k, back): m = s.rolling(k).mean(); return (m - m.shift(1).rolling(back).min()).dropna()

cur = pd.read_csv('/home/claude/archive/data/fred/UNRATE.csv'); cur.columns = ['d', 'v']
cur = cur.set_index(pd.to_datetime(cur['d']))['v'].astype(float)
fpu = alfred.first_prints('UNRATE'); UR = pd.concat([cur[cur.index < fpu.index.min()], fpu]).sort_index()
u5 = pd.read_csv('/home/claude/archive/data/fred/UEMPLT5.csv'); u5.columns = ['d', 'v']
u5 = u5.set_index(pd.to_datetime(u5['d']))['v'].astype(float).dropna()
cl = pd.read_csv('/home/claude/archive/data/fred/CLF16OV.csv'); cl.columns = ['d', 'v']
cl = cl.set_index(pd.to_datetime(cl['d']))['v'].astype(float).dropna()
FLOW = (u5 / cl * 100).dropna()

def route(second):
    turns = B.american_chronology(PL, TL, sahm=G, second=second)
    hit = {}; other = []
    for t in [x for x in turns if x['kind'] == 'peak']:
        c = [i for i, (p, q) in enumerate(zip(PK, TR)) if p - pd.DateOffset(months=6) <= t['date'] <= q]
        if c: hit[PK[c[0]]] = (t['published'] - AC.month_end(PK[c[0]])).days
        else: other.append(f"{t['published']:%Y-%m-%d}")
    return hit, other

base_hit, base_other = route(BASE)
P('STAGE 5 - THE TWO LABOUR CANDIDATES')
P(f'  version 43 base: median {np.median(list(base_hit.values())):.0f} d, worst {max(base_hit.values())}, '
  f'within a month {sum(0 <= l <= 30 for l in base_hit.values())}/12, 1973 {base_hit[pd.Timestamp("1973-11-01")]}, '
  f'2007 {base_hit[pd.Timestamp("2007-12-01")]}, other {base_other}')

DIS = [(pd.Timestamp('1951-09-20'), 'July 1951'), (pd.Timestamp('1952-04-10'), 'March 1952'), (pd.Timestamp('1967-04-20'), 'February 1967')]
def margins(o, line, label):
    o = o.dropna(); sd = float(o[quiet(o.index)].std())
    P(f'    {label} (line {line:g}, quiet sd {sd:.3f})')
    for call, nm in DIS:
        seg = o[call - pd.DateOffset(months=6): call + pd.DateOffset(months=12)]
        if not len(seg): P(f'      {nm:15s} the series does not reach it'); continue
        mx = float(seg.max()); cal = o[call - pd.DateOffset(months=7): call + pd.DateOffset(months=12)]
        P(f'      {nm:15s} window {seg.index[0]:%Y-%m}-{seg.index[-1]:%Y-%m}: max {mx:6.3f} in {seg.idxmax():%Y-%m}, '
          f'margin {line - mx:+6.3f} ({(line - mx) / sd:+.2f} sd)'
          + (f'   [one month earlier: {float(cal.max()):.3f} in {cal.idxmax():%Y-%m}, margin {line - float(cal.max()):+.3f}]' if float(cal.max()) > mx else ''))

for nm, s, forms, lines, pub in (
        ('the unemployment rate, gap form (first prints from 1960-03)', UR, [(1, 6), (1, 12), (2, 6), (2, 12), (3, 6), (3, 12)], np.arange(0.30, 1.05, 0.05), 7),
        ('the flow into unemployment (current vintage only)', FLOW, [(1, 6), (1, 12), (2, 6), (2, 12), (3, 6), (3, 12)], np.arange(0.10, 0.70, 0.025), 7)):
    P(f'\n=== {nm}')
    cache = {}
    for k, b in forms:
        o = rise(s, k, b)
        for l in lines:
            l = float(l); e = exposure(o, l)
            if e > 5.8: continue
            hit, other = route(BASE + [dict(name=f'{nm}[{k},{b}]', gap=o, line=l, pub_day=pub)])
            if len(hit) < 12: continue
            cache[(k, b, round(l, 3))] = (hit, other, e)
    P(f'  {len(cache)} settings inside the 5.8 per cent gate and calling all twelve')
    P('  LEAVE-ONE-RECESSION-OUT (no episode outside the thirteen; then the sum of the kept lags; ties to the lower line):')
    picks = []
    for p in PK:
        if p < s.index[0] + pd.DateOffset(months=24): continue
        best = None
        for key, (hit, other, e) in cache.items():
            if len(other) > 1: continue
            sc = (len(other), sum(v for q, v in hit.items() if q != p), key[2])
            if best is None or sc < best[0]: best = (sc, key)
        if best is None: P(f'    leave out {p:%Y-%m}: nothing inside the gate'); continue
        key = best[1]; hit, other, e = cache[key]; picks.append(key)
        P(f'    leave out {p:%Y-%m}: picks k={key[0]} back={key[1]:2d} line {key[2]:.3f} (exposure {e:.1f}%); held-out lag {hit[p]:+d} against {base_hit[p]:+d}')
    P(f'    every fold the same: {len(set(picks)) == 1} {set(picks)}')
    if not picks: continue
    k, b, l = picks[0]; o = rise(s, k, b)
    hit, other, e = cache[(k, b, l)]
    P(f'  THE FOLDS\' CHOICE: k={k} back={b} line {l:.3f}, exposure {e:.1f}%')
    P(f'    median {np.median(list(hit.values())):.0f} d, worst {max(hit.values())}, within a month {sum(0 <= v <= 30 for v in hit.values())}/12, '
      f'1973 {hit[pd.Timestamp("1973-11-01")]} (was {base_hit[pd.Timestamp("1973-11-01")]}), 2007 {hit[pd.Timestamp("2007-12-01")]}, other {other}')
    P('  THE KNIFE EDGE around the choice (same k and back, the neighbouring lines):')
    for ll in sorted(x[2] for x in cache if x[0] == k and x[1] == b):
        h2, o2, e2 = cache[(k, b, ll)]
        P(f'    line {ll:.3f} exposure {e2:4.1f}%  1973 {h2[pd.Timestamp("1973-11-01")]:4d}  2007 {h2[pd.Timestamp("2007-12-01")]:4d}  '
          f'worst {max(h2.values()):4d}  outside the thirteen {o2 if o2 else "none"}')
    P('  THE THREE CLAIMS CALLS OUTSIDE THE THIRTEEN, on the tool\'s own window:')
    margins(o, l, nm)
    P('  THE COMBINED EXPOSURE:')
    idx = pd.date_range(max(pd.Timestamp('1960-01-01'), o.index[0]), '2026-07-01', freq='MS')
    al = lambda x, li: exp_series(x, li).reindex(idx).fillna(False).astype(bool)
    eS, eV, eN = al(G, 0.5), al(VR, 0.36), al(o, l); q = quiet(idx)
    p0, p1 = (eS | eV)[q].mean(), (eS | eV | eN)[q].mean()
    P(f'    {idx[0]:%Y-%m} to {idx[-1]:%Y-%m} ({int(q.sum())} quiet months): Sahm {eS[q].mean()*100:.2f}%, vacancy {eV[q].mean()*100:.2f}%, '
      f'the candidate {eN[q].mean()*100:.2f}%')
    P(f'    the shipped OR {p0*100:.2f}%  ->  with the candidate {p1*100:.2f}%   multiplier {p1/max(p0,1e-12):.3f}x')
    for lab, pc in (('point estimate', 3 / 78), ('upper Poisson bound', 0.112)):
        P(f'      hazard, {lab}: {pc*p0*100:.3f}% a year (one in {1/(pc*p0):,.0f}) -> {pc*p1*100:.3f}% (one in {1/(pc*p1):,.0f})')
log.close()
