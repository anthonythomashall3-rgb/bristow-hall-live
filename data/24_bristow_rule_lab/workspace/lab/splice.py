"""Splice the euro-area aggregate onto the OECD euro-area series.

Where the OECD publishes a euro-area index the OECD series is used; before it
begins the member-state aggregate is chained on at the first overlapping month,
so the level is continuous and no month is counted twice.
"""
import os, sys, numpy as np, pandas as pd
KEI='/home/claude/lab/kei'
def load(p):
    d=pd.read_csv(p); d.columns=['d','v']
    d['d']=pd.to_datetime(d.d); d['v']=pd.to_numeric(d.v,errors='coerce')
    return d.dropna().set_index('d')['v'].astype(float).sort_index()
for f in ['PRVM_BTE','PRVM_C','PRVM_F','TOVM_G47','TOCAPA_G45','EX__T','IM__T']:
    a=f'{KEI}/EA20_{f}.csv'; b=f'{KEI}/EAAGG_{f}.csv'
    if not os.path.exists(b): continue
    agg=load(b)
    if os.path.exists(a):
        oe=load(a); j=oe.index.min()
        if j<=agg.index.max() and j>agg.index.min():
            k=float(oe[j])/float(agg[j])
            out=pd.concat([agg[:j][:-1]*k, oe])
        else:
            out=oe
    else:
        out=agg
    fn=f'{KEI}/EAX_{f}.csv'
    with open(fn,'w') as g:
        g.write('date,value\n')
        for d,v in out.items(): g.write(f'{d.strftime("%Y-%m-%d")},{v:.4f}\n')
    print(f'EAX {f}: {out.index.min():%Y-%m} .. {out.index.max():%Y-%m}  n={len(out)}')
