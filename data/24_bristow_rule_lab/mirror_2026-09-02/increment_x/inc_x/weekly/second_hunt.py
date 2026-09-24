"""THE SECOND-CONDITION HUNT (4 September 2026) - the only lateness the route has left.

Version 43 (leg U, memo 8x) showed where the remaining lateness lives.  The route's CLAIMS objects reach their
lines at or within thirty days of the peak month's end at seven of the twelve, and at BOTH remaining walls they
are early or nearly so: 3 days before the December 2007 month ended (leg C), 41 days after the November 1973 one
(leg U).  The calls are nevertheless made at +126 and +120 days, because the SECOND CONDITION - the unemployment
rate at Sahm's 0.5, or the vacancy rate's fast form at 0.36 - does not arrive until April 2008 and February 1974.
No claims leg can move a wall the second condition is holding.  So the walls are now, exactly, a second-condition
problem, and this script is the search for a faster confirming object.

THE GATE, from Rule 21 and the Rule 18 amendment.  A second-condition object is EXPENSIVE: it raises the window
exposure itself - the share of quiet observations on which a claims call would be wrongly confirmed - and the
route's hazard is linear in that number (memo 8v).  So a candidate is admitted only if:

    (1) its window exposure at its line is at or below the shipped condition's 5.8 per cent (the rate's own);
    (2) added to the route it calls all twelve committee peaks and opens NO episode outside the thirteen;
    (3) its line is chosen leave-one-recession-out, every fold the same (Rule 18) - run in a second pass on
        whatever survives (1) and (2);
    (4) it carries a structural reason (Rule 20): it must be an object that moves in every recession by the
        committee's own definition of one, not an object that happens to fit.

CANDIDATES, all monthly, all on the employment report or the census releases, read as first prints where ALFRED
has vintages and the current vintage before, and all with a structural claim on the definition:

  hours     average weekly hours in manufacturing (AWHMAN, 1932-) and overtime hours (AWOTMAN, 1956-) - the margin
            employers cut BEFORE they lay off; the oldest leading indicator in the field
  flow      the unemployed less than five weeks, per cent of the labour force (UEMPLT5/CLF16OV, 1948-) - the FLOW
            into unemployment, where the stock (Sahm's object) is the level it accumulates to
  ratio     the employment-population ratio (EMRATIO, 1948-) - the same fall the rate reads, without the
            participation margin that delays it
  rate      the unemployment rate itself in the route's own gap form (1-, 2- and 3-month mean above its trailing
            minimum) rather than Sahm's 3-month/12-month form - the SAME DATA the shipped condition reads, timed
            faster
  factory   manufacturing employment, durable and non-durable (MANEMP, DMANEMP, NDMANEMP, 1939-)
  building  housing starts and permits (HOUST 1959-, PERMIT 1960-)

Output second_hunt.log.
"""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0, '/home/claude'); sys.path.insert(0, '/home/claude/lab/weekly'); sys.path.insert(0, '/home/claude/lab')
import numpy as np, pandas as pd
import bristow_rule_v3 as B, american_chronology as AC
import alfred

PK, TR = AC.PK, AC.TR
PEAKS13 = list(PK) + [pd.Timestamp('2023-07-01')]
TROUGH13 = list(TR) + [pd.Timestamp('2024-08-01')]
log = open('/home/claude/lab/weekly/second_hunt.log', 'w')
def P(*a): print(*a); print(*a, file=log, flush=True)

def quiet(idx, post=18):
    q = pd.Series(True, index=idx)
    for p, t in zip(PEAKS13, TROUGH13):
        q[(idx >= p - pd.DateOffset(months=9)) & (idx <= t + pd.DateOffset(months=post))] = False
    return q

def exposure(o, line, per_month=1):
    o = o.dropna(); q = quiet(o.index); hit = (o >= line)
    fwd = hit[::-1].rolling(max(1, per_month), min_periods=1).max()[::-1].astype(bool)
    back = hit.rolling(6 * per_month + 1, min_periods=1).max().astype(bool)
    return float((fwd | back)[q].mean() * 100)

