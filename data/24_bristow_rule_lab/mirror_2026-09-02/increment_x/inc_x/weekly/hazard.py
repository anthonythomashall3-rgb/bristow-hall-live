"""The route's false-alarm hazard, measured (4 September 2026) - the method taken from the Paper 2 chat's round 17
(`claude/paper2-ladder-round17-false-alarm-and-miss-risk-2026-09-04.md`), applied to this route.

Anthony's Rules 20 and 21 ask for a number, not an argument alone.  Three estimates of the same quantity:

  (a) THE RECORD.  Zero episodes outside the thirteen since 1949.  By the rule of three the annual rate is at most
      3/N at 95 per cent confidence, N the count of quiet years.

  (b) EXTREME VALUE.  For each object of the route, take its annual maximum over QUIET years (a year with no month
      inside [peak - 9 months, trough + 18 months] of the thirteen), fit a generalized extreme-value distribution by
      maximum likelihood, and read off the probability that a quiet year's maximum clears the object's line.

  (c) THE CONJUNCTION.  This route does not fire on any single object: a peak call needs a CLAIMS object at its line
      AND the second condition (the unemployment rate at Sahm's 0.5 or the vacancy rate's fast form at 0.36) inside
      the window.  So the route's hazard is P(a claims object clears in a quiet year) x P(the second condition is met
      in the window | a claims call), and the second factor is the window exposure of `window_exposure.py` - or, read
      on the record's own three disturbance calls, zero of three.  Both are reported.

Output hazard.log.
"""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0, '/home/claude'); sys.path.insert(0, '/home/claude/lab/weekly')
import numpy as np, pandas as pd
from scipy import stats
import bristow_rule_v3 as B, american_chronology as AC, legs_1948 as L

PEAKS = ['1948-11', '1953-07', '1957-08', '1960-04', '1969-12', '1973-11', '1980-01', '1981-07', '1990-07', '2001-03', '2007-12', '2020-02', '2023-07']
TROUGHS = ['1949-10', '1954-05', '1958-04', '1961-02', '1970-11', '1975-03', '1980-07', '1982-11', '1991-03', '2001-11', '2009-06', '2020-04', '2024-08']
M = lambda s: pd.Timestamp(s + '-01')
log = open('/home/claude/lab/weekly/hazard.log', 'w')
def P(*a): print(*a); print(*a, file=log)

def quiet_mask(idx, post=18):
    q = pd.Series(True, index=idx)
    for p, t in zip(PEAKS, TROUGHS):
        q[(idx >= M(p) - pd.DateOffset(months=9)) & (idx <= M(t) + pd.DateOffset(months=post))] = False
    return q

def gev_hazard(s, line, label, start=None):
    """P(a quiet year's maximum of `s` clears `line`), from a GEV fitted to the quiet annual maxima"""
    s = s.dropna()
    if start: s = s[start:]
    q = quiet_mask(s.index)
    sq = s[q]
    if len(sq) < 60: return None
    am = sq.groupby(sq.index.year).max()
    am = am[sq.groupby(sq.index.year).size() >= (len(sq) / max(1, sq.index.year.nunique())) * 0.5]   # years with most of their observations quiet
    if len(am) < 12: return None
    c, loc, sc = stats.genextreme.fit(am.values)
    p = float(stats.genextreme.sf(line, c, loc=loc, scale=sc))
    P(f'  {label:52s} quiet years {len(am):3d}  observed max {am.max():8.3f}  line {line:7.3f}  '
      f'GEV c={c:+.2f} loc={loc:.2f} scale={sc:.2f}  P(year clears) {p * 100:6.3f}%  '
      f'return period {"never" if p <= 0 else f"1 in {1 / p:,.0f} years"}')
    return p

P('THE ROUTE\'S FALSE-ALARM HAZARD (the method of the Paper 2 chat\'s round 17, applied to this route)')
P('\n(a) THE RECORD. Quiet years = a calendar year with no month inside [peak - 9 months, trough + 18 months] of the thirteen.')
allm = pd.date_range('1949-01-01', '2026-08-01', freq='MS'); qm = quiet_mask(allm)
qy = sorted({t.year for t in allm[qm] if (qm[allm.year == t.year]).all()})
P(f'    quiet years since 1949: {len(qy)}; ROUTE episodes opened in them: 0 (the route opens thirteen, every one inside a window).')
P(f'    rule of three on the route: the annual false-episode rate is at most 3/{len(qy)} = {3 / len(qy) * 100:.1f}% at 95 per cent confidence; the point estimate is zero.')
P('    the CLAIMS LEGS alone are a different matter: they opened three episodes outside the thirteen since 1949 - July 1951,')
P('    March 1952 and February 1967 - which is the rate the second condition has to cut down, and did (0 of 3 confirmed).')

