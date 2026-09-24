"""CONSTRUCTION EMPLOYMENT AS A THIRD ALTERNATIVE IN THE SECOND CONDITION - the decision, on first prints.

THE ORDER OF OPERATIONS, and why it is this order.  §8y refused housing starts partly on a THIN MARGIN at the
February 1967 claims call, and the first pass on this object then chose its line by leave-one-out and measured the
margin afterwards - which is the wrong way round.  A margin is ADMISSIBILITY, like the window exposure: it is a
property the clause must have before it may be considered at all, not a score to be traded off.  So:

  GATE 1  window exposure at or below 5.8 per cent (the shipped condition's own);
  GATE 2  the OR of the whole second condition no higher than the shipped pair's 6.72 per cent - the hazard is
          the OR's (§8v), so a candidate that raises it is buying speed with risk;
  GATE 3  at EVERY ONE of the three claims calls outside the thirteen - July 1951, March 1952, February 1967 -
          the object's maximum inside the tool's own window must fall short of its line by at least the margin
          the SHIPPED CONDITION ITSELF carries.  Measured, those are Sahm's +0.46 standard deviations and the
          vacancy form's +0.26, both at February 1967; the gate is therefore +0.46 sd, the better of the two.
          Nothing may enter this route that clears a disturbance by less than the route already does.
  GATE 4  all twelve called, no episode outside the thirteen.

Only what passes all four is eligible; the folds then choose among the eligible, leave-one-recession-out.

FIRST PRINTS.  777 ALFRED vintages of USCONS from 3 November 1961 were fetched for this test, so 1967, 1973, 1981,
1990, 2001, 2007 and 2020 are all read as the figure the employment report actually printed; 1948-1960 carry the
current vintage, as the unemployment rate does before 1960.  Published the first Friday of the month after
(pub_day 7).

Output uscons_final.log.
"""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0, '/home/claude'); sys.path.insert(0, '/home/claude/lab/weekly'); sys.path.insert(0, '/home/claude/lab/rt')
import numpy as np, pandas as pd
import bristow_rule_v3 as B, american_chronology as AC, alfred

PK, TR = AC.PK, AC.TR
P13 = list(PK) + [pd.Timestamp('2023-07-01')]; T13 = list(TR) + [pd.Timestamp('2024-08-01')]
log = open('/home/claude/lab/weekly/uscons_final.log', 'w')
def P(*a): print(*a); print(*a, file=log, flush=True)
def quiet(idx):
    q = pd.Series(True, index=idx)
    for p, t in zip(P13, T13): q[(idx >= p - pd.DateOffset(months=9)) & (idx <= t + pd.DateOffset(months=18))] = False
    return q
def exp_s(o, line):
    h = (o >= line)
    return (h[::-1].rolling(1, min_periods=1).max()[::-1].astype(bool) | h.rolling(7, min_periods=1).max().astype(bool))

PL, TL = AC.legs(safe=True, with_S=True, with_U=True)
G = AC.sahm_rt(); VR = AC.vacancy_gap_rt(2, 6)
BASE = [dict(name='vacancy(2,6)', gap=VR, line=0.36, pub_day=30)]
IDX = pd.date_range('1949-01-01', '2026-07-01', freq='MS'); QM = quiet(IDX)
eS = exp_s(G, 0.5).reindex(IDX).fillna(False).astype(bool); eV = exp_s(VR, 0.36).reindex(IDX).fillna(False).astype(bool)
SHIPPED_OR = float((eS | eV)[QM].mean() * 100)

DIS = [(pd.Timestamp('1951-09-20'), 'July 1951', pd.Timestamp('1951-12-10')),
       (pd.Timestamp('1952-04-10'), 'March 1952', pd.Timestamp('1952-10-10')),
       (pd.Timestamp('1967-04-20'), 'February 1967', pd.Timestamp('1968-08-20'))]
def tightest(o, line):
    o = o.dropna(); sd = float(o[quiet(o.index)].std()); out = []
    for call, nm, end in DIS:
        seg = o[call - pd.DateOffset(months=6): end]
        if len(seg): out.append((line - float(seg.max())) / sd)
    return (min(out) if out else -9.9), sd

def marg_table(o, line, label):
    o = o.dropna(); sd = float(o[quiet(o.index)].std())
    P(f'    {label} (line {line:g}, quiet sd {sd:.3f})')
    for call, nm, end in DIS:
        seg = o[call - pd.DateOffset(months=6): end]
        if not len(seg): P(f'      {nm:15s} not reached'); continue
        mx = float(seg.max())
        P(f'      {nm:15s} {seg.index[0]:%Y-%m} to {seg.index[-1]:%Y-%m}: max {mx:8.2f} in {seg.idxmax():%Y-%m}, '
          f'margin {line - mx:+8.2f} ({(line - mx) / sd:+.2f} sd)')

P('GATE 3 CALIBRATION - the margins the SHIPPED condition itself carries at the three disturbance calls:')
marg_table(G, 0.5, "Sahm's gap on the rate as first published")
marg_table(VR, 0.36, "the vacancy rate's fast form (2,6)")
gS, _ = tightest(G, 0.5); gV, _ = tightest(VR, 0.36)
GATE3 = max(gS, gV)
P(f'    tightest: Sahm {gS:+.2f} sd, vacancy {gV:+.2f} sd  ->  GATE 3 is set at {GATE3:+.2f} sd, the better of the two.')

