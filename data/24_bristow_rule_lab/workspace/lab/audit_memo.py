"""Every headline number in the memo, recomputed in one pass."""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_p=0.01,peak_cap=18)
tot=[]
for c in ALL: tot+=run_country_concept(c,**K)
s=score(tot,'',show=False)
print(f'ALL           {s["n"]} contractions   peak {s["hp"]} ({100*s["hp"]/s["n"]:.0f}%)  trough {s["ht"]} ({100*s["ht"]/s["n"]:.0f}%)')
lv=[r for r in tot if CONCEPT[r['country']]=='level']; sl=score(lv,'',show=False)
print(f'LEVEL         {sl["n"]} contractions   peak {sl["hp"]} ({100*sl["hp"]/sl["n"]:.0f}%)  trough {sl["ht"]} ({100*sl["ht"]/sl["n"]:.0f}%)')
nod=sum(1 for r in tot if r['pk'] is None or r['tr'] is None)
print(f'undated       {nod} of {s["n"]}')
for c in ALL:
    x=score([r for r in tot if r['country']==c],'',show=False)
    print(f'   {c:26s} {x["n"]:2d}  {x["hp"]:2d}/{x["n"]:<2d} MAD {x["mp"]:.1f}   {x["ht"]:2d}/{x["n"]:<2d} MAD {x["mt"]:.1f}')
