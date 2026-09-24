"""Does the weekly caller find the recession Paper 1 says was missed?

Paper 1's dual object, from the program's own documents:
  the national labour-market recession   March 2024 - August 2024
  the rolling state-mass episode         June 2023 - May 2026 (E-last, Maryland the anchor)
Neither is in the NBER's chronology; the committee has announced nothing since 2021-07-19.
"""
import sys; sys.path.insert(0,'/home/claude')
import bristow_rule_v3 as B, pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
SA=pd.read_csv('/home/claude/lab/dol/US_state_claims_sa_rt.csv',index_col=0,parse_dates=True)
NC=pd.read_csv('/home/claude/lab/weekly/US_nat_claims_rt.csv',index_col=0,parse_dates=True)
def md(x,y): return (x.year-y.year)*12+(x.month-y.month)
def mo(t): return pd.Timestamp(t.year,t.month,1)
Bd=B.state_breadth(SA,13,104,25.0)
P=B.weekly_peak_calls(Bd,50.,2,52)
T=B.weekly_trough_calls(np.log(NC['initial claims']),8,6,10.,40.,13)
TARG={'peak':{'1990-07':'NBER','2001-03':'NBER','2007-12':'NBER','2020-02':'NBER',
              '2023-06':'Paper 1, rolling episode onset','2024-03':'Paper 1, national labour-market recession'},
      'trough':{'1991-03':'NBER','2001-11':'NBER','2009-06':'NBER','2020-04':'NBER',
                '2024-08':'Paper 1, national labour-market recession end',
                '2026-05':'Paper 1, rolling episode end'}}
for kind,calls in (('peak',P),('trough',T)):
    print(f'--- {kind} calls')
    for pub,dt in calls:
        if pub<pd.Timestamp('1991-01-01'): continue
        near=min(TARG[kind],key=lambda k: abs(md(dt,pd.Timestamp(k+'-01'))))
        lag=md(mo(pub),pd.Timestamp(near+'-01')); err=md(dt,pd.Timestamp(near+'-01'))
        ok='HIT ' if abs(lag)<=2 and abs(err)<=2 else 'miss'
        print(f'  {ok} pub {pub:%Y-%m} dated {dt:%Y-%m}  vs {near} ({TARG[kind][near]})  lag {lag:+3d} err {err:+3d}')
print()
print('targets never called:')
for kind,calls in (('peak',P),('trough',T)):
    got=set()
    for pub,dt in calls:
        if pub<pd.Timestamp('1991-01-01'): continue
        for k in TARG[kind]:
            if abs(md(dt,pd.Timestamp(k+'-01')))<=2 and abs(md(mo(pub),pd.Timestamp(k+'-01')))<=2: got.add(k)
    for k in TARG[kind]:
        if k not in got and pd.Timestamp(k+'-01')>=pd.Timestamp('1991-01-01'):
            print(f'  {kind:7s} {k}  ({TARG[kind][k]})')