cur = pd.read_csv('/home/claude/archive/data/fred/USCONS.csv'); cur.columns = ['d', 'v']
cur = cur.set_index(pd.to_datetime(cur['d']))['v'].astype(float).dropna()
fp = alfred.first_prints('USCONS'); v0 = alfred.vintages('USCONS')[0]
S = pd.concat([cur[cur.index < fp.index.min()], fp]).sort_index()
P(f'\nUSCONS on first prints from the ALFRED vintage of {v0:%Y-%m-%d} ({len(alfred.vintages("USCONS"))} vintages); '
  f'current vintage {cur.index[0]:%Y-%m} to {fp.index.min():%Y-%m}.')
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
P(f'version 43 base: median {np.median(list(b.values())):.0f} d, worst {max(b.values())}, within a month '
  f'{sum(0 <= v <= 30 for v in b.values())}/12, mae {np.mean([abs(x) for x in be.values()]):.2f}, other {bo}')

P(f'\nTHE ELIGIBLE SET - every (k, back, line) passing all four gates.')
P(f'    {"k":>2} {"back":>4} {"line":>6} {"expo":>5} {"OR":>6} {"margin":>7}  {"1973":>5} {"2007":>5} {"worst":>5} {"med":>4} {"mae":>5}  outside')
elig = {}
for k in (1, 2, 3):
    for back in (6, 12):
        o = fall(k, back)
        for line in np.arange(60, 400, 5.0):
            line = float(line)
            e = float(exp_s(o, line).reindex(IDX).fillna(False).astype(bool)[QM].mean() * 100)
            if e > 5.8: continue                                                     # gate 1
            comb = float((eS | eV | exp_s(o, line).reindex(IDX).fillna(False).astype(bool))[QM].mean() * 100)
            if comb > SHIPPED_OR + 1e-9: continue                                    # gate 2
            m, sd = tightest(o, line)
            if m < GATE3: continue                                                   # gate 3
            hit, err, other = route(BASE + [dict(name='cons', gap=o, line=line, pub_day=7)])
            if len(hit) < 12 or len(other) > 1: continue                             # gate 4
            elig[(k, back, line)] = (hit, err, other, e, comb, m)
            P(f'    {k:2d} {back:4d} {line:6.0f} {e:5.1f} {comb:6.2f} {m:+7.2f}  {hit[pd.Timestamp("1973-11-01")]:5d} '
              f'{hit[pd.Timestamp("2007-12-01")]:5d} {max(hit.values()):5d} {np.median(list(hit.values())):4.0f} '
              f'{np.mean([abs(x) for x in err.values()]):5.2f}  {other}')
P(f'    {len(elig)} settings eligible.')
if not elig: P('    nothing passes all four gates: the object is refused.'); log.close(); sys.exit()

P('\nLEAVE-ONE-RECESSION-OUT among the ELIGIBLE (the sum of the kept lags, then the kept date errors, ties to the wider margin):')
picks = []
for p in PK:
    best = None
    for key, (hit, err, other, e, comb, m) in elig.items():
        sc = (sum(v for q, v in hit.items() if q != p), sum(abs(v) for q, v in err.items() if q != p), -m)
        if best is None or sc < best[0]: best = (sc, key)
    key = best[1]; hit, err, other, e, comb, m = elig[key]; picks.append(key)
    P(f'    leave out {p:%Y-%m}: picks k={key[0]} back={key[1]:2d} line {key[2]:.0f}k (exposure {e:.1f}%, OR {comb:.2f}%, margin {m:+.2f} sd); '
      f'held-out lag {hit[p]:+d} against {b[p]:+d}, date {err[p]:+d} against {be[p]:+d}')
P(f'    every fold the same: {len(set(picks)) == 1} {set(picks)}')
k, back, line = picks[0]; hit, err, other, e, comb, m = elig[(k, back, line)]
P(f'\nTHE FOLDS\' CHOICE: construction employment, {k}-month reading {line:.0f},000 below its trailing {back}-month maximum,')
P(f'  published the first Friday. Exposure {e:.1f}%; the OR of the second condition {comb:.2f}% against the shipped {SHIPPED_OR:.2f}% - UNCHANGED;')
P(f'  the tightest disturbance margin {m:+.2f} sd against the shipped condition\'s own {GATE3:+.2f}.')
P(f'  median {np.median(list(hit.values())):.0f} d (was {np.median(list(b.values())):.0f}), worst {max(hit.values())} (was {max(b.values())}), '
  f'within a month {sum(0 <= v <= 30 for v in hit.values())}/12 (was {sum(0 <= v <= 30 for v in b.values())}), '
  f'mae {np.mean([abs(x) for x in err.values()]):.2f} (was {np.mean([abs(x) for x in be.values()]):.2f}), other {other}')
P('  ' + '  '.join(f'{p:%Y-%m}:{v:+d}[{err[p]:+d}]' + (f'(was {b[p]:+d})' if v != b[p] else '') for p, v in hit.items()))
marg_table(fall(k, back), line, 'the chosen object at the three disturbance calls')
P('\n1966-67, the case that refused housing starts: starts halved; construction PAYROLLS, month by month:')
o = fall(k, back); seg = o['1965-06':'1968-08']
P('  ' + '  '.join(f'{t:%y-%m}:{v:.0f}' for t, v in seg.items()))
log.close()
