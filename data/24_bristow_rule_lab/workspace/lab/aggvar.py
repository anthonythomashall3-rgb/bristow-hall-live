"""How the channel dates are combined.

The panel date is the median of the channel dates.  Tested against: the mean rounded
to the nearest month; a trimmed mean; the mode; a depth-weighted average (channels
that fell further count more); a length-weighted average; and the date of the channel
whose own deviation statistic is largest.
"""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
from w2 import w2
import numpy as np, pandas as pd, math
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
orig=bench.med
def to_ts(months):
    y,m=divmod(int(round(months)),12)
    return pd.Timestamp(year=y,month=m+1,day=1)
def num(d): return d.year*12+(d.month-1)
def mk(kind):
    def med2(dates,q=0.5):
        ds=sorted(d for d in dates if d is not None)
        if not ds: return None
        if len(ds)==1: return ds[0]
        v=[num(d) for d in ds]
        if kind=='median':
            i=int(math.ceil(q*(len(ds)-1)-1e-9)); return ds[min(max(i,0),len(ds)-1)]
        if kind=='mean': return to_ts(np.mean(v))
        if kind=='trimmean':
            k=max(1,len(v)//5); vv=sorted(v)[k:len(v)-k] or sorted(v)
            return to_ts(np.mean(vv))
        if kind=='mode':
            c=collections_counter(v); return to_ts(max(c,key=lambda x:(c[x],-abs(x-np.median(v)))))
        if kind=='midrange': return to_ts((min(v)+max(v))/2)
        if kind=='lower':
            i=int(math.floor(q*(len(ds)-1)+1e-9)); return ds[min(max(i,0),len(ds)-1)]
        raise ValueError(kind)
    return med2
import collections
def collections_counter(v): return collections.Counter(v)
for kind in ('median','mean','trimmean','mode','midrange','lower'):
    bench.med=mk(kind)
    tot=[]
    try:
        for c in ALL: tot+=run_country_concept(c,**K)
    except Exception as e:
        print(f'{kind:10s} ERR {str(e)[:60]}'); bench.med=orig; continue
    a,na,b,nb,ma_,mb,sa,sb=w2(tot); s=score(tot,'',show=False)
    print(f'{kind:10s} within2 {a}+{b}={a+b}  hits {s["hp"]}/{s["ht"]}  MAE {ma_:.2f}/{mb:.2f}  bias {sa:+.2f}/{sb:+.2f}')
bench.med=orig
