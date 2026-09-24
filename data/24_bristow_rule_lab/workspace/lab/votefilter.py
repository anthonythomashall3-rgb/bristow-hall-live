"""Should every channel get a vote?

Two filters never tried.  A DEPTH filter: a channel that barely moved in the window
carries little information about where the turn was, so it votes only if its own fall
is at least a stated fraction of the deepest channel's.  An OUTLIER filter: channel
dates more than k months from the median are dropped and the median retaken.
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
orig=bench.med_fallback
def num(d): return d.year*12+(d.month-1)
def mk_outlier(k):
    def mf(a,b):
        d=orig(a,b)
        if d is None or k is None: return d
        ds=[x for x in a if x is not None] or [x for x in b if x is not None]
        if len(ds)<4: return d
        c=num(d); keep=[x for x in ds if abs(num(x)-c)<=k]
        if len(keep)<2: return d
        return med(keep)
    return mf
print('--- outlier trim on the channel dates')
for k in (None,24,18,12,9,6):
    bench.med_fallback=mk_outlier(k)
    tot=[]
    for c in ALL: tot+=run_country_concept(c,**K)
    a,na,b,nb,ma_,mb,sa,sb=w2(tot); s=score(tot,'',show=False)
    print(f'   drop dates more than {str(k):>4s} months from the median: within2 {a}+{b}={a+b}  hits {s["hp"]}/{s["ht"]}  MAE {ma_:.2f}/{mb:.2f}')
bench.med_fallback=orig
print('--- depth filter on which channels vote')
import types
src=open('/home/claude/lab/bench.py').read()
import importlib
for frac in (None,0.1,0.25,0.4):
    if frac is None:
        rep=None
    else:
        rep=("    ch_t=[(nm,s) for nm,s in chs if nm not in SKIP_TROUGH] or chs",
             f"""    _dd=[]
    for _n,_s in chs:
        _m=ma(_s,n)[w0:w1].dropna(); _x=maxdd(_m)
        _dd.append((_n,_s,_x if _x is not None else 0.0))
    _deep=min([x for _,_,x in _dd] or [0.0])
    _ok=[(a_,b_) for a_,b_,x in _dd if _deep>=-1e-9 or x<= {frac}*_deep] or chs
    ch_t=[(nm,s) for nm,s in _ok if nm not in SKIP_TROUGH] or _ok""")
    new=src if rep is None else src.replace(rep[0],rep[1],1)
    open('/home/claude/lab/_vf.py','w').write(new)
    import _vf; importlib.reload(_vf)
    _vf.SKIP=bench.SKIP; _vf.SKIP_PEAK=set(); _vf.SKIP_TROUGH=set(); _vf.ABSTAIN=True
    tot=[]
    for c in _vf.ALL: tot+=_vf.run_country_concept(c,**K)
    a,na,b,nb,ma_,mb,sa,sb=w2(tot); s=_vf.score(tot,'',show=False)
    print(f'   a channel votes only if it fell at least {str(frac):>5s} of the deepest: within2 {a}+{b}={a+b}  hits {s["hp"]}/{s["ht"]}  MAE {ma_:.2f}/{mb:.2f}')
