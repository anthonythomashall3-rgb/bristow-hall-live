import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np
bench.SKIP={'exports','imports','car registrations','unemployment'}; bench.ABSTAIN=True
vals=[]
for bt in [0.01,0.02,0.03,0.05]:
 for bp in [0.01,0.02,0.03,0.05]:
  for cap in [9,12,18,24]:
   r=[]
   for c in CLASSICAL: r+=run_country2(c,min_depth=0.0,n=3,band_t=bt,band_p=bp,peak_cap=cap)
   s=score(r,'',show=False); vals.append(s['hp']+s['ht'])
print(f'restricted grid (smoothing 3 months, bands 1-5%, cap 9-24 months), {len(vals)} settings:')
print(f'   min {min(vals)}  median {int(np.median(vals))}  max {max(vals)} of 96')
CFG=dict(min_depth=0.0,n=3,L=12,band_t=0.03,band_p=0.02,peak_cap=12)
print()
tot=[]
for c in CLASSICAL:
    r=run_country2(c,**CFG); tot+=r; score(r,'   '+c)
score(tot,'CLASSICAL, band_t=0.03')
print()
for r in tot:
    if r['nch'] and not (r['hp'] and r['ht']):
        print(f"  MISS {r['country']:24s} {str(r['peak_off']):9s} {str(r['tr_off']):9s} nch={r['nch']} ep={str(r['ep']):>4s} et={str(r['et']):>4s}")
print()
A=[];B=[]
for c in CLASSICAL: A+=run_country2(c,**CFG); B+=run_country_bb(c)
score(A,'   Bristow Rule   (classical)'); score(B,'   Bry-Boschan    (classical)')
A=[];B=[]
for c in ALL: A+=run_country2(c,**CFG); B+=run_country_bb(c)
score(A,'   Bristow Rule   (all nine)'); score(B,'   Bry-Boschan    (all nine)')
