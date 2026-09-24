import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np
bench.SKIP={'exports','imports','car registrations','unemployment'}; bench.ABSTAIN=True
CFG=dict(min_depth=0.0,n=3,L=12,band_t=0.02,band_p=0.02,peak_cap=12)
print('--- architecture, classical sample')
A=[];B=[];D=[]
for c in CLASSICAL:
    A+=run_country2(c,**CFG)
    B+=run_country_ci(c,band_t=0.02,band_p=0.02,n=3,peak_cap=12)
    D+=run_country4(c,band_t=0.02,band_p=0.02,n=3,peak_cap=12)
score(A,'A median of channel dates'); score(B,'B date a composite index'); score(D,'D date the median panel')
print()
print('--- parameter sweep range, classical sample')
tot=[]
for n in [3,4,5]:
 for bt in [0.005,0.01,0.02,0.03,0.05]:
  for bp in [0.005,0.01,0.02,0.03,0.05]:
   for cap in [6,9,12,18,24]:
    r=[]
    for c in CLASSICAL: r+=run_country2(c,min_depth=0.0,n=n,band_t=bt,band_p=bp,peak_cap=cap)
    s=score(r,'',show=False); tot.append(s['hp']+s['ht'])
print(f'   {len(tot)} settings: min {min(tot)}  median {int(np.median(tot))}  max {max(tot)} of 96')
print()
print('--- standalone, classical sample')
allr=[]; nx=0; xs=[]
for c in CLASSICAL:
    det=standalone(c,thr=1.5,q=0.5,gap=12,band_t=0.02,band_p=0.02)
    det=[d for d in det if d['depth'] is not None and d['depth']<=-2.0]
    rows,extra=match(c,det,window=18); allr+=rows; nx+=len(extra); xs+=[(c,d) for d in extra]
n=len(allr)
print(f'   found {sum(1 for r in allr if r["found"])}/{n}   peak {sum(r["hp"] for r in allr)}/{n}   trough {sum(r["ht"] for r in allr)}/{n}   outside the chronology {nx}')
md_in=[d['depth'] for c,d in [] ]
ext=[d['depth'] for c,d in xs]
print(f'   outside episodes median depth {np.median(ext):.1f}%   French among them {sum(1 for c,d in xs if c=="France")}')
