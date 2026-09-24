"""The two-tier American verdict - MEASURED 3 September 2026 and WITHDRAWN from the route the same day (Anthony: one call, one date).  Kept as the listing of the route's fifteen episodes with the measured confirmation reading beside each.

3 September 2026.  The route's peak calls (union_peaks.py: legs A, B, C, M; the tool's union_calls,
365-day episodes, no chronology) are read with the tool's confirm_episodes against two confirmers:

  E   the breadth of states whose payroll employment is falling (payroll_breadth_calls on the
      Fieldhouse field's state payrolls, amplitude 0.75, minimum phase 6, three-month mean - chosen
      leave-one-peak-out, every fold the same; 12 of 12 postwar peaks, no other call 1949-2024)
  D2  two channels of the shipped seven-channel panel at a drawdown of 2.0 per cent or more (today's
      data; the panel's month is in hand by the 15th of the month after) - 12 of 12, and alone it
      fires once outside a recession window, December 1959, four months before the April 1960 peak

Horizon eighteen months.  Every episode of the record is printed with its call, its date, and its
verdict; the three episodes the committee did not date (1951, 1967, 2023) are the ones the confirmers
leave unconfirmed.  Caveats stated where they belong: the state payrolls are today's vintage with
real-time factors (the harvest holds a state payroll vintage archive for a first-print replay, not
yet run), and D2 is on today's panel.  Output american_verdict.log.
"""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab'); sys.path.insert(0,'/home/claude/lab/weekly'); sys.path.insert(0,'/home/claude/lab/fh')
import numpy as np, pandas as pd, bristow_rule_v3 as B
import union_peaks as U, legs_1948 as L48, bench
from bench import channels
bench.SKIP={'exports','imports','car registrations','unemployment','construction production','construction output','capital goods production','intermediate goods production','consumer durables production'}
legs={'A':U.leg_A(),'B':U.leg_B(0.20),'C':U.leg_C(),'M':L48.leg_M(0.20)}
eps=B.union_calls(legs,date_order=('A','C'))
P=pd.read_csv('/home/claude/lab/fh/FH_state_payrolls_nsa.csv',index_col=0,parse_dates=True)
E=B.payroll_breadth_calls(P)
chs=[(nm,s) for nm,s in channels('United States') if nm not in bench.SKIP]
D=B._panel_frame(chs,lambda s:B.deviation(s,12,3)); D=D[D.index>=pd.Timestamp('1948-01-01')]
two=((D>=2.0).sum(axis=1)>=2)
D2=[]; on=False
for t,v in two.items():
    if v and not on: D2.append((pd.Timestamp(t.year,t.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=14),t)); on=True
    elif not v: on=False
ASOF=pd.Timestamp('2026-09-03')
eps=B.confirm_episodes(eps,{'E payroll breadth':E,'D2 two channels at 2%':D2},horizon_months=18,asof=ASOF)
NBER={'1948-11','1953-07','1957-08','1960-04','1969-12','1973-11','1980-01','1981-07','1990-07','2001-03','2007-12','2020-02'}
def near(d):
    for m in NBER:
        t=pd.Timestamp(m+'-01')
        if abs((d-t).days)<=200: return m
    return None
print('call published   leg  date at call  final date   committee peak   verdict       confirmed by             on            days after call')
for ep in eps:
    if ep['published']<pd.Timestamp('1948-06-01'): continue
    c=near(ep['published'])
    print(f"{ep['published']:%Y-%m-%d}       {ep['leg']}    {ep['date_at_call'].strftime('%Y-%m') if ep['date_at_call'] is not None else 'pending':10s}    {ep['date'].strftime('%Y-%m') if ep['date'] is not None else '-':8s}     {c or 'none':10s}       {ep['verdict']:11s}   {ep['confirmed_by'] or '-':24s} {ep['confirmed_on'].strftime('%Y-%m-%d') if ep['confirmed_on'] is not None else '-':12s}  {ep['confirm_days'] if ep['confirm_days'] is not None else '-'}")
rec=[ep for ep in eps if ep['published']>=pd.Timestamp('1948-06-01')]
conf=[ep for ep in rec if ep['verdict']=='confirmed']; unc=[ep for ep in rec if ep['verdict']!='confirmed']
print(f"\nepisodes {len(rec)}: confirmed {len(conf)} (all twelve committee recessions: {all(near(ep['published']) for ep in conf)}), unconfirmed {len(unc)} {[ep['published'].strftime('%Y-%m') for ep in unc]}")
print(f"confirmation days after the call, median {np.median([ep['confirm_days'] for ep in conf]):.0f}, range {min(ep['confirm_days'] for ep in conf)} to {max(ep['confirm_days'] for ep in conf)}; by leg {dict(pd.Series([ep['confirmed_by'] for ep in conf]).value_counts())}")
print('E calls:',[(p.strftime('%Y-%m-%d'),d.strftime('%Y-%m')) for p,d in E])
print('D2 firings 1948 on:',[(p.strftime('%Y-%m-%d'),d.strftime('%Y-%m')) for p,d in D2])
