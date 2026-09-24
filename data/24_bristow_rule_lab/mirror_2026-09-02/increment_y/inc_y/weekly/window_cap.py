"""THE CONFIRMATION WINDOW'S FORWARD REACH - the parameter never varied (4 September 2026).

Anthony: "we almost succeeded in something revolutionary.  Try more options like it.  WE CAN GET IT FASTER."

He is right that the search stopped one step early.  Five candidates were refused in memo 8y, 8aa, 8ab and 8ac,
and every one of them was refused on the SAME case - February 1967 - and in the same way: the object reaches its
line somewhere in 1967 or 1968, long after the claims call, and so would have confirmed a disturbance.  What was
never questioned is WHY it gets the chance.  `american_chronology` gives a claims call a confirmation window of

    [ the claims call - back_months , the claims field's own end of that episode ]

and the claims field's 1967 episode runs from 20 April 1967 to 20 August 1968.  So the second condition has
SIXTEEN MONTHS after the 1967 claims call in which to trip.  Housing starts tripped it in June 1968, fourteen
months after; construction employment on first prints in June 1968; the pair in June 1968.  Every refusal in this
version traces to readings more than a year after the call.

In the twelve real recessions the second condition does not need anything like that long.  So this script asks a
question nobody has asked: what if the window's FORWARD reach is capped?

    cap h:  the window is [ call - back_months , min( the claims field's end , call + h months ) ]

If the twelve still confirm at h = 6 or 9 - and they should, because the shipped condition's own crossings arrive
within a few months - then the disturbance exposure of every candidate collapses, and the refusals of 8y-8ac must
all be re-scored.  The cap is itself a clause and must be chosen leave-one-recession-out like any other.

Output window_cap.log.
"""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0, '/home/claude'); sys.path.insert(0, '/home/claude/lab/weekly'); sys.path.insert(0, '/home/claude/lab/rt')
import numpy as np, pandas as pd
import bristow_rule_v3 as B, american_chronology as AC
PK, TR = AC.PK, AC.TR
log = open('/home/claude/lab/weekly/window_cap.log', 'w')
def P(*a): print(*a); print(*a, file=log, flush=True)

PL, TL = AC.legs(safe=True, with_S=True, with_U=True)
G = AC.sahm_rt(); VR = AC.vacancy_gap_rt(2, 6)
SECOND = [dict(name='vacancy(2,6)', gap=VR, line=0.36, pub_day=30)]

# how long after each claims call does the shipped condition actually arrive?
plain = B.american_chronology(PL, TL)
CL = [(t['published'], t['date']) for t in plain if t['kind'] == 'peak']
ENDS = {}
for i, t in enumerate(plain):
    if t['kind'] == 'peak':
        nxt = [u for u in plain[i + 1:] if u['kind'] == 'trough']
        ENDS[t['published']] = nxt[0]['published'] if nxt else pd.Timestamp('2027-01-01')

def first_cross(o, line, call, end):
    seg = o[call - pd.DateOffset(months=6): end]
    t = next((tt for tt, v in seg.items() if v >= line), None)
    return t

P('HOW LONG THE SHIPPED SECOND CONDITION ACTUALLY TAKES, claims call by claims call')
P('  (the crossing month, and its distance in months from the month of the claims call)')
rows = []
for call, d in CL:
    end = ENDS[call]
    a = first_cross(G, 0.5, call, end); b = first_cross(VR, 0.36, call, end)
    best = min([x for x in (a, b) if x is not None], default=None)
    which = 'Sahm' if best is not None and best == a else ('vacancy' if best is not None else '-')
    lab = next((f'{p:%Y-%m}' for p, q in zip(PK, TR) if p - pd.DateOffset(months=9) <= call <= q), 'DISTURBANCE')
    if best is None:
        P(f'  claims call {call:%Y-%m-%d}  ({lab:12s})  never confirmed inside the window (end {end:%Y-%m-%d})')
    else:
        m = (best.year - call.year) * 12 + (best.month - call.month)
        rows.append((lab, m))
        P(f'  claims call {call:%Y-%m-%d}  ({lab:12s})  first crossing {best:%Y-%m} by {which:8s} = {m:+3d} months from the call; '
          f'the window runs to {end:%Y-%m-%d} ({(end.year-call.year)*12+(end.month-call.month):+3d} months)')
real = [m for lab, m in rows if lab != 'DISTURBANCE']
P(f'\n  on the twelve: crossings from {min(real):+d} to {max(real):+d} months from the claims call; '
  f'median {np.median(real):+.0f}; the largest is what any forward cap must clear.')

P('\nTHE CAP, run through the route. h = months after the claims call at which the window closes.')
P(f'  {"cap":>5}  peaks  other calls                median  worst  in-month  mae')
def route(cap):
    if cap is None:
        turns = B.american_chronology(PL, TL, sahm=G, second=SECOND)
    else:
        turns = B.american_chronology(PL, TL, sahm=G, second=SECOND, horizon_months=cap)
    hit = {}; err = {}; other = []
    for x in [y for y in turns if y['kind'] == 'peak']:
        c = [i for i, (p, q) in enumerate(zip(PK, TR)) if p - pd.DateOffset(months=6) <= x['date'] <= q]
        if c:
            hit[PK[c[0]]] = (x['published'] - AC.month_end(PK[c[0]])).days
            err[PK[c[0]]] = (x['date'].year - PK[c[0]].year) * 12 + (x['date'].month - PK[c[0]].month)
        else: other.append(f"{x['published']:%Y-%m-%d}")
    return hit, err, other
import inspect
sig = inspect.signature(B.american_chronology)
P(f'  (american_chronology signature carries: {", ".join(sig.parameters)})')
for cap in (3, 4, 5, 6, 8, 9, 12, 18, 24, 36):
    hit, err, other = route(cap)
    if len(hit) < 12:
        P(f'  {cap:5d}  {len(hit):5d}  MISSES - not admissible')
        continue
    P(f'  {cap:5d}  {len(hit):5d}  {str(other):26s} {np.median(list(hit.values())):6.0f} {max(hit.values()):6d} '
      f'{sum(0 <= v <= 30 for v in hit.values()):9d}  {np.mean([abs(x) for x in err.values()]):.2f}')
h, e, o = route(None)
P(f'  {"none":>5}  {len(h):5d}  {str(o):26s} {np.median(list(h.values())):6.0f} {max(h.values()):6d} '
  f'{sum(0 <= v <= 30 for v in h.values()):9d}  {np.mean([abs(x) for x in e.values()]):.2f}   <- as shipped')
log.close()
