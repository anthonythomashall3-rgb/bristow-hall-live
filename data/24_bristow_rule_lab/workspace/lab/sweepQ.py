import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np
bench.SKIP={'exports','imports','car registrations'}; bench.ABSTAIN=True
QC=['Euro area','Spain','France']
P=[];T=[]
for bt in [0.01,0.02,0.03,0.05,0.08]:
 for bp in [0.01,0.02,0.03,0.05,0.08]:
  for L in [3,4,5,6,8]:
   for cap in [2,3,4,6]:
    Q=[]
    for c in QC: Q+=run_country_q(c,band_t=bt,band_p=bp,L=L,peak_cap=cap)
    s=score(Q,'',show=False); P.append(s['hp']); T.append(s['ht'])
print(f'quarterly rule across the grid ({len(P)} settings), n=17:')
print(f'   peaks   min {min(P)}  median {int(np.median(P))}  max {max(P)}')
print(f'   troughs min {min(T)}  median {int(np.median(T))}  max {max(T)}')
Q=[]
for c in QC: Q+=run_country_q(c,band_t=0.02,band_p=0.02,L=4,peak_cap=4)
score(Q,'   plain setting bt=bp=0.02 L=4Q cap=4Q')
for r in Q:
    if r['nch']: print(f"      {r['country']:12s} {str(r['peak_off']):9s} {str(r['tr_off']):9s} nch={r['nch']} ep={r['ep']:+d} et={r['et']:+d}")