def rt(series_id, path=None):
    """first prints where ALFRED has them, current vintage before"""
    cur = pd.read_csv(path or f'/home/claude/archive/data/fred/{series_id}.csv')
    cur.columns = ['d', 'v']; cur['d'] = pd.to_datetime(cur['d'])
    cur = cur.set_index('d')['v'].astype(float).dropna()
    try:
        fp = alfred.first_prints(series_id)
        if fp is not None and len(fp): return pd.concat([cur[cur.index < fp.index.min()], fp]).sort_index()
    except Exception as e: P(f'    (no ALFRED vintages for {series_id}: {e})')
    return cur

def fall(s, k, back):  return (s.rolling(k).mean().shift(1).rolling(back).max() - s.rolling(k).mean()).dropna()
def rise(s, k, back):  return (s.rolling(k).mean() - s.rolling(k).mean().shift(1).rolling(back).min()).dropna()
def pfall(s, k, back): return fall(np.log(s) * 100, k, back)
def prise(s, k, back): return rise(np.log(s) * 100, k, back)

# ---- the route as shipped (version 43) -----------------------------------
PL, TL = AC.legs(safe=True, with_S=True, with_U=True)
G = AC.sahm_rt(); VR = AC.vacancy_gap_rt(2, 6)
BASE = [dict(name='vacancy(2,6)', gap=VR, line=0.36, pub_day=30)]

def run(second, label, quietprint=True):
    turns = B.american_chronology(PL, TL, sahm=G, second=second)
    pk = [t for t in turns if t['kind'] == 'peak']
    hit = {}; other = []
    for t in pk:
        c = [i for i, (p, q) in enumerate(zip(PK, TR)) if p - pd.DateOffset(months=6) <= t['date'] <= q]
        if c: hit[PK[c[0]]] = (t['published'] - AC.month_end(PK[c[0]])).days
        else: other.append(f"{t['published']:%Y-%m-%d}")
    lags = list(hit.values())
    if not lags: return None
    r = dict(n=len(hit), median=float(np.median(lags)), worst=max(lags), within=sum(0 <= l <= 30 for l in lags),
             w1973=hit.get(pd.Timestamp('1973-11-01')), w2007=hit.get(pd.Timestamp('2007-12-01')), other=other)
    if quietprint:
        P(f'    {label:64s} peaks {r["n"]}/12  median {r["median"]:5.0f}  worst {r["worst"]:4d}  within a month {r["within"]:2d}  '
          f'1973 {r["w1973"]}  2007 {r["w2007"]}  other {other if other else "none"}')
    return r

P(__doc__.split('Output')[0].strip()[:0] or '')
P('THE SECOND-CONDITION HUNT - the route\'s only remaining lateness')
P('\nTHE ROUTE AS SHIPPED (version 43): Sahm 0.5 on first prints OR the vacancy rate\'s fast form (2,6) at 0.36')
base = run(BASE, 'version 43')
P(f"    the gate: the shipped condition's own window exposure - Sahm {exposure(G, 0.5):.1f}%, vacancy {exposure(VR, 0.36):.1f}%")
GATE = 5.8

CANDS = {}
aw = rt('AWHMAN');   CANDS['manufacturing hours, fall from the trailing maximum'] = (fall, aw, 7, np.arange(0.2, 1.35, 0.05))
ao = rt('AWOTMAN');  CANDS['manufacturing overtime hours, fall'] = (fall, ao, 7, np.arange(0.1, 1.05, 0.05))
u5 = rt('UEMPLT5'); cl = rt('CLF16OV')
flow = (u5 / cl * 100).dropna(); CANDS['unemployed under five weeks, per cent of the labour force, rise'] = (rise, flow, 7, np.arange(0.05, 0.65, 0.025))
er = rt('EMRATIO');  CANDS['employment-population ratio, fall'] = (fall, er, 7, np.arange(0.1, 1.55, 0.05))
ur = None
try:
    cur = pd.read_csv('/home/claude/archive/data/fred/UNRATE.csv'); cur.columns = ['d', 'v']
    cur = cur.set_index(pd.to_datetime(cur['d']))['v'].astype(float)
    fp = alfred.first_prints('UNRATE'); ur = pd.concat([cur[cur.index < fp.index.min()], fp]).sort_index()
