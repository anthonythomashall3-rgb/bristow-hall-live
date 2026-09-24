import sys, time; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
bench.SKIP={'exports','imports','construction production','car registrations','manufacturing production'}
best=[]
for n in [3,4,5]:
 for bt in [0.01,0.02,0.03,0.05]:
  for bp in [0.01,0.02,0.03,0.05,0.08,0.12]:
   for cap in [12,18,24,36,None]:
    for lead in [12,18,24]:
     tot=[]
     for c in CLASSICAL: tot+=run_country2(c,min_depth=0.0,n=n,band_t=bt,band_p=bp,peak_cap=cap,lead=lead)
     s=score(tot,'',show=False)
     best.append((s["hp"]+s["ht"],-(s["mp"]+s["mt"]),n,bt,bp,999 if cap is None else cap,lead,s))
best.sort(reverse=True)
for b in best[:15]:
    s=b[7]
    print(f'n={b[2]} bt={b[3]} bp={b[4]} cap={b[5]} lead={b[6]}  peak {s["hp"]}/{s["n"]} MAD {s["mp"]:.2f}  trough {s["ht"]}/{s["n"]} MAD {s["mt"]:.2f}  sum={b[0]}')
