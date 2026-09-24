import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
for c in ('United States','United States (interwar)'):
    print('===',c)
    for r in run_country_concept(c,**K):
        f=lambda d: d.strftime('%Y-%m') if d is not None else '--'
        m1='' if abs(r['ep'])<=2 else '   <-- outside 2'
        m2='' if abs(r['et'])<=2 else '   <-- outside 2'
        print(f"  {r['peak_off']} pred {f(r['pk'])} err {r['ep']:+d}{m1}")
        print(f"  {r['tr_off']} pred {f(r['tr'])} err {r['et']:+d}{m2}")
