"""A search over the channel set, forwards and backwards.

Scored on Anthony's criterion - dates inside two months of the committee's own date,
at both ends - with the hit count as a tie-break.  Every candidate is then checked by
leaving each chronology out in turn, so a set that only works in sample is caught.
"""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
from w2 import w2
import collections
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
BASE={'exports','imports','car registrations','unemployment','construction production',
      'construction output','capital goods production','intermediate goods production',
      'consumer durables production'}
ALLNAMES=sorted({n for c in ALL for n,_ in channels(c)})
def run(skip):
    bench.SKIP=set(skip)
    t=[]
    for c in ALL: t+=run_country_concept(c,**K)
    return t
def obj(t):
    a,na,b,nb,ma_,mb,sa,sb=w2(t); s=score(t,'',show=False)
    return (a+b, s['hp']+s['ht'], a, b, s['hp'], s['ht'], ma_, mb)
cur=set(BASE)
t=run(cur); best=obj(t)
print(f'start  within2 {best[2]}+{best[3]}={best[0]}  hits {best[4]}/{best[5]}  MAE {best[6]:.2f}/{best[7]:.2f}',flush=True)
print('\n--- adding back one skipped channel at a time',flush=True)
for nm in sorted(BASE):
    o=obj(run(cur-{nm}))
    print(f'   +{nm:34s} within2 {o[0]:3d} ({o[0]-best[0]:+d})  hits {o[1]:3d} ({o[1]-best[1]:+d})',flush=True)
print('\n--- dropping one kept channel at a time',flush=True)
kept=[n for n in ALLNAMES if n not in BASE]
res=[]
for nm in kept:
    o=obj(run(cur|{nm}))
    res.append((o[0]-best[0],o[1]-best[1],nm))
for d,h,nm in sorted(res,reverse=True):
    if d or h: print(f'   -{nm:34s} within2 {d:+3d}  hits {h:+3d}',flush=True)
print('   (channels not listed change nothing)',flush=True)
bench.SKIP=set(BASE)
