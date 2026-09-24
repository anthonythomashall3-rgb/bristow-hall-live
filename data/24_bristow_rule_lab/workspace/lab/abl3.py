import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.)
BASE={'exports','imports','car registrations','unemployment','construction production',
      'construction output','capital goods production','intermediate goods production',
      'consumer durables production'}
def run(skip):
    bench.SKIP=set(skip)
    tot=[]
    for c in ALL: tot+=run_country_concept(c,**K)
    return score(tot,'',show=False)
b=run(BASE); print(f'base  peak {b["hp"]}/80 trough {b["ht"]}/80')
names=sorted({n for c in ALL for n,_ in channels(c)})
print()
print('--- adding back one skipped channel at a time')
for nm in sorted(BASE):
    s=run(BASE-{nm})
    print(f'   +{nm:34s} peak {s["hp"]:2d} ({s["hp"]-b["hp"]:+d})  trough {s["ht"]:2d} ({s["ht"]-b["ht"]:+d})')
print()
print('--- dropping one kept channel at a time')
kept=[n for n in names if n not in BASE]
for nm in kept:
    s=run(BASE|{nm})
    d=(s['hp']-b['hp'])+(s['ht']-b['ht'])
    if d!=0: print(f'   -{nm:34s} peak {s["hp"]:2d} ({s["hp"]-b["hp"]:+d})  trough {s["ht"]:2d} ({s["ht"]-b["ht"]:+d})')
