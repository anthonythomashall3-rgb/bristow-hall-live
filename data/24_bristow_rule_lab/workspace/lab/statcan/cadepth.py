import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd
ch=dict(channels('Canada'))
g=pd.read_csv('/home/claude/lab/statcan/CA_gdp_q_long.csv',index_col=0,parse_dates=True)['v']
cfg=PANELS['Canada']
for _e in cfg['chrono']:
    pk_off,tr_off,freq=ep3(_e,'M')
    pkm=ts(pk_off); trm=ts(tr_off)
    w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
    core=None;nm=None
    for k in ('monthly GDP','industrial production'):
        s=ch.get(k)
        if s is not None and s.index.min()<=w0 and s.index.max()>=trm: core,nm=s,k; break
    d=dev(core,12,3)[w0:w1].dropna()
    m=ma(core,3)[w0:w1].dropna()
    dd=(m.cummax()-m)/m.cummax()*100
    print(f"{pk_off}/{tr_off}  {nm:22s} maxD={d.max():5.2f}  maxDD={dd.max():5.2f}  gdpQ={'yes' if g.index.min()<=w0 else 'no'}")
