"""Alternatives to the deviation statistic.

D(t) = [max of the previous twelve months - m(t)] / that max, in percent.  Tested
against: distance below a trailing MEAN rather than a trailing max; distance below
the trailing max in logs; the year-on-year growth rate; the month-on-month change;
and the level standardised by its own trailing standard deviation.
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
def mk(kind):
    cache={}
    def dev2(x,L=12,n=3):
        k=(id(x),L,n,kind); e=cache.get(k)
        if e is not None and e[0] is x: return e[1]
        m=bench.ma(x,n)
        if kind=='max':      r=(m.shift(1).rolling(L).max()-m)/m.shift(1).rolling(L).max()*100.0
        elif kind=='mean':   r=(m.shift(1).rolling(L).mean()-m)/m.shift(1).rolling(L).mean()*100.0
        elif kind=='median': r=(m.shift(1).rolling(L).median()-m)/m.shift(1).rolling(L).median()*100.0
        elif kind=='logmax':
            mx=m.shift(1).rolling(L).max(); r=(np.log(mx)-np.log(m))*100.0
        elif kind=='yoy':    r=-(m/m.shift(12)-1.0)*100.0
        elif kind=='mom':    r=-(m/m.shift(1)-1.0)*100.0
        elif kind=='zscore':
            sd=m.diff().rolling(60,min_periods=24).std()
            r=(m.shift(1).rolling(L).max()-m)/sd
        elif kind=='max24':  r=(m.shift(1).rolling(24).max()-m)/m.shift(1).rolling(24).max()*100.0
        elif kind=='maxexp': r=(m.expanding().max().shift(1)-m)/m.expanding().max().shift(1)*100.0
        else: raise ValueError(kind)
        cache[k]=(x,r); return r
    return dev2
for kind in ('max','mean','median','logmax','yoy','mom','zscore','max24','maxexp'):
    bench.dev=mk(kind)
    tot=[]
    try:
        for c in ALL: tot+=run_country_concept(c,**K)
    except Exception as e:
        print(f'{kind:8s} ERR {str(e)[:60]}'); bench.dev=_orig; continue
    a,na,b,nb,ma_,mb,sa,sb=w2(tot); s=score(tot,'',show=False)
    print(f'{kind:8s} within2 {a}+{b}={a+b}  hits {s["hp"]}/{s["ht"]}  MAE {ma_:.2f}/{mb:.2f}  bias {sa:+.2f}/{sb:+.2f}')
bench.dev=_orig
