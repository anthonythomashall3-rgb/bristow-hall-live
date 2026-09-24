import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
for md in (1.0,2.0,3.0,4.0,5.0,6.0,8.0):
    K=dict(min_depth=md,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
    bench._DEV.clear()
    tot=[]
    for c in ALL: tot+=run_country_concept(c,**K)
    s=score(tot,'',show=False)
    ep=[abs(r['ep']) for r in tot if r['ep'] is not None]; et=[abs(r['et']) for r in tot if r['et'] is not None]
    mo=[r for r in tot if PANELS[r['country']]['freq']=='M']
    mep=[abs(r['ep']) for r in mo if r['ep'] is not None]; met=[abs(r['et']) for r in mo if r['et'] is not None]
    print(f'md={md:4.1f}  peak {s["hp"]}/83 trough {s["ht"]}/83  MAD {np.mean(ep):.2f}/{np.mean(et):.2f}'
          f'  monthly-w2 {sum(1 for x in mep if x<=2)},{sum(1 for x in met if x<=2)} of {len(mep)}'
          f'  exact {sum(1 for x in ep if x==0)},{sum(1 for x in et if x==0)}')
