import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np
bench.SKIP={'exports','imports','car registrations','unemployment'}; bench.ABSTAIN=True
best=[]
for n in [3,4,5]:
 for bt in [0.005,0.01,0.02,0.03,0.05]:
  for bp in [0.005,0.01,0.02,0.03,0.05]:
   for cap in [6,9,12,18,24]:
    r=[]
    for c in CLASSICAL: r+=run_country2(c,min_depth=0.0,n=n,band_t=bt,band_p=bp,peak_cap=cap)
    s=score(r,'',show=False); best.append((s['hp']+s['ht'],-(s['mp']+s['mt']),n,bt,bp,cap,s))
best.sort(reverse=True)
for b in best[:12]:
    s=b[6]; print(f'n={b[2]} bt={b[3]} bp={b[4]} cap={b[5]:2d}  peak {s["hp"]}/{s["n"]} MAD {s["mp"]:.2f}  trough {s["ht"]}/{s["n"]} MAD {s["mt"]:.2f}  sum={b[0]}')
# matched vs outside depth
mat=[]; ext=[]
for c in CLASSICAL:
    det=standalone(c,thr=1.5,q=0.5,gap=12,band_t=0.02,band_p=0.02)
    det=[d for d in det if d['depth'] is not None and d['depth']<=-2.0]
    rows,extra=match(c,det,window=18)
    ids={id(d) for d in extra}
    ext+=[d['depth'] for d in extra]
    mat+=[d['depth'] for d in det if id(d) not in ids]
print(f'\nstandalone: matched n={len(mat)} median depth {np.median(mat):.1f}% ; outside n={len(ext)} median depth {np.median(ext):.1f}%')
