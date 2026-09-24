import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
bench.SKIP={'exports','imports','car registrations','unemployment'}; bench.ABSTAIN=True
base=dict(lam=500000.)
print(f'{"mode":10s} {"cap":>4s}  {"peak":>9s} {"trough":>9s}  sum')
for mode in ['median','tightest','level','growth','diffusion']:
    for cap in [9,12]:
        tot=[]
        for c in ALL: tot+=run_country_ens(c,mode=mode,peak_cap=cap,**base)
        s=score(tot,'',show=False)
        print(f'{mode:10s} {cap:4d}  {s["hp"]:4d}/{s["n"]:<4d} {s["ht"]:4d}/{s["n"]:<4d}  {s["hp"]+s["ht"]}')
# concept routing with cap 9 for reference
for cap in [9,12]:
    tot=[]
    for c in ALL: tot+=run_country_concept(c,min_depth=5.0,lam=500000.,peak_cap=cap)
    s=score(tot,'',show=False)
    print(f'{"concept":10s} {cap:4d}  {s["hp"]:4d}/{s["n"]:<4d} {s["ht"]:4d}/{s["n"]:<4d}  {s["hp"]+s["ht"]}')
