# q30.py - STATE SAHM BREADTH on the first prints of the state unemployment rates (BLS LAUS releases 1994-2026, the
# harvest's state_ur_first_prints_refmonth_fixed.csv, one row per state per release): for each state the three-month
# mean of the first-print rate above its twelve-month low (the hub's object, per state), the share of states at the
# hub's line 0.3667 (the rule's numbers, no new one), against the breadth line 0.60. Reported: every month the share
# stood at 0.60 with its release day, inside or outside a recession window; the shares of 2023-24 and 2001, 2007-08, 2020.
# Run: PYTHONPATH=. python3 s2/q30.py
import os,sys
import pandas as pd, numpy as np
H=os.path.expanduser('~/Projects/Onset Detector Data/bristow-hall-harvest/data/bls_laus/state_ur_first_prints_refmonth_fixed.csv')
d=pd.read_csv(H); d=d[(d.geo_level=='state')&(d.series_id=='state_ur')]
d['obs_period']=pd.to_datetime(d['obs_period']); d['vintage_date']=pd.to_datetime(d['vintage_date'])
d=d.sort_values(['geo_code','obs_period','vintage_date']).drop_duplicates(['geo_code','obs_period'],keep='first')   # the first print of each month
W=d.pivot(index='obs_period',columns='geo_code',values='value').sort_index(); REL=d.groupby('obs_period')['vintage_date'].max()
print('states',W.shape[1],'months',W.index.min().date(),'..',W.index.max().date(),'| first release',REL.min().date())
m3=W.rolling(3,min_periods=3).mean(); low=m3.rolling(12,min_periods=12).min().shift(1); gap=(m3-low)
LINE=0.3667; share=((gap>=LINE-1e-9).sum(axis=1)/gap.notna().sum(axis=1)).where(gap.notna().sum(axis=1)>=40)
PK=['1948-11-01','1953-07-01','1957-08-01','1960-04-01','1969-12-01','1973-11-01','1980-01-01','1981-07-01','1990-07-01','2001-03-01','2007-12-01','2020-02-01','2024-04-01']
TR=['1949-10-01','1954-05-01','1958-04-01','1961-02-01','1970-11-01','1975-03-01','1980-07-01','1982-11-01','1991-03-01','2001-11-01','2009-06-01','2020-04-01','2024-09-01']
PKm=[pd.Timestamp(x) for x in PK]; TRm=[pd.Timestamp(x) for x in TR]
def in_rec(t): return any(PKm[i]-pd.DateOffset(months=6)<=pd.Timestamp(t.year,t.month,1)<=TRm[i] for i in range(len(PKm)))
at=share[share>=0.60-1e-9]
print('months with the share at 0.60:',[(m.strftime('%Y-%m'),round(float(v),2),REL[m].date().isoformat(),'in' if in_rec(m) else 'OUTSIDE') for m,v in at.items()])
for a,b in (('2000-09-01','2001-06-01'),('2007-06-01','2008-06-01'),('2019-12-01','2020-05-01'),('2023-06-01','2024-09-01')):
    s=share[(share.index>=a)&(share.index<=b)]; print(a[:7],'..',b[:7],{m.strftime('%Y-%m'):(round(float(v),2),REL[m].date().isoformat()) for m,v in s.items()})
# the national hub for comparison: the month the rule's X fired is known; here the share at lower breadth lines for information only
for L in (0.5,0.4,0.3):
    a2=share[share>=L-1e-9]; eps=[]; last=None
    for m in a2.index:
        if last is None or (m-last).days>200: eps.append(m)
        last=m
    print(f'  (information) share >= {L}: episodes {[(m.strftime("%Y-%m"),"in" if in_rec(m) else "OUT") for m in eps]}')
