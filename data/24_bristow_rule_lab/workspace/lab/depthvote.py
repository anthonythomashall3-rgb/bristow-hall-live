"""The depth filter, tested properly and validated out of sample."""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
from w2 import w2
import importlib, collections
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
src=open('/home/claude/lab/bench.py').read()
CAND=[None,0.15,0.3,0.4,0.5,0.6]
res={}
for frac in CAND:
    if frac is None: new=src
    else:
        new=src.replace("    ch_t=[(nm,s) for nm,s in chs if nm not in SKIP_TROUGH] or chs",
f"""    _dd=[]
    for _n,_s in chs:
        _m=ma(_s,n)[w0:w1].dropna(); _x=maxdd(_m)
        _dd.append((_n,_s,_x if _x is not None else 0.0))
    _deep=min([x for _,_,x in _dd] or [0.0])
    _ok=[(a_,b_) for a_,b_,x in _dd if _deep>=-1e-9 or x<= {frac}*_deep] or chs
    ch_t=[(nm,s) for nm,s in _ok if nm not in SKIP_TROUGH] or _ok""",1)
    open('/home/claude/lab/_dv.py','w').write(new)
    import _dv; importlib.reload(_dv)
    _dv.SKIP=bench.SKIP; _dv.SKIP_PEAK=set(); _dv.SKIP_TROUGH=set(); _dv.ABSTAIN=True
    t=[]
    for c in _dv.ALL: t+=_dv.run_country_concept(c,**K)
    res[frac]=t
def sc(rows,c):
    r=[x for x in rows if x['country']==c and not (x['pk'] is None and x['tr'] is None)]
    return (sum(1 for x in r if x['ep'] is not None and abs(x['ep'])<=2)
           +sum(1 for x in r if x['et'] is not None and abs(x['et'])<=2))
oos=0;n=0;picks=collections.Counter()
for c in ALL:
    best=max(CAND,key=lambda k:(sum(sc(res[k],o) for o in ALL if o!=c),
                                sum(x['hp']+x['ht'] for x in res[k] if x['country']!=c)))
    picks[best]+=1; oos+=sc(res[best],c)
    n+=2*len([x for x in res[best] if x['country']==c and not (x['pk'] is None and x['tr'] is None)])
for k in CAND:
    a,na,b,nb,ma_,mb,sa,sb=w2(res[k]); s=score(res[k],'',show=False)
    print(f'depth filter {str(k):>5s}  within2 {a}+{b}={a+b}  hits {s["hp"]}/{s["ht"]}  MAE {ma_:.2f}/{mb:.2f}')
print(f'leave-one-chronology-out within two: {oos}/{n}')
print('chosen by the other eight:',dict(picks))
