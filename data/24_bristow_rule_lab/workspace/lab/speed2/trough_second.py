"""A labor-market second condition at the ENDS, tried (3 September 2026, night, fourth pass): the vacancy rate's
rise above its previous-`back`-month minimum and the unemployment rate's fall below its previous-`back`-month
maximum, at each committee trough and through the May-September 1970 pause.  Output trough_second.log."""
import sys; sys.path.insert(0,'/home/claude/lab/slack'); import pandas as pd, numpy as np
from objects import load
from bound import M, months
v=-load()['-vacancy rate']; u=load()['UR']
TR=['1949-10','1954-05','1958-04','1961-02','1970-11','1975-03','1980-07','1982-11','1991-03','2001-11','2009-06','2020-04','2026-02']
print("A SECOND CONDITION FOR THE ENDS: the vacancy rate's RISE (k-month mean above its minimum over the previous `back` months) and the unemployment rate's FALL (k-month mean below its previous-`back`-month maximum), at each committee trough and in the 1970 pause (May-August 1970)")
def rise(s,k,back): m=s.rolling(k).mean(); return (m-m.shift(1).rolling(back).min()).dropna()
def fall(s,k,back): m=s.rolling(k).mean(); return (m.shift(1).rolling(back).max()-m).dropna()
for name,g in (('vacancy rise (2,6)',rise(v,2,6)),('vacancy rise (3,12)',rise(v,3,12)),('UR fall (2,6)',fall(u,2,6)),('UR fall (3,12)',fall(u,3,12))):
    row=[]
    for t in TR:
        seg=g[M(t)-pd.DateOffset(months=2):M(t)+pd.DateOffset(months=12)]
        first={line:(None if seg[seg>=line].empty else months(seg[seg>=line].index[0],M(t))) for line in (0.1,0.2,0.3)}
        row.append(f"{t[:7]}: {' '.join(f'{k}:{(v if v is not None else chr(45)):>3}' for k,v in first.items())}")
    pause=g['1970-05':'1970-09']
    print(f'\n{name}: first month at 0.1 / 0.2 / 0.3, months after the trough')
    for r in row: print('   ', r)
    print(f'    the 1970 pause, May-Sep 1970 readings: {pause.round(2).tolist()}')