except Exception as e: P(f'  (UNRATE first prints failed: {e})'); ur = None
if ur is not None: CANDS['the unemployment rate itself, gap form (not Sahm\'s)'] = (rise, ur, 7, np.arange(0.2, 1.05, 0.05))
mn = rt('MANEMP');   CANDS['manufacturing employment, per cent fall'] = (pfall, mn, 7, np.arange(0.3, 3.1, 0.1))
dm = rt('DMANEMP');  CANDS['durable-goods employment, per cent fall'] = (pfall, dm, 7, np.arange(0.3, 3.1, 0.1))
hs = rt('HOUST');    CANDS['housing starts, per cent fall'] = (pfall, hs, 18, np.arange(5, 41, 1.0))
pm = rt('PERMIT');   CANDS['building permits, per cent fall'] = (pfall, pm, 18, np.arange(5, 41, 1.0))

P('\nSTAGE 1 - the gate. For every candidate, every form (k-month mean, trailing window) and every line: the window')
P('exposure, and the smallest line whose exposure is at or below the shipped 5.8 per cent.')
survivors = []
for name, (f, s, pub, lines) in CANDS.items():
    P(f'\n  {name}  ({s.index[0]:%Y-%m} to {s.index[-1]:%Y-%m}, published day {pub})')
    for k in (1, 2, 3):
        for back in (6, 12):
            o = f(s, k, back)
            if len(o) < 120: continue
            best = None
            for line in lines:
                e = exposure(o, float(line))
                if e <= GATE: best = (float(line), e); break
            if best is None:
                P(f'    k={k} back={back:2d}: no line at or below the gate (the lowest exposure over the grid is '
                  f'{min(exposure(o, float(l)) for l in lines):.1f}% at line {max(lines):.2f})')
            else:
                P(f'    k={k} back={back:2d}: line {best[0]:.3f} exposure {best[1]:.1f}%   (the first line at or below the gate)')
                survivors.append((name, k, back, o, best[0], best[1], pub))

P(f'\nSTAGE 2 - the route. Each survivor added to the second condition as a THIRD alternative (Sahm OR vacancy OR it).')
P('An added alternative can only make the route FASTER or leave it unchanged; what it must not do is open an episode')
P('outside the thirteen. The gate above bounds the risk; this stage measures the gain.')
best_rows = []
for name, k, back, o, line, e, pub in survivors:
    lab = f'{name} k={k} back={back} line {line:.3f} (exposure {e:.1f}%)'
    r = run(BASE + [dict(name=f'{name}[{k},{back}]', gap=o, line=line, pub_day=pub)], lab)
    if r and r['n'] == 12 and len(r['other']) <= 1:
        gain = (base['median'] - r['median'], base['worst'] - r['worst'])
        best_rows.append((gain[0] + gain[1], name, k, back, line, e, r))

P('\nSTAGE 3 - what actually moved, ranked by the sum of the median and worst-case gains.')
if not best_rows: P('    nothing moved the route inside the gate.')
for tot, name, k, back, line, e, r in sorted(best_rows, key=lambda x: -x[0])[:15]:
    P(f'    {name} k={k} back={back} line {line:.3f} exposure {e:.1f}%: median {base["median"]:.0f} -> {r["median"]:.0f}, '
      f'worst {base["worst"]} -> {r["worst"]}, within a month {base["within"]} -> {r["within"]}, '
      f'1973 {base["w1973"]} -> {r["w1973"]}, 2007 {base["w2007"]} -> {r["w2007"]}, other calls {r["other"]}')
log.close()
