"""Every headline number in the memo, recomputed in one pass, at the shipped config."""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
tot=[]
for c in ALL: tot+=run_country_concept(c,**K)
s=score(tot,'',show=False)
lv=[r for r in tot if CONCEPT[r['country']]=='level']; sl=score(lv,'',show=False)
have=[r for r in tot if not (r['pk'] is None and r['tr'] is None)]
ep=[abs(r['ep']) for r in have if r['ep'] is not None]
et=[abs(r['et']) for r in have if r['et'] is not None]
print(f'ALL      {s["n"]} contractions  peak {s["hp"]} ({100*s["hp"]/s["n"]:.0f}%) MAD {s["mp"]:.2f}   trough {s["ht"]} ({100*s["ht"]/s["n"]:.0f}%) MAD {s["mt"]:.2f}')
print(f'LEVEL    {sl["n"]} contractions  peak {sl["hp"]} ({100*sl["hp"]/sl["n"]:.0f}%)   trough {sl["ht"]} ({100*sl["ht"]/sl["n"]:.0f}%)')
print(f'undated  {sum(1 for r in tot if r["pk"] is None or r["tr"] is None)} of {s["n"]}')
print(f'within2  peaks {sum(1 for x in ep if x<=2)}/{len(ep)}  troughs {sum(1 for x in et if x<=2)}/{len(et)}')
print(f'within3  peaks {sum(1 for x in ep if x<=3)}/{len(ep)}  troughs {sum(1 for x in et if x<=3)}/{len(et)}')
print(f'exact    peaks {sum(1 for x in ep if x==0)}/{len(ep)}  troughs {sum(1 for x in et if x==0)}/{len(et)}')
print(f'mean|e|  peaks {np.mean(ep):.2f}  troughs {np.mean(et):.2f}')
for c in ALL:
    x=score([r for r in tot if r['country']==c],'',show=False)
    print(f'   {c:26s} {x["n"]:2d}  {x["hp"]:2d}/{x["n"]:<2d} MAD {x["mp"]:.1f}   {x["ht"]:2d}/{x["n"]:<2d} MAD {x["mt"]:.1f}')
