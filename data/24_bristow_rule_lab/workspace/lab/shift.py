"""A trailing n-month mean is centered at t-(n-1)/2.  The month at which the smoothed
series turns is therefore (n-1)/2 months later than the month the underlying series turns.
Test: report the corrected month."""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np, pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
tot=[]
for c in ALL: tot+=run_country_concept(c,**K)
MQ=[c for c in ALL if PANELS[c]['freq']=='M']
for sh in (0,-1,-2):
    hp=ht=0; ep=[]; et=[]; mep=[]; met=[]; uep=[]; uet=[]
    for r in tot:
        fq='Q' if isinstance(r['peak_off'],tuple) else 'M'
        s = sh if fq=='M' else 0
        pk = r['pk']+pd.DateOffset(months=s) if r['pk'] is not None else None
        tr = r['tr']+pd.DateOffset(months=s) if r['tr'] is not None else None
        a,e1=hit(pk,r['peak_off'],fq); b,e2=hit(tr,r['tr_off'],fq)
        hp+=a; ht+=b
        if e1 is not None: ep.append(abs(e1))
        if e2 is not None: et.append(abs(e2))
        if fq=='M':
            if e1 is not None: mep.append(abs(e1))
            if e2 is not None: met.append(abs(e2))
        if r['country'].startswith('United States'):
            if e1 is not None: uep.append(abs(e1))
            if e2 is not None: uet.append(abs(e2))
    print(f'shift {sh:+d} months:  peak {hp}/83 trough {ht}/83   monthly MAD '
          f'{np.mean(mep):.2f}/{np.mean(met):.2f}  monthly w2 {sum(1 for x in mep if x<=2)},'
          f'{sum(1 for x in met if x<=2)} of {len(mep)}   US w2 {sum(1 for x in uep if x<=2)},'
          f'{sum(1 for x in uet if x<=2)} of {len(uep)}')
