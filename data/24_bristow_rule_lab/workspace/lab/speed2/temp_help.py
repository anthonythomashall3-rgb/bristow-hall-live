"""Temporary-help employment as a labor-demand object (3 September 2026, night, fourth pass) - tried, not adopted.
CES temporary help services (1990 on, first Friday of the month after): the k-month mean of the log level below its
maximum over the previous `back` months; recession maxima, the highest reading outside recession windows, the line
half a log point above it, crossings at that line; JOLTS-style first prints from ALFRED (2011 on).  Output temp_help.log."""
import sys; sys.path.insert(0,'/home/claude/lab/slack'); sys.path.insert(0,'/home/claude/lab/rt')
import pandas as pd, numpy as np, alfred
from objects import fred
from bound import M, months
th=fred('/home/claude/lab/cps/03_payroll_employment/monthly/TEMPHELPS.csv'); lt=np.log(th)*100
print('TEMPORARY HELP SERVICES employment (CES, 1990 on; published the first Friday of the month after): the k-month mean of the log level below its maximum over the previous `back` months, in log points x100')
EPS=[('1990-07','1991-03'),('2001-03','2001-11'),('2007-12','2009-06'),('2020-02','2020-04')]; E24=('2023-06','2025-06')
PK=['1990-07','2001-03','2007-12','2020-02']; TR=['1991-03','2001-11','2009-06','2020-04']
def form(k,back):
    m=lt.rolling(k).mean(); return (m.shift(1).rolling(back).max()-m).dropna()
print('form     max inside each recession [peak-3m, trough]      2023-24 max   highest reading outside the windows (month, value)   crossings at that line + 0.5: recessions (months after peak) | 2023-24')
for k in (1,2,3):
    for back in (6,12):
        g=form(k,back)
        mx=[float(g[M(a)-pd.DateOffset(months=3):M(b)].max()) for a,b in EPS]; m24=float(g[M(E24[0])-pd.DateOffset(months=3):M(E24[1])].max())
        outs=g[[not (any(M(p)-pd.DateOffset(months=9)<=t<=M(q)+pd.DateOffset(months=6) for p,q in zip(PK,TR)) or (M('2022-06')<=t<=M('2026-06'))) for t in g.index]]
        hi=outs.max(); line=round(float(hi)+0.5,1)
        lags=[]
        for a,b in EPS:
            seg=g[M(a)-pd.DateOffset(months=3):M(b)]; h=seg[seg>=line]; lags.append(None if h.empty else months(h.index[0],M(a)))
        seg=g[M(E24[0])-pd.DateOffset(months=3):M(E24[1])]; h=seg[seg>=line]; t24='never' if h.empty else h.index[0].strftime('%Y-%m')
        print(f'({k},{back:2d})    {["%.1f"%x for x in mx]}    {m24:5.1f}       {outs.idxmax():%Y-%m} {hi:5.1f}        line {line:4.1f}: ' + ' '.join(f'{l:>3d}' if l is not None else '  -' for l in lags) + f' | {t24}')
print('\nthe object in 2007-08 (log points below the 6-month max, 2-month mean):', form(2,6)['2007-06':'2008-06'].round(1).tolist())
print('first prints (ALFRED TEMPHELPS vintages from 2011): the as-of (2,6) reading around 2019-2020 and 2022-2024')
vints=alfred.vintages('TEMPHELPS'); rows=[]
for vd in vints:
    s=alfred.asof('TEMPHELPS',vd)
    if s is None: continue
    l=np.log(s)*100; m=l.rolling(2).mean(); gap=(m.shift(1).rolling(6).max()-m).dropna()
    rows.append((vd,gap.index[-1],round(float(gap.iloc[-1]),1)))
df=pd.DataFrame(rows,columns=['vintage','month','gap']).set_index('vintage')
print(df['2019-06':'2020-06'].to_string()); print(df['2022-06':'2024-03'].gap.round(1).tolist())
print('as-of maximum before March 2020:', df[:'2020-02-28'].gap.max(), df[:'2020-02-28'].gap.idxmax().date())
