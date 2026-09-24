"""STAGE 4 OF THE SECOND-CONDITION HUNT (4 September 2026): the survivor, put through Rule 18 and Rule 21.

Stage 1-3 (`second_hunt.py`) swept every fast monthly object with a structural claim on the committee's definition,
gated each at the shipped condition's own window exposure (5.8 per cent), and found ONE candidate that moves both
remaining walls: HOUSING STARTS, the one-month level 36 per cent or more below its trailing six-month maximum,
published the 18th of the month after, read as FIRST PRINTS from July 1960 (the first ALFRED vintage - genuine
real time across both walls, which EMRATIO 1996 and UEMPLT5 no-vintages are not).

    version 43            1973 +120 d   2007 +126 d   worst 126   within a month 4/12
    with housing starts   1973  +41 d   2007  +18 d   worst  90   within a month 5/12

This script asks the four questions that decide whether it may be adopted.

  (1) LEAVE-ONE-RECESSION-OUT (Rule 18): is the form and the line the folds' own choice, or the sweep's?
  (2) THE KNIFE EDGE (the discipline of memo 8h): how much of the grid around the chosen line behaves the same
      way?  A clause that works at one line and fails at the next is a fitted clause.
  (3) 1966-67 (Rule 21, no future false alarms): the credit crunch of 1966 halved housing starts.  The route
      makes a claims call in February 1967.  How close does the object come to confirming it, in its own units
      and in its own standard deviations?  If the margin is thin the clause is refused however much speed it buys.
  (4) THE COMBINED EXPOSURE: the gate is per object, but the hazard is set by the OR of the whole second
      condition.  What does the route's window exposure become, and what does that do to the hazard of memo 8v?

Output second_hunt2.log.
"""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0, '/home/claude'); sys.path.insert(0, '/home/claude/lab/weekly'); sys.path.insert(0, '/home/claude/lab/rt')
import numpy as np, pandas as pd
import bristow_rule_v3 as B, american_chronology as AC, alfred

PK, TR = AC.PK, AC.TR
PEAKS13 = list(PK) + [pd.Timestamp('2023-07-01')]
TROUGH13 = list(TR) + [pd.Timestamp('2024-08-01')]
log = open('/home/claude/lab/weekly/second_hunt2.log', 'w')
def P(*a): print(*a); print(*a, file=log, flush=True)

def quiet(idx, post=18):
    q = pd.Series(True, index=idx)
    for p, t in zip(PEAKS13, TROUGH13):
        q[(idx >= p - pd.DateOffset(months=9)) & (idx <= t + pd.DateOffset(months=post))] = False
    return q

def exposure_series(o, line, per_month=1):
    o = o.dropna(); hit = (o >= line)
    fwd = hit[::-1].rolling(max(1, per_month), min_periods=1).max()[::-1].astype(bool)
    back = hit.rolling(6 * per_month + 1, min_periods=1).max().astype(bool)
    return (fwd | back)

def exposure(o, line, per_month=1):
    o = o.dropna(); q = quiet(o.index)
    return float(exposure_series(o, line, per_month)[q].mean() * 100)

PL, TL = AC.legs(safe=True, with_S=True, with_U=True)
G = AC.sahm_rt(); VR = AC.vacancy_gap_rt(2, 6)
BASE = [dict(name='vacancy(2,6)', gap=VR, line=0.36, pub_day=30)]
hs_rt = alfred.first_prints('HOUST')                       # genuine first prints from July 1960
hs_cur = pd.read_csv('/home/claude/archive/data/fred/HOUST.csv'); hs_cur.columns = ['d', 'v']
hs_cur = hs_cur.set_index(pd.to_datetime(hs_cur['d']))['v'].astype(float).dropna()
hs = pd.concat([hs_cur[hs_cur.index < hs_rt.index.min()], hs_rt]).sort_index()

def pfall(s, k, back):
    m = np.log(s) * 100.0; m = m.rolling(k).mean()
    return (m.shift(1).rolling(back).max() - m).dropna()

def route(second, peaks=None):
    turns = B.american_chronology(PL, TL, sahm=G, second=second)
    pk = [t for t in turns if t['kind'] == 'peak']
    hit = {}; other = []
    for t in pk:
        c = [i for i, (p, q) in enumerate(zip(PK, TR)) if p - pd.DateOffset(months=6) <= t['date'] <= q]
        if c: hit[PK[c[0]]] = (t['published'] - AC.month_end(PK[c[0]])).days
        else: other.append(f"{t['published']:%Y-%m-%d}")
    return hit, other

