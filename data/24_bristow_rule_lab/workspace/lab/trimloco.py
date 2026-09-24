import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
from w2 import w2
import collections
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
orig=bench.med_fallback
def num(d): return d.year*12+(d.month-1)
def mk(k):
    def mf(a,b):
        d=orig(a,b)
        if d is None or k is None: return d
        ds=[x for x in a if x is not None] or [x for x in b if x is not None]
        if len(ds)<4: return d
        c=num(d); keep=[x for x in ds if abs(num(x)-c)<=k]
        if len(keep)<2: return d
        return med(keep)
    return mf
CAND=[None,36,30,24,21,18,15,12]
res={}
for k in CAND:
    bench.med_fallback=mk(k)
    t=[]
    for c in ALL: t+=run_country_concept(c,**K)
    res[k]=t
bench.med_fallback=orig
def sc(rows,c):
    r=[x for x in rows if x['country']==c and not (x['pk'] is None and x['tr'] is None)]
    return (sum(1 for x in r if x['ep'] is not None and abs(x['ep'])<=2)
           +sum(1 for x in r if x['et'] is not None and abs(x['et'])<=2))
oos=0;n=0;picks=collections.Counter()
for c in ALL:
    best=max(CAND,key=lambda k: (sum(sc(res[k],o) for o in ALL if o!=c),
                                 sum(x['hp']+x['ht'] for x in res[k] if x['country']!=c)))
    picks[best]+=1; oos+=sc(res[best],c)
    n+=2*len([x for x in res[best] if x['country']==c and not (x['pk'] is None and x['tr'] is None)])
for k in CAND:
    a,na,b,nb,ma_,mb,sa,sb=w2(res[k]); s=score(res[k],'',show=False)
    print(f'trim {str(k):>5s}  within2 {a}+{b}={a+b}  hits {s["hp"]}/{s["ht"]}  MAE {ma_:.2f}/{mb:.2f}')
print(f'leave-one-chronology-out within two: {oos}/{n}')
print('chosen by the other eight:',dict(picks))
