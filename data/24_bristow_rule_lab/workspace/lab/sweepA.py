import sys, time; sys.path.insert(0,'/home/claude/lab')
from bench import *
t0=time.time(); best=[]
for n in [3,4,5]:
 for bt in [0.005,0.01,0.02,0.03,0.05]:
  for bp in [0.005,0.01,0.02,0.03,0.05]:
   for cap in [6,9,12,18,24]:
    tot=[]
    for c in CLASSICAL: tot+=run_country2(c,min_depth=0.0,n=n,band_t=bt,band_p=bp,peak_cap=cap)
    s=score(tot,'',show=False)
    best.append((s['hp']+s['ht'], -(s['mp']+s['mt']), n,bt,bp,cap, s))
best.sort(reverse=True)
for b in best[:15]:
    s=b[6]
    print(f'n={b[2]} bt={b[3]:.3f} bp={b[4]:.3f} cap={b[5]:2d}  peak {s["hp"]}/{s["n"]} MAD {s["mp"]:.2f}  trough {s["ht"]}/{s["n"]} MAD {s["mt"]:.2f}  sum={b[0]}')
print('elapsed %.0fs'%(time.time()-t0))
