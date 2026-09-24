import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
def full():
    t=[]
    for c in ALL: t+=run_country_concept(c,**K)
    s=score(t,'',show=False); return (s['hp'],s['ht'])
res=[]
for i in range(3):
    res.append(full())
    # force cache churn: drop and reload every panel, run a decoy pass in between
    for c in ALL: bench._cache.pop(c,None)
    bench.SKIP=bench.SKIP|{'retail volume'}
    for c in ALL: run_country_concept(c,**K)
    bench.SKIP=bench.SKIP-{'retail volume'}
    for c in ALL: bench._cache.pop(c,None)
    import gc; gc.collect()
print('three passes with cache churn between them:',res)
print('deterministic' if len(set(res))==1 else 'NOT DETERMINISTIC')
