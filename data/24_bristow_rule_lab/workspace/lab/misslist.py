import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
tot=[]
for c in ALL: tot+=run_country_concept(c,**K)
print('PEAK MISSES')
for r in tot:
    if not r['hp']: print(f"  {r['country']:26s} {r['peak_off']}  err {r['ep']}")
print('TROUGH MISSES')
for r in tot:
    if not r['ht']: print(f"  {r['country']:26s} {r['tr_off']}  err {r['et']}")
