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
print('|peak error| > 2:')
for r in sorted([r for r in tot if r['ep'] is not None and abs(r['ep'])>2],key=lambda r:-abs(r['ep'])):
    print(f"   {r['country']:26s} {str(r['peak_off']):10s} {r['ep']:+3d}   {r['verdict']}")
print('|trough error| > 2:')
for r in sorted([r for r in tot if r['et'] is not None and abs(r['et'])>2],key=lambda r:-abs(r['et'])):
    print(f"   {r['country']:26s} {str(r['tr_off']):10s} {r['et']:+3d}   {r['verdict']}")
