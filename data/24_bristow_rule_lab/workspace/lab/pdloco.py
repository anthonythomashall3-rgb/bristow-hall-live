"""Leave one chronology out on the channel-level peak-depth abstention."""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np, collections
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
_orig=bench.ch_peak
F=[0.0]
def ch_peak_f(level,w0,w1,band=0.02,n=3,tadj=False,win=120,minp=60,abstain=None,where=None):
    _ab=bench.ABSTAIN if abstain is None else abstain
    if _ab and F[0]>0:
        lv=bench.prep(level,n,tadj,win,minp)
        m=bench.ma(lv,n)[w0:w1].dropna()
        if len(m)>=4:
            hi=float(m.max()); i=m.idxmax()
            lo=float(m[i:].min()) if len(m[i:]) else float(m.min())
            if hi>0 and (hi-lo)/hi*100.0 < F[0]: return None
    return _orig(level,w0,w1,band,n,tadj,win,minp,abstain,where)
bench.ch_peak=ch_peak_f
CAND=[0.0,0.5,1.0,1.5,2.0,3.0]
res={}
for f in CAND:
    F[0]=f; bench._DEV.clear()
    t=[]
    for c in ALL: t+=run_country_concept(c,**K)
    res[f]=t
def sc(rows,c):
    r=[x for x in rows if x['country']==c]
    return sum(x['hp']+x['ht'] for x in r)
def w2(rows,c):
    r=[x for x in rows if x['country']==c]
    return (sum(1 for x in r if x['ep'] is not None and abs(x['ep'])<=2)
           +sum(1 for x in r if x['et'] is not None and abs(x['et'])<=2))
picks=collections.Counter(); oos=0; oos_w2=0
for c in ALL:
    best=max(CAND,key=lambda k:(sum(sc(res[k],o) for o in ALL if o!=c),
                                sum(w2(res[k],o) for o in ALL if o!=c), -k))
    picks[best]+=1; oos+=sc(res[best],c); oos_w2+=w2(res[best],c)
    print(f'  hold out {c:26s} folds pick f={best}   held-out hits {sc(res[best],c)}')
print('picks:',dict(picks))
print(f'out of sample total {oos} endpoints; shipped f=0 gives {sum(sc(res[0.0],c) for c in ALL)}; '
      f'f=1.0 in sample {sum(sc(res[1.0],c) for c in ALL)}')

print()
print('per chronology, f=0.0 -> f=1.0  (hits, then within-2 endpoints)')
for c in ALL:
    print(f'  {c:26s} {sc(res[0.0],c):2d} -> {sc(res[1.0],c):2d}    w2 {w2(res[0.0],c):2d} -> {w2(res[1.0],c):2d}')
print()
print('episodes whose peak error changes:')
for a,b in zip(res[0.0],res[1.0]):
    if a['ep']!=b['ep']:
        print(f"   {a['country']:24s} {str(a['peak_off']):10s} {a['ep']} -> {b['ep']}")
