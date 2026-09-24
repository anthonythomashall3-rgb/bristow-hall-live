"""Every number quoted in the memo, recomputed at the shipped configuration."""
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
ep=[abs(r['ep']) for r in tot if r['ep'] is not None]; et=[abs(r['et']) for r in tot if r['et'] is not None]
mo=[r for r in tot if PANELS[r['country']]['freq']=='M']
qu=[r for r in tot if PANELS[r['country']]['freq']=='Q']
mep=[abs(r['ep']) for r in mo if r['ep'] is not None]; met=[abs(r['et']) for r in mo if r['et'] is not None]
qep=[abs(r['ep']) for r in qu if r['ep'] is not None]; qet=[abs(r['et']) for r in qu if r['et'] is not None]
print(f'ALL 83   peak {s["hp"]} ({100*s["hp"]/83:.0f}%)  trough {s["ht"]} ({100*s["ht"]/83:.0f}%)')
lv=[r for r in tot if CONCEPT[r['country']]=='level']; sl=score(lv,'',show=False)
print(f'LEVEL {sl["n"]}   peak {sl["hp"]} ({100*sl["hp"]/sl["n"]:.0f}%)  trough {sl["ht"]} ({100*sl["ht"]/sl["n"]:.0f}%)')
print(f'undated  {sum(1 for r in tot if r["pk"] is None or r["tr"] is None)}')
print()
print(f'MONTHLY chronologies: {len(mo)} contractions, {len(mep)} dated')
print(f'   mean |error| peaks {np.mean(mep):.2f} months  troughs {np.mean(met):.2f} months')
for k in (0,1,2,3):
    print(f'   within {k}: peaks {sum(1 for x in mep if x<=k)}/{len(mep)} '
          f'({100*sum(1 for x in mep if x<=k)/len(mep):.0f}%)  troughs {sum(1 for x in met if x<=k)}/{len(met)} '
          f'({100*sum(1 for x in met if x<=k)/len(met):.0f}%)')
print(f'QUARTERLY chronologies: {len(qu)} contractions')
print(f'   mean |error| peaks {np.mean(qep):.2f} quarters  troughs {np.mean(qet):.2f} quarters')
for k in (0,1):
    print(f'   within {k} quarter(s): peaks {sum(1 for x in qep if x<=k)}/{len(qep)}  troughs {sum(1 for x in qet if x<=k)}/{len(qet)}')
print()
for c in ALL:
    x=score([r for r in tot if r['country']==c],'',show=False)
    print(f'   {c:26s} {x["n"]:2d}  peaks {x["hp"]:2d}/{x["n"]:<2d} MAD {x["mp"]:.2f}   troughs {x["ht"]:2d}/{x["n"]:<2d} MAD {x["mt"]:.2f}')
print()
print('signed error means (bias):')
sp=[r['ep'] for r in mo if r['ep'] is not None]; st=[r['et'] for r in mo if r['et'] is not None]
print(f'   monthly peaks {np.mean(sp):+.2f}   monthly troughs {np.mean(st):+.2f}')
print()
print('error distribution, monthly chronologies:')
import collections
for tag,arr in (('peaks',[r['ep'] for r in mo if r['ep'] is not None]),
                ('troughs',[r['et'] for r in mo if r['et'] is not None])):
    c_=collections.Counter(arr)
    print('  ',tag,'  '.join(f'{k:+d}:{c_[k]}' for k in sorted(c_)))
print()
print('MISSES')
for r in tot:
    if not r['hp']: print(f"   peak   {r['country']:26s} {str(r['peak_off']):10s} err {r['ep']}   {r['verdict']}")
for r in tot:
    if not r['ht']: print(f"   trough {r['country']:26s} {str(r['tr_off']):10s} err {r['et']}   {r['verdict']}")
