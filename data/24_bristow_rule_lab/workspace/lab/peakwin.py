import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(band_t=0.03,band_p=0.01,peak_cap=18,n=3,L=12,min_depth=5.0,lam=500000.)
# lambda sensitivity on the growth route
for lam in (14400.,129600.,500000.,1e6,2e6):
    t=[]
    for c in ALL: t+=run_country_concept(c,**{**K,'lam':lam})
    s=score(t,'',show=False)
    print(f'lambda={lam:9.0f}  peak {s["hp"]}/83 trough {s["ht"]}/83')
