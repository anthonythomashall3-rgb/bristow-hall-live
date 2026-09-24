import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
from w2 import w2
import pandas as pd, collections
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
_orig=bench.dev
def mk(hs):
    cache={}
    def dev2(x,L=12,n=3):
        k=(id(x),n,tuple(hs)); e=cache.get(k)
        if e is not None and e[0] is x: return e[1]
        m=bench.ma(x,n); parts=[]
        for h in hs:
            mx=m.shift(1).rolling(h).max(); parts.append((mx-m)/mx*100.0)
        r=pd.concat(parts,axis=1).mean(axis=1); cache[k]=(x,r); return r
    return dev2
CAND=[(12,),(11,12,13),(10,12,14),(9,12,15),(8,12,16),(6,12,18),(12,15,18)]
res={}
for hs in CAND:
    bench.dev=mk(hs) if len(hs)>1 else _orig
    t=[]
    for c in ALL: t+=run_country_concept(c,**K)
    res[hs]=t
bench.dev=_orig
def sc(rows,c):
    r=[x for x in rows if x['country']==c and not (x['pk'] is None and x['tr'] is None)]
    return (sum(1 for x in r if x['ep'] is not None and abs(x['ep'])<=2)
           +sum(1 for x in r if x['et'] is not None and abs(x['et'])<=2))
oos=0;n=0;picks=collections.Counter()
for c in ALL:
    best=max(CAND,key=lambda k: sum(sc(res[k],o) for o in ALL if o!=c))
    picks[best]+=1; oos+=sc(res[best],c)
    n+=2*len([x for x in res[best] if x['country']==c and not (x['pk'] is None and x['tr'] is None)])
for hs in CAND:
    a,na,b,nb,ma_,mb,sa,sb=w2(res[hs]); s=score(res[hs],'',show=False)
    print(f'{str(hs):22s} within2 {a}+{b}={a+b}  hits {s["hp"]}/{s["ht"]}  MAE {ma_:.2f}/{mb:.2f}')
print(f'leave-one-chronology-out within two: {oos}/{n}')
print('chosen by the other eight:',dict(picks))
