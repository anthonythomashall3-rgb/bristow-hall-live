import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import math
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.)
orig=bench.med
def mk(q0):
    def med2(dates,q=None):
        ds=sorted(d for d in dates if d is not None)
        if not ds: return None
        if len(ds)==1: return ds[0]
        qq=q0 if q is None else q
        i=int(math.ceil(qq*(len(ds)-1)-1e-9))
        return ds[min(max(i,0),len(ds)-1)]
    return med2
QS=[0.3,0.4,0.5,0.6,0.7]
res={}
for q0 in QS:
    bench.med=mk(q0)
    rows=[]
    for c in ALL: rows+=run_country_concept(c,**K)
    res[q0]=rows
    s=score(rows,'',show=False)
    print(f'q={q0}  peak {s["hp"]}/80 trough {s["ht"]}/80',flush=True)
bench.med=orig
oos_p=oos_t=n=0; picks={}
for c in ALL:
    best=max(QS,key=lambda q: sum(r['hp']+r['ht'] for r in res[q] if r['country']!=c))
    picks[c]=best
    mine=[r for r in res[best] if r['country']==c]
    oos_p+=sum(r['hp'] for r in mine); oos_t+=sum(r['ht'] for r in mine); n+=len(mine)
print(f'leave-one-chronology-out: peak {oos_p}/{n} trough {oos_t}/{n}')
print('q chosen by the other eight:',picks)
