import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
bench.SKIP={'exports','imports','construction production','car registrations','manufacturing production'}
best=[]
for qt in [0.3,0.4,0.5,0.6,0.7,0.8]:
 for qp in [0.2,0.3,0.4,0.5,0.6,0.7]:
  for bp in [0.02,0.03,0.05]:
   tot=[]
   for c in CLASSICAL: tot+=run_country2(c,min_depth=0.0,n=3,band_t=0.01,band_p=bp,peak_cap=12,qt=qt,qp=qp)
   s=score(tot,'',show=False)
   best.append((s['hp']+s['ht'],-(s['mp']+s['mt']),qt,qp,bp,s))
best.sort(reverse=True)
for b in best[:14]:
    s=b[5]
    print(f'qt={b[2]} qp={b[3]} bp={b[4]}  peak {s["hp"]}/{s["n"]} MAD {s["mp"]:.2f}  trough {s["ht"]}/{s["n"]} MAD {s["mt"]:.2f}  sum={b[0]}')
