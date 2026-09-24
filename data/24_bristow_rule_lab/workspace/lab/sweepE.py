import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
bench.SKIP={'exports','imports','car registrations'}
best=[]
for ab in [True,False]:
 for n in [3,4]:
  for bt in [0.01,0.02,0.03]:
   for bp in [0.01,0.02,0.03,0.05]:
    for cap in [9,12,18,24]:
     bench.ABSTAIN=ab; tot=[]
     for c in CLASSICAL: tot+=run_country2(c,min_depth=0.0,n=n,band_t=bt,band_p=bp,peak_cap=cap)
     s=score(tot,'',show=False)
     best.append((s['hp']+s['ht'],-(s['mp']+s['mt']),ab,n,bt,bp,cap,s))
best.sort(reverse=True)
for b in best[:14]:
    s=b[7]
    print(f'abstain={str(b[2]):5s} n={b[3]} bt={b[4]} bp={b[5]} cap={b[6]:2d}  peak {s["hp"]}/{s["n"]} MAD {s["mp"]:.2f}  trough {s["ht"]}/{s["n"]} MAD {s["mt"]:.2f}  sum={b[0]}')
