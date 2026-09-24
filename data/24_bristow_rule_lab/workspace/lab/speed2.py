"""Told that a trough has occurred, how fast can the rule name it?
The clock starts at the month the real-time trigger fires, not at the official trough."""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import trigger as T
import pandas as pd, numpy as np
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.ABSTAIN=True
chs=[(nm,s) for nm,s in channels('United States') if nm not in bench.SKIP]
TR=[ts(t) for p,t in US_M if t>='1969']
print(f'{"NBER trough":12s} {"months of data":>15s} {"date given":>11s} {"error":>6s}')
rows=[]
for t in TR:
    got=None
    for k in range(0,25):
        asof=t+pd.DateOffset(months=k)
        use=[(nm,s[:asof]) for nm,s in chs]
        use=[(nm,s) for nm,s in use if len(s.dropna())>60]
        w0=t-pd.DateOffset(months=36); w1=asof
        r=date_any('United States',use,w0,w1,band_t=0.12,band_p=0.01,n=3,L=12,peak_cap=18,
                   min_depth=5.0,lam=500000.)
        d=r['trough']
        if d is not None and abs(md(d,t))<=2:
            got=(k,d); break
    if got: print(f'{t:%Y-%m}      {got[0]:15d} {got[1]:%Y-%m}      {md(got[1],t):+3d}'); rows.append(got[0])
    else:   print(f'{t:%Y-%m}      {"never within 2":>15s}')
if rows: print(f'mean months of data after the trough before the date is right within two: {np.mean(rows):.1f}')
