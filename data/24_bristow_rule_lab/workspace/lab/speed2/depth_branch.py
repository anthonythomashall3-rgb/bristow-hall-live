"""The speed hunt, part two: the claims objects' own DEPTH as the fast branch (3 September 2026, night).

Everything that excludes 1967 also excludes 2023-24 - except the unemployment rate, which is slow.
So the rule can have two branches: (i) a claims reading so deep that no disturbance ever reached it
calls at once, no rate needed; (ii) the ordinary claims line AND Sahm's 0.5 catches what is left
(2023-24).  This script measures branch (i)'s material: for the national conjunct (the smaller of the
year-over-year log changes in initial and continued claims - weekly from 1968 on the Department's
file, monthly 1948 on on the Fieldhouse field) and for the state breadth index (leg A, 36/8), the
maximum inside each of the sixteen claims episodes and the first day each higher line is reached,
in days after the committee's peak month.  The line is set by the disturbances' maxima (1951, 1952,
1967) - the negatives - and the speed at it is read on the twelve.  Output depth_branch.log.
"""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0, '/home/claude'); sys.path.insert(0, '/home/claude/lab/weekly'); sys.path.insert(0, '/home/claude/lab/fh')
import numpy as np, pandas as pd, bristow_rule_v3 as B
import v8_legs as V, legs_1948 as L, union_peaks as U

EP = [('1948-11', '1949-10', 'recession'), ('1951-07', '1952-07', 'DISTURBANCE'), ('1952-03', '1952-12', 'DISTURBANCE'), ('1953-07', '1954-05', 'recession'),
      ('1957-08', '1958-04', 'recession'), ('1960-04', '1961-02', 'recession'), ('1967-02', '1968-02', 'DISTURBANCE'), ('1969-12', '1970-11', 'recession'),
      ('1973-11', '1975-03', 'recession'), ('1980-01', '1980-07', 'recession'), ('1981-07', '1982-11', 'recession'), ('1990-07', '1991-03', 'recession'),
      ('2001-03', '2001-11', 'recession'), ('2007-12', '2009-06', 'recession'), ('2020-02', '2020-04', 'recession'), ('2023-07', '2026-02', '2023-24')]
M = lambda s: pd.Timestamp(s + '-01')
def month_end(t): return t + pd.offsets.MonthEnd(0)

# weekly conjunct, Department's file (1967 on), published 7 days after the week
cw = B.claims_conjunct(V.D.ic_nsa.dropna(), V.D.cc_nsa.dropna())
# monthly conjunct on the field, 1948 on (legs_1948: weekly averages per month), published the 10th of the month after
ic, cc = L.national_nsa()
cm = B.claims_conjunct(ic, cc, weeks=12, smooth=1) if False else None
def monthly_conjunct():
    li = np.log(ic); lc = np.log(cc)
    c = pd.concat([li - li.shift(12), lc - lc.shift(12)], axis=1).min(axis=1)
    return c.dropna()
cm = monthly_conjunct()
# state breadth index, leg A (Fieldhouse field 36/8, two-month mean), published the 20th of the month after
P = pd.read_csv('/home/claude/lab/fh/FH_state_claims_sa_rt_log.csv', index_col=0, parse_dates=True)
A = B.claims_diffusion(P.rolling(2).mean().dropna(how='all'), 36., 8)
# the Department's monthly index 48/13 (1971 on)
PAN = pd.read_csv('/home/claude/lab/dol/US_state_monthly_4ch_sa.csv', index_col=0, parse_dates=True)
cols = [c for c in PAN.columns if c.endswith('| initial claims') or c.endswith('| continued weeks claimed')]
AD = B.claims_diffusion(PAN[cols], 48., 13)

def first_cross(s, line, a, b, pub):
    seg = s[M(a) - pd.DateOffset(months=3): M(b)]
    hit = seg[seg >= line]
    return None if hit.empty else pub(hit.index[0])
pub_w = lambda t: t + pd.Timedelta(days=7)
pub_m10 = lambda t: pd.Timestamp(t.year, t.month, 1) + pd.DateOffset(months=1) + pd.Timedelta(days=9)
pub_m20 = lambda t: pd.Timestamp(t.year, t.month, 1) + pd.DateOffset(months=1) + pd.Timedelta(days=19)

print('maxima inside each episode [peak-3m, trough]')
print('episode      kind          weekly conjunct  monthly conjunct  breadth A (FH 36/8)  breadth Dept (48/13)')
for a, b, k in EP:
    w0, w1 = M(a) - pd.DateOffset(months=3), M(b)
    def mx(s): seg = s[w0:w1].dropna(); return None if seg.empty else float(seg.max())
    f = lambda v, p=2: f'{v:8.{p}f}' if v is not None else '       -'
    print(f'{a}      {k:12s}  {f(mx(cw))}         {f(mx(cm))}          {f(mx(A), 0)}              {f(mx(AD), 0)}')

print('\nfirst reach of each line, days after the peak month (weekly conjunct published 7 days after the week; monthly conjunct the 10th, breadth the 20th of the month after)')
for name, s, pub in (('weekly conjunct', cw, pub_w), ('monthly conjunct', cm, pub_m10), ('breadth A', A, pub_m20), ('breadth Dept', AD, pub_m20)):
    lines = (0.20, 0.25, 0.30, 0.35, 0.40, 0.50) if 'conjunct' in name else (50, 60, 70, 80, 90)
    print(f'\n{name}')
    for line in lines:
        row = []
        for a, b, k in EP:
            t = first_cross(s, line, a, b, pub)
            row.append(f'{a[:4]}:{"   -" if t is None else f"{(t - month_end(M(a))).days:+4d}"}')
        print(f'  {line:>5}: ' + ' '.join(row))
