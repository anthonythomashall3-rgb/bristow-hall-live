"""A breadth trough object on the Fieldhouse state field, tried against the 1970 pause (3 September 2026, night,
fourth pass): the share of states whose k-month mean of log claims stands x log points below its maximum over the
previous `back` months.  Pauses are broad: the shares inside recessions before the trough month run as high as at
the troughs (1961, 1975, 1982).  Not adopted.  Output trough_breadth_states.log."""
import sys, warnings; warnings.filterwarnings('ignore'); sys.path.insert(0,'/home/claude')
import numpy as np, pandas as pd, bristow_rule_v3 as B
P=pd.read_csv('/home/claude/lab/fh/FH_state_claims_sa_rt_log.csv',index_col=0,parse_dates=True)
ic=P[[c for c in P.columns if c.endswith('| initial claims')]]*100; cc=P[[c for c in P.columns if c.endswith('| continued weeks claimed')]]*100
TR=['1949-10','1954-05','1958-04','1961-02','1970-11','1975-03','1980-07','1982-11','1991-03','2001-11','2009-06','2020-04']
PK=['1948-11','1953-07','1957-08','1960-04','1969-12','1973-11','1980-01','1981-07','1990-07','2001-03','2007-12','2020-02']
M=lambda s: pd.Timestamp(s+'-01')
def md(a,b): return (a.year-b.year)*12+a.month-b.month
print('A BREADTH TROUGH OBJECT on the Fieldhouse state field (1947-2024): share of states whose k-month mean of log claims stands x log points BELOW its maximum over the previous `back` months (claims falling from their high = activity past its trough)')
for name,X in (('initial claims',ic),('continued claims',cc)):
    for k,back,x in ((2,6,5),(2,6,10),(2,12,10),(3,12,10),(2,6,15)):
        m=X.rolling(k).mean(); g=m.shift(1).rolling(back).max()-m
        sh=((g>=x).sum(axis=1)/g.notna().sum(axis=1)*100).dropna()
        pause=sh['1970-05':'1970-09'].max()
        rows=[]
        for p,t in zip(PK,TR):
            seg=sh[M(t)-pd.DateOffset(months=2):M(t)+pd.DateOffset(months=12)]
            f50=seg[seg>=50].index.min(); f70=seg[seg>=70].index.min()
            rows.append(f"{t[:4]}:{'-' if pd.isna(f50) else f'{md(f50,M(t)):+d}'}/{'-' if pd.isna(f70) else f'{md(f70,M(t)):+d}'}")
        pre=[]
        for p,t in zip(PK,TR):
            seg=sh[M(p)+pd.DateOffset(months=1):M(t)-pd.DateOffset(months=1)]
            pre.append(int(round(seg.max())) if len(seg) else -1)
        print(f'{name:16s} k={k} back={back} x={x:2d}: first month at 50%/70% after the trough ' + ' '.join(rows) + f' | 1970 pause max {pause:3.0f}% | max share before each trough inside the recession {pre}')