def add(k, back, line): return BASE + [dict(name=f'starts[{k},{back}]', gap=pfall(hs, k, back), line=line, pub_day=18)]

P('STAGE 4 - HOUSING STARTS AS A THIRD ALTERNATIVE IN THE SECOND CONDITION')
P(f'  the object: first prints from {hs_rt.index.min():%Y-%m} (ALFRED vintage {alfred.vintages("HOUST")[0]:%Y-%m-%d}); '
  f'current vintage {hs_cur.index.min():%Y-%m} to {hs_rt.index.min():%Y-%m}')
base_hit, base_other = route(BASE)
P(f'  version 43 base: median {np.median(list(base_hit.values())):.0f} d, worst {max(base_hit.values())}, '
  f'within a month {sum(0 <= l <= 30 for l in base_hit.values())}/12, 1973 {base_hit[pd.Timestamp("1973-11-01")]}, '
  f'2007 {base_hit[pd.Timestamp("2007-12-01")]}, other {base_other}')

# ---------- (1) leave one recession out ------------------------------------
P('\n(1) LEAVE-ONE-RECESSION-OUT over k in {1,2,3}, back in {6,12}, line 20 to 45 per cent in steps of one.')
P('    The fold score, in order: no episode outside the thirteen; then the sum of the lags at the ELEVEN peaks the')
P('    fold keeps (housing starts reach 1960); ties to the lower line. The held-out peak is then read.')
GRID = [(k, b, float(l)) for k in (1, 2, 3) for b in (6, 12) for l in np.arange(20, 45.5, 1.0)]
cache = {}
for k, b, l in GRID:
    hit, other = route(add(k, b, l)); cache[(k, b, l)] = (hit, other, exposure(pfall(hs, k, b), l))
picks = []
for i, p in enumerate(PK):
    if p < pd.Timestamp('1960-01-01'): continue
    best = None
    for key, (hit, other, ex) in cache.items():
        if len(other) > 1 or ex > 5.8 or len(hit) < 12: continue
        keep = [v for q, v in hit.items() if q != p]
        s = (len(other), sum(keep), key[2])
        if best is None or s < best[0]: best = (s, key)
    if best is None: P(f'    leave out {p:%Y-%m}: nothing inside the gate'); continue
    key = best[1]; hit, other, ex = cache[key]
    picks.append(key)
    P(f'    leave out {p:%Y-%m}: picks k={key[0]} back={key[1]:2d} line {key[2]:.0f}%  (exposure {ex:.1f}%); '
      f'held-out lag {hit[p]:+d} d against {base_hit[p]:+d}')
P(f'    every fold the same: {len(set(picks)) == 1} {set(picks)}')

# ---------- (2) the knife edge ---------------------------------------------
P('\n(2) THE KNIFE EDGE. Every (k, back, line) inside the gate, with the two walls and the calls outside the thirteen.')
P('    A clause is a knife edge if the neighbours of its line behave differently.')
rows = []
for (k, b, l), (hit, other, ex) in sorted(cache.items()):
    if ex > 5.8 or len(hit) < 12: continue
    rows.append((k, b, l, ex, hit[pd.Timestamp('1973-11-01')], hit[pd.Timestamp('2007-12-01')],
                 max(hit.values()), sum(0 <= v <= 30 for v in hit.values()), other))
P(f'    {"k":>2} {"back":>4} {"line":>5} {"expo":>5}  {"1973":>5} {"2007":>5} {"worst":>5} {"in month":>8}  outside the thirteen')
for k, b, l, ex, w73, w07, wo, inm, other in rows:
    flag = '  <-- both walls' if (w73 <= 60 and w07 <= 40 and len(other) <= 1) else ''
    P(f'    {k:2d} {b:4d} {l:5.0f} {ex:5.1f}  {w73:5d} {w07:5d} {wo:5d} {inm:8d}  {other if other else "none"}{flag}')
clean = [r for r in rows if len(r[8]) <= 1]
P(f'    of {len(rows)} settings inside the gate, {len(clean)} open no episode outside the thirteen; '
  f'of those, {sum(1 for r in clean if r[4] <= 60 and r[5] <= 40)} move BOTH walls.')

