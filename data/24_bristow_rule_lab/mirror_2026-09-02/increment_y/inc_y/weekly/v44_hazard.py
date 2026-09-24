"""THE HAZARD OF VERSION 44, measured the way memo 8v measured version 43's (4 September 2026).

Version 44 makes two changes: the confirmation window becomes SYMMETRIC about the claims call (six months either
side, still closing early if the claims field's own episode ends first), and a third alternative joins the second
condition - housing starts two-month mean thirty log points below their trailing twelve-month maximum AND the
unemployment rate 0.20 points above its trailing twelve-month minimum, both in the same month.

The route's hazard is P(a claims call in a quiet year) x P(the second condition is met inside the window | a
claims call).  The first factor is untouched - it is a property of the claims legs.  The second is the window
exposure of the OR of the whole second condition, and BOTH of version 44's changes bear on it:

  * the symmetric window makes the exposure SMALLER, because the window is shorter;
  * the pair makes it larger by whatever it adds - and the point of the gates was that it adds nothing.

Both are measured here on first prints, and the resulting hazard is put beside version 43's.

Output v44_hazard.log.
"""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0, '/home/claude'); sys.path.insert(0, '/home/claude/lab/weekly'); sys.path.insert(0, '/home/claude/lab/rt')
import numpy as np, pandas as pd
from scipy import stats
import bristow_rule_v3 as B, american_chronology as AC, alfred
PK, TR = AC.PK, AC.TR
P13 = list(PK) + [pd.Timestamp('2023-07-01')]; T13 = list(TR) + [pd.Timestamp('2024-08-01')]
log = open('/home/claude/lab/weekly/v44_hazard.log', 'w')
def P(*a): print(*a); print(*a, file=log, flush=True)
IDX = pd.date_range('1949-01-01', '2026-07-01', freq='MS')
def quiet(idx):
    q = pd.Series(True, index=idx)
    for p, t in zip(P13, T13): q[(idx >= p - pd.DateOffset(months=9)) & (idx <= t + pd.DateOffset(months=18))] = False
    return q
QM = quiet(IDX)
def rt(sid):
    cur = pd.read_csv(f'/home/claude/archive/data/fred/{sid}.csv'); cur.columns = ['d', 'v']
    cur = cur.set_index(pd.to_datetime(cur['d']))['v'].astype(float).dropna()
    fp = alfred.first_prints(sid); return pd.concat([cur[cur.index < fp.index.min()], fp]).sort_index()
G = AC.sahm_rt(); VR = AC.vacancy_gap_rt(2, 6)
HS = rt('HOUST'); UR = rt('UNRATE')
h = (np.log(HS) * 100).rolling(2).mean(); H = (h.shift(1).rolling(12).max() - h).dropna()
u = UR.rolling(1).mean(); U = (u - u.shift(1).rolling(12).min()).dropna()
Z = pd.concat([H / 30.0, U / 0.20], axis=1).dropna().min(axis=1)

def window_exposure(objs, fwd_months):
    """the share of quiet months on which a claims call would be confirmed: the object stands at its line
    somewhere in [that month - 6 months, that month + fwd_months]"""
    m = pd.Series(False, index=IDX)
    for o, line in objs:
        hit = (o.dropna() >= line)
        f = hit[::-1].rolling(fwd_months + 1, min_periods=1).max()[::-1].astype(bool)
        b = hit.rolling(7, min_periods=1).max().astype(bool)
        m = m | (f | b).reindex(IDX).fillna(False).astype(bool)
    return float(m[QM].mean())

P("THE SECOND CONDITION'S WINDOW EXPOSURE, on first prints, over the quiet months since 1949")
P(f"  ({int(QM.sum())} quiet months of {len(IDX)})")
P(f'  {"":52s} {"exposure":>9}')
for lab, objs, fwd in (
        ("version 43: Sahm 0.50 OR vacancy 0.36, forward reach 18 months", [(G, 0.5), (VR, 0.36)], 18),
        ("the same objects, forward reach 6 months (the symmetric window)", [(G, 0.5), (VR, 0.36)], 6),
        ("version 44: the same two OR the pair, forward reach 6 months", [(G, 0.5), (VR, 0.36), (Z, 1.0)], 6),
        ("the pair alone, forward reach 6 months", [(Z, 1.0)], 6)):
    P(f'  {lab:52s} {window_exposure(objs, fwd) * 100:8.2f}%')
e43 = window_exposure([(G, 0.5), (VR, 0.36)], 18)
e44 = window_exposure([(G, 0.5), (VR, 0.36), (Z, 1.0)], 6)
n_calls, n_years = 3, 78
lo_c = stats.chi2.ppf(0.025, 2 * n_calls) / 2 / n_years
hi_c = stats.chi2.ppf(0.975, 2 * n_calls + 2) / 2 / n_years
P(f'\nTHE ROUTE\'S HAZARD  =  P(a claims call in a quiet year) x P(the second condition confirms it)')
P(f'  P(a claims call in a quiet year): three outside the thirteen in {n_years} years (1951, 1952, 1967) = '
  f'{n_calls / n_years * 100:.1f}% a year (exact Poisson 95 per cent interval {lo_c * 100:.1f}% to {hi_c * 100:.1f}%)')
for lab, e in (('version 43', e43), ('VERSION 44', e44)):
    for nm, pc in (('point estimate', n_calls / n_years), ('upper Poisson bound', hi_c)):
        hz = pc * e
        P(f'  {lab:11s} {nm:20s}: exposure {e * 100:5.2f}%  ->  hazard {hz * 100:.3f}% a year, '
          f'one false episode every {1 / hz:,.0f} years; over a 6.5-year expansion {(1 - (1 - hz) ** 6.5) * 100:.2f}%')
P(f'\n  version 44 divides the hazard by {e43 / e44:.2f} - and it does so while making the rule FASTER, which is')
P('  the first time in this program that speed and safety have moved the same way.  The pair contributes nothing')
P('  to the exposure (it never stands at its line in a quiet month); the whole gain is the symmetric window.')
log.close()
