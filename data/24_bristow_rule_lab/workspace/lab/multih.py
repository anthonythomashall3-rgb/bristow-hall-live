"""Several horizons at once.

D uses a single twelve-month lookback.  A turning point that a twelve-month window
sees clearly may be invisible to a six-month one and vice versa, so the natural
generalisation is to combine horizons: the maximum of D over several lookbacks, or
their average.
"""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
from w2 import w2
import numpy as np, pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
_orig=bench.dev
def mk(hs,how):
    cache={}
    def dev2(x,L=12,n=3):
        k=(id(x),L,n,tuple(hs),how); e=cache.get(k)
        if e is not None and e[0] is x: return e[1]
        m=bench.ma(x,n); parts=[]
        for h in hs:
            mx=m.shift(1).rolling(h).max()
            parts.append((mx-m)/mx*100.0)
        D=pd.concat(parts,axis=1)
        r=D.max(axis=1) if how=='max' else D.mean(axis=1)
        cache[k]=(x,r); return r
    return dev2
for hs,how in (((12,),'max'),((11,12,13),'mean'),((10,12,14),'mean'),((9,12,15),'mean'),
               ((8,12,16),'mean'),((6,12,18),'mean'),((9,12,15),'max'),
               ((10,11,12,13,14),'mean'),((9,10,11,12,13,14,15),'mean'),((12,15,18),'mean'),
               ((6,9,12,15,18),'mean')):
    bench.dev=mk(hs,how)
    tot=[]
    for c in ALL: tot+=run_country_concept(c,**K)
    a,na,b,nb,ma_,mb,sa,sb=w2(tot); s=score(tot,'',show=False)
    print(f'horizons {str(hs):16s} {how:4s} within2 {a}+{b}={a+b}  hits {s["hp"]}/{s["ht"]}  MAE {ma_:.2f}/{mb:.2f}')
bench.dev=_orig
