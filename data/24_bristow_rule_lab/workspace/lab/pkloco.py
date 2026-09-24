import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
from w2 import w2
import collections
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
CAND=[('last',0.01,18),('last',0.02,18),('mid',0.01,18),('mid',0.01,24),('mid',0.02,18)]
res={}
for wp,bp,cap in CAND:
    bench.PLATEAU_P=wp
    tot=[]
    for c in ALL: tot+=run_country_concept(c,band_t=0.12,band_p=bp,peak_cap=cap,n=3,L=12,
                                           min_depth=5.0,lam=500000.)
    res[(wp,bp,cap)]=tot
bench.PLATEAU_P='last'
def sc(rows,c):
    r=[x for x in rows if x['country']==c and not (x['pk'] is None and x['tr'] is None)]
    return (sum(1 for x in r if x['ep'] is not None and abs(x['ep'])<=2)
           +sum(1 for x in r if x['et'] is not None and abs(x['et'])<=2))
oos=0;n=0;picks=collections.Counter()
for c in ALL:
    best=max(CAND,key=lambda k: sum(sc(res[k],o) for o in ALL if o!=c))
    picks[best]+=1; oos+=sc(res[best],c)
    n+=2*len([x for x in res[best] if x['country']==c and not (x['pk'] is None and x['tr'] is None)])
for k in CAND:
    a,na,b,nb,ma_,mb,sa,sb=w2(res[k]); s=score(res[k],'',show=False)
    print(f'{str(k):22s} within2 {a}+{b}={a+b}  hits {s["hp"]}/{s["ht"]}  MAE {ma_:.2f}/{mb:.2f}')
print(f'leave-one-chronology-out within two: {oos}/{n}')
print('chosen by the other eight:',dict(picks))
