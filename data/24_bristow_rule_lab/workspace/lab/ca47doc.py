"""How much of the 1947-48 Canadian contraction is in the series C.D. Howe names?"""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd
ch=dict(channels('Canada'))
g=pd.read_csv('/home/claude/lab/statcan/CA_gdp_q_long.csv',index_col=0,parse_dates=True)['v']
for _e in PANELS['Canada']['chrono']:
    pk_off,tr_off,freq=ep3(_e,'M')
    pkm=ts(pk_off); trm=ts(tr_off)
    w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
    core=None;nm=None
    for k in ('monthly GDP','industrial production'):
        s=ch.get(k)
        if s is not None and s.index.min()<=w0 and s.index.max()>=trm: core,nm=s,k; break
    m=ma(core,3)[w0:w1].dropna()
    dd=(m.cummax()-m)/m.cummax()*100
    gq=g[w0:w1]
    gdd=((gq.cummax()-gq)/gq.cummax()*100).max() if len(gq)>4 else float('nan')
    print(f"{pk_off}/{tr_off}  {nm:22s} monthly max drawdown in window {dd.max():5.2f}%   "
          f"quarterly real GDP {gdd:5.2f}%")
