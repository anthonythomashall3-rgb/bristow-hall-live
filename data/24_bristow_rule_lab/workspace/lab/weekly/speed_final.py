"""The real-time weekly caller, final record, with no look-ahead of any kind.

The seasonal factors are re-estimated each December from the data available then and
applied unchanged for the following year, so the first five years of the file are a
warm-up in which the factors are estimated on too little history.  The record is reported
from 1991, the first year with five years of history behind the factors.
"""
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
SA=pd.read_csv('/home/claude/lab/dol/US_state_claims_sa_rt.csv',index_col=0,parse_dates=True)
NC=pd.read_csv('/home/claude/lab/weekly/US_nat_claims_rt.csv',index_col=0,parse_dates=True)
PK=['1990-07','2001-03','2007-12','2020-02']; TR=['1991-03','2001-11','2009-06','2020-04']
def mo(t): return pd.Timestamp(t.year,t.month,1)
def md(x,y): return (x.year-y.year)*12+(x.month-y.month)
exec(open('/home/claude/lab/weekly/final_caller.py').read()
     .split("def peak_calls")[1].join(["def peak_calls",""]).split("def sc(")[0])
def breadth(sm,L,thsq):
    K=SA.rolling(sm).mean()*100.0
    S=K-K.rolling(L,min_periods=L//2).min()
    return ((S>=thsq).sum(axis=1)/S.notna().sum(axis=1)*100.0).dropna()
def nat(nsm):
    N=(np.log(NC['initial claims'])*100.0).rolling(nsm).mean()
    return pd.concat([N.rename('n'),(N-N.rolling(52,min_periods=26).min()).rename('g')],
                     axis=1,sort=True).dropna()
P=peak_calls(breadth(13,104,25.),50.,2,52,'first_above')
T=trough_calls(nat(8),6,10.,40.,13)
print(f'{"end":7s} {"published":10s} {"dated":8s} {"official":9s} {"lag":>4s} {"error":>6s}')
def rep(calls,tgt,label,cut='1991-01'):
    hits=0; n=0; fa=0
    for pub,dt in calls:
        if pub<pd.Timestamp(cut): continue
        near=min(tgt,key=lambda k: abs(md(dt,pd.Timestamp(k+'-01'))))
        lag=md(mo(pub),pd.Timestamp(near+'-01')); err=md(dt,pd.Timestamp(near+'-01'))
        ok=abs(lag)<=2 and abs(err)<=2
        print(f'{label:7s} {pub:%Y-%m}    {dt:%Y-%m}  {near}   {lag:+4d} {err:+6d}   {"HIT" if ok else "false"}')
        if ok: hits+=1
        else: fa+=1
    return hits,fa
hp,fp=rep(P,PK,'peak'); ht,ft=rep(T,TR,'trough')
tgtP=[k for k in PK if pd.Timestamp(k+'-01')>=pd.Timestamp('1991-01')]
tgtT=[k for k in TR if pd.Timestamp(k+'-01')>=pd.Timestamp('1991-01')]
print()
print(f'From 1991: peaks {hp}/{len(tgtP)} within two months on both lag and error, {fp} false;'
      f'  troughs {ht}/{len(tgtT)}, {ft} false')
