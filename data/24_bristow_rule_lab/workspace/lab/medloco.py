import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.)
def make(kind):
    def med2(dates,q=0.5):
        ds=sorted(d for d in dates if d is not None)
        if not ds: return None
        n=len(ds)
        if n%2==1: return ds[n//2]
        return ds[n//2-1] if kind=='lower' else ds[n//2]
    return med2
KINDS=['lower','upper']
res={}
for kind in KINDS:
    bench.med=make(kind)
    rows=[]
    for c in ALL: rows+=run_country_concept(c,**K)
    res[kind]=rows
# leave-one-chronology-out: pick the convention on the other eight, score the ninth
oos_p=oos_t=n=0; picks={}
for c in ALL:
    best=max(KINDS,key=lambda k: sum(r['hp']+r['ht'] for r in res[k] if r['country']!=c))
    picks[c]=best
    mine=[r for r in res[best] if r['country']==c]
    oos_p+=sum(r['hp'] for r in mine); oos_t+=sum(r['ht'] for r in mine); n+=len(mine)
print('in sample:', {k:(sum(r['hp'] for r in res[k]),sum(r['ht'] for r in res[k])) for k in KINDS})
print(f'leave-one-chronology-out: peak {oos_p}/{n}  trough {oos_t}/{n}')
print('convention chosen by the other eight:', picks)