# ---------- (3) the disturbances, on the tool's OWN window ------------------
P("\n(3) THE THREE CLAIMS CALLS OUTSIDE THE THIRTEEN - 1951, 1952 and 1967 - read on the window the TOOL uses,")
P("    not on a calendar month. `american_chronology` slices the object at gg[claims call - 6 months : window end],")
P("    and the slice is by DATE: a claims call published on 20 April 1967 does not see the October 1966 reading,")
P("    because 1 October 1966 falls before 20 October 1966. That twenty days is the whole margin, as the numbers show.")
DIS = [(pd.Timestamp('1951-09-20'), 'July 1951'), (pd.Timestamp('1952-04-10'), 'March 1952'), (pd.Timestamp('1967-04-20'), 'February 1967')]
def wall_margin(o, line, label, pub_day, months=6):
    o = o.dropna(); sd = float(o[quiet(o.index)].std())
    P(f'    {label}  (line {line:g}, quiet standard deviation {sd:.2f})')
    for call, nm in DIS:
        seg = o[call - pd.DateOffset(months=months): call + pd.DateOffset(months=12)]
        seg = seg[:call + pd.DateOffset(months=12)]
        if not len(seg):
            P(f'      {nm:15s} the series does not reach it (a wall on this object, not a pass)'); continue
        mx = float(seg.max()); at = seg.idxmax()
        cal = o[call - pd.DateOffset(months=months+1): call + pd.DateOffset(months=12)]
        P(f'      {nm:15s} window {seg.index[0]:%Y-%m} to {seg.index[-1]:%Y-%m}: maximum {mx:6.2f} in {at:%Y-%m}, '
          f'margin {line - mx:+6.2f} ({(line - mx) / sd:+.2f} sd)'
          + (f'   [one month earlier the window would carry {float(cal.max()):.2f} in {cal.idxmax():%Y-%m}]' if float(cal.max()) > mx else ''))
wall_margin(pfall(hs, 1, 6), 36.0, 'housing starts, one month, 36 per cent below the trailing six-month maximum', 18)
P('    1951 and 1952 are before January 1959 and cannot be read at all: housing starts can only ever be a THIRD')
P('    alternative beside the two objects that reach 1948, never a replacement for them.')

# ---------- (4) the combined exposure ---------------------------------------
P('\n(4) THE COMBINED EXPOSURE - the hazard is set by the OR of the whole second condition, not by any one object.')
idx = pd.date_range('1960-01-01', '2026-07-01', freq='MS')
def align(o, line, per_month=1):
    e = exposure_series(o, line, per_month)
    return e.reindex(idx).fillna(False).astype(bool)
eS = align(G, 0.5); eV = align(VR, 0.36); eH = align(pfall(hs, 1, 6), 36.0)
q = quiet(idx)
P(f'    on the common months {idx[0]:%Y-%m} to {idx[-1]:%Y-%m} ({int(q.sum())} quiet):')
P(f'      Sahm alone                    {eS[q].mean() * 100:5.2f}%')
P(f'      vacancy alone                 {eV[q].mean() * 100:5.2f}%')
P(f'      housing starts alone          {eH[q].mean() * 100:5.2f}%')
P(f'      the shipped OR (Sahm, vacancy){(eS | eV)[q].mean() * 100:5.2f}%')
P(f'      the OR with housing starts    {(eS | eV | eH)[q].mean() * 100:5.2f}%')
inc = (eS | eV | eH)[q].mean() / max(1e-12, (eS | eV)[q].mean())
P(f'    the multiplier on the route\'s hazard: {inc:.2f}x')
for lab, pc in (('point estimate', 3 / 78), ('upper Poisson bound', 0.112)):
    lo0, hi0 = pc * (eS | eV)[q].mean(), pc * (eS | eV)[q].mean()
    lo1, hi1 = pc * (eS | eV | eH)[q].mean(), pc * (eS | eV | eH)[q].mean()
    P(f'      hazard, {lab}: {lo0 * 100:.3f}% a year -> {lo1 * 100:.3f}% a year '
      f'(one in {1 / lo0:,.0f} -> one in {1 / lo1:,.0f} years)')
log.close()
