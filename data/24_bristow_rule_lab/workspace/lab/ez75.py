import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
for c in ('Euro area','Spain'):
    print('===',c, PANELS[c]['chrono'])
    for r in run_country_concept(c,**K):
        print(f"   {str(r['peak_off']):10s}/{str(r['tr_off']):10s} pk={r['pk'].date() if r['pk'] is not None else None} "
              f"tr={r['tr'].date() if r['tr'] is not None else None} ep={r['ep']} et={r['et']} n={r['nch']} {r['verdict']}")