P('\n(b) EXTREME VALUE, object by object. NOTE what this measures: the probability that an object TOUCHES its line in a quiet')
P('year, which is not the probability of a CALL - leg A calls on a censored crossing (a phase of five months, a cycle of')
P('fifteen), so its index touches fifty far more often than it opens an episode. The object-level numbers are the raw')
P('exposure; the call-level rate is measured on the calls themselves in (c).')
Pn = pd.read_csv('/home/claude/lab/fh/FH_state_claims_sa_rt_log.csv', index_col=0, parse_dates=True)
D = B.claims_diffusion(Pn.rolling(2).mean().dropna(how='all'), 36., 8)
ic, cc = L.national_nsa(); conj_m = B.claims_conjunct(ic, cc, weeks=12, smooth=1).resample('MS').max()
import cc_trough_grid as CG
Nw = pd.read_csv('/home/claude/lab/weekly/DOL_national_weekly_claims_sa_rt.csv', index_col=0, parse_dates=True)
conj_w = B.claims_conjunct(Nw['ic_sa_rt'], Nw['cc_sa_rt'], weeks=12, smooth=1) if 'ic_sa_rt' in Nw else None
hz = {}
hz['A'] = gev_hazard(D, 50.0, "leg A: the states' claims diffusion (36/8), line 50 per cent")
hz['M'] = gev_hazard(conj_m, 0.20, "leg M: the national monthly claims conjunct, line 0.20")
try:
    W = CG.W; br = None
    P('  (leg C, the weekly state breadth, is read from its own real-time file; its quiet maxima are in speed_final.log)')
except Exception: pass
P('\n  the second condition:')
hz['sahm'] = gev_hazard(AC.sahm_rt(), 0.5, "Sahm's gap on the rate as first published, line 0.50", start='1960')
hz['vac'] = gev_hazard(AC.vacancy_gap_rt(2, 6), 0.36, 'the vacancy rate\'s fast form (2,6), line 0.36', start='1949')

P('\n(c) THE CONJUNCTION - what the route actually requires, measured on the calls.')
P('    The route needs a CLAIMS CALL and the second condition met inside its window. Each factor, measured:')
n_calls, n_years = 3, 78
lo_c, hi_c = stats.chi2.ppf(0.025, 2 * n_calls) / 2 / n_years, stats.chi2.ppf(0.975, 2 * n_calls + 2) / 2 / n_years
P(f'      P(a claims call in a quiet year): three calls outside the thirteen in {n_years} years (1951, 1952, 1967) = '
  f'{n_calls / n_years * 100:.1f}% a year (exact Poisson 95 per cent interval {lo_c * 100:.1f}% to {hi_c * 100:.1f}%).')
P('      P(the second condition confirms it | a claims call): 0 of 3 on the record; from the window exposure of')
P('      window_exposure.py, 0.9 per cent (the vacancy form) to 6.5 per cent (either object) of quiet observations.')
for lab, pc in (('point estimate', n_calls / n_years), ('upper Poisson bound', hi_c)):
    lo = pc * 0.009; hi = pc * 0.065
    P(f'      route hazard, {lab}: {lo * 100:.3f}% to {hi * 100:.3f}% a year - one false episode every {1 / hi:,.0f} to {1 / lo:,.0f} years;')
    P(f'         over a 6.5-year expansion {(1 - (1 - hi) ** 6.5) * 100:.2f}% to {(1 - (1 - lo) ** 6.5) * 100:.2f}%; over ten years '
      f'{(1 - (1 - hi) ** 10) * 100:.2f}% to {(1 - (1 - lo) ** 10) * 100:.2f}%.')
P('    For comparison the Paper 2 chat\'s v7.2, whose channels fire singly rather than in conjunction, carries 3.5 per cent')
P('    a year (one in 29). The conjunction is worth one to two orders of magnitude, and it is the reason this route')
P('    refuses fast single objects (memo 8o, 8r) however much speed they buy.')
P('\n(d) MISS. Thirteen of thirteen detected since 1948; by the rule of three the per-recession miss rate is at most')
P('    3/13 = 23 per cent at 95 per cent confidence, and the Clopper-Pearson lower bound on detection is 79 per cent;')
P('    the leave-one-out folds of the vacancy form (memo 8l) detect the held-out recession in every fold. The route\'s')
P('    exposure, as the Paper 2 chat found for its own rule, is lateness rather than blindness: the three walls.')
log.close()
