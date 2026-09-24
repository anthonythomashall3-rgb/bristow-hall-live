"""Within-N accuracy, monthly and quarterly chronologies reported separately."""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
tot=[]
for c in ALL: tot+=run_country_concept(c,**K)
MQ=[c for c in ALL if PANELS[c]['freq']=='M']
mo=[r for r in tot if r['country'] in MQ]
qu=[r for r in tot if r['country'] not in MQ]
def rep(rows,unit,scale):
    ep=[abs(r['ep'])*scale for r in rows if r['ep'] is not None]
    et=[abs(r['et'])*scale for r in rows if r['et'] is not None]
    print(f'  n={len(rows)} dated {len(ep)}/{len(et)}   mean |e| {np.mean(ep):.2f}/{np.mean(et):.2f} {unit}')
    for k in (0,1,2,3):
        print(f'    within {k} {unit}: peaks {sum(1 for x in ep if x<=k)}/{len(ep)}'
              f'  troughs {sum(1 for x in et if x<=k)}/{len(et)}')
print('MONTHLY chronologies (US, US interwar, Canada, Japan, Korea, Brazil)')
rep(mo,'months',1)
print('QUARTERLY chronologies (Euro area, Spain, France)')
rep(qu,'quarters',1)
print('QUARTERLY expressed in months (1 quarter = 3 months)')
rep(qu,'months',3)
ep=[abs(r['ep'])*(1 if r['country'] in MQ else 3) for r in tot if r['ep'] is not None]
et=[abs(r['et'])*(1 if r['country'] in MQ else 3) for r in tot if r['et'] is not None]
print(f'ALL 83, quarterly counted as 3 months each: mean |e| {np.mean(ep):.2f}/{np.mean(et):.2f}')
for k in (0,1,2,3):
    print(f'    within {k} months: peaks {sum(1 for x in ep if x<=k)}/{len(ep)}  troughs {sum(1 for x in et if x<=k)}/{len(et)}')
