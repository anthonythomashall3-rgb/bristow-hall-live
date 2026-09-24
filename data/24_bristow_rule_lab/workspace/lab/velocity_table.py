"""Velocity: how fast the activity panel deepens after each of the route's peak calls (3 September 2026).

Anthony's question: was the June 2023 call early because 2023-24 was a slow burn - a broad deterioration
with very low velocity?  Measured here on today's data: for each peak call the American route makes
(union_peaks.log: the twelve committee peaks and the three other calls of 1951, 1967 and 2023), the
panel's composite D - the median across the seven shipped channels of the drawdown of the three-month
mean from its trailing twelve-month maximum, in per cent - is read from the month the call carried (or
the call month) forward: its value 3, 6, 9, 12 and 18 months on, the first month it reaches the 2.0 line
that opens the level clause's peak search, and its maximum inside 24 months; beside it the deepest single
channel's D and the share of the seven channels whose own D reaches 2.0 inside 24 months.  Velocity is
the composite D per month over the first six months.  The question the table answers is whether the
twelve and the three separate on depth or on speed, and by how much.  Output velocity_table.log.  A
measurement; nothing chosen on it.
"""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab'); sys.argv=['x']
import numpy as np, pandas as pd, bristow_rule_v3 as B, bench
from bench import PANELS, channels
bench.SKIP={'exports','imports','car registrations','unemployment','construction production','construction output','capital goods production','intermediate goods production','consumer durables production'}
chs=[(nm,s) for nm,s in channels('United States') if nm not in bench.SKIP]
CALLS=[('1948-12-10','1948-11','NBER 1948-11'),('1951-09-20','1951-07','other call'),('1953-09-20','1953-07','NBER 1953-07'),
       ('1957-08-20','1957-06','NBER 1957-08'),('1960-02-20','1959-12','NBER 1960-04'),('1967-04-20','1967-02','other call'),
       ('1970-01-31','1969-12','NBER 1969-12'),('1974-02-16','1973-12','NBER 1973-11'),('1980-03-20','1980-01','NBER 1980-01'),
       ('1981-12-20','1981-10','NBER 1981-07'),('1990-09-20','1990-07','NBER 1990-07'),('2001-03-31','2001-02','NBER 2001-03'),
       ('2007-12-28','2007-12','NBER 2007-12'),('2020-03-28','2020-02','NBER 2020-02'),('2023-08-28','2023-07','other call (Paper 1: Apr-Aug 2024)')]
def mo(s): return pd.Timestamp(s+'-01')
D=B._panel_frame(chs,lambda s: B.deviation(s,12,3))
comp=D.median(axis=1)
print('call date     dated    what                      comp D at +3   +6   +9  +12  +18  | first month >= 2.0 (months from date)  max D (24 mo)  deepest channel (24 mo)   channels >= 2.0  velocity (D per month, first 6)')
rows=[]
for call,dated,what in CALLS:
    d0=mo(dated); seg=comp[d0:d0+pd.DateOffset(months=24)]
    vals=[float(comp.get(d0+pd.DateOffset(months=k),np.nan)) for k in (3,6,9,12,18)]
    first=next((t for t,v in seg.items() if v>=2.0),None)
    mx=float(seg.max()); mxm=seg.idxmax()
    Dseg=D[d0:d0+pd.DateOffset(months=24)]
    deep=Dseg.max(); deepest=deep.idxmax(); share=int((deep>=2.0).sum()); n=int(deep.notna().sum())
    vel=(vals[1]-float(comp.get(d0,np.nan)))/6.0
    rows.append((what,vals,first,mx,share,vel))
    print(f"{call}   {dated}  {what:38s} "+' '.join(f'{v:5.2f}' for v in vals)+f"  | {'never' if first is None else f'{first:%Y-%m} (+{(first.year-d0.year)*12+first.month-d0.month})':16s}  {mx:5.2f} at {mxm:%Y-%m}   {deep.max():5.2f} {deepest[:22]:22s}  {share}/{n}   {vel:+.2f}")
nb=[r for r in rows if r[0].startswith('NBER')]; ot=[r for r in rows if not r[0].startswith('NBER')]
print(f"\nthe twelve committee peaks: composite D reaches 2.0 in {sum(1 for r in nb if r[2] is not None)} of 12, at +{min((r[2].year*12+r[2].month) for r in nb if r[2] is not None) - 0 if False else ''}"
      f"; months to the line {[None if r[2] is None else (r[2].year*12+r[2].month)-(mo(c[1]).year*12+mo(c[1]).month) for r,c in zip(nb,[x for x in CALLS if x[2].startswith('NBER')])]}")
print(f"  max composite D within 24 months: min {min(r[3] for r in nb):.2f}, median {np.median([r[3] for r in nb]):.2f}; channels at 2.0: min {min(r[4] for r in nb)} of 7; velocity min {min(r[5] for r in nb):+.2f}, median {np.median([r[5] for r in nb]):+.2f}")
print(f"the three other calls (1951, 1967, 2023): max composite D {[round(r[3],2) for r in ot]}; channels at 2.0 {[r[4] for r in ot]}; velocity {[round(r[5],2) for r in ot]}; line reached {[r[2] is not None for r in ot]}")
