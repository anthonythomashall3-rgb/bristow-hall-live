"""Channels can be good at one end and bad at the other.

The NBER excludes the unemployment rate partly because it lags at the trough - an
end-specific judgement about a channel.  The rule has always had the hooks for this
and never used them.  Here each channel is dropped from the PEAK only, and from the
TROUGH only, and the effect measured.
"""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
from w2 import w2
bench.ABSTAIN=True
BASE={'exports','imports','car registrations','unemployment','construction production',
      'construction output','capital goods production','intermediate goods production',
      'consumer durables production'}
bench.SKIP=set(BASE)
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
def run(sp,st):
    bench.SKIP_PEAK=set(sp); bench.SKIP_TROUGH=set(st)
    t=[]
    for c in ALL: t+=run_country_concept(c,**K)
    bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set()
    a,na,b,nb,ma_,mb,sa,sb=w2(t); s=score(t,'',show=False)
    return (a+b,s['hp']+s['ht'],a,b,s['hp'],s['ht'],ma_,mb)
base=run(set(),set())
print(f'base  within2 {base[2]}+{base[3]}={base[0]}  hits {base[4]}/{base[5]}  MAE {base[6]:.2f}/{base[7]:.2f}',flush=True)
kept=[n for n in sorted({n for c in ALL for n,_ in channels(c)}) if n not in BASE]
print('\n--- dropped from the PEAK only',flush=True)
for nm in kept:
    o=run({nm},set())
    if o[0]!=base[0] or o[1]!=base[1]:
        print(f'   {nm:36s} within2 {o[0]-base[0]:+3d}  hits {o[1]-base[1]:+3d}  ({o[2]}+{o[3]}, {o[4]}/{o[5]})',flush=True)
print('\n--- dropped from the TROUGH only',flush=True)
for nm in kept:
    o=run(set(),{nm})
    if o[0]!=base[0] or o[1]!=base[1]:
        print(f'   {nm:36s} within2 {o[0]-base[0]:+3d}  hits {o[1]-base[1]:+3d}  ({o[2]}+{o[3]}, {o[4]}/{o[5]})',flush=True)
print('\n--- ADDED back at one end only (from the excluded nine)',flush=True)
for nm in sorted(BASE):
    bench.SKIP=BASE-{nm}
    o1=run({nm},set())   # available at the trough only
    o2=run(set(),{nm})   # available at the peak only
    bench.SKIP=set(BASE)
    print(f'   {nm:30s} trough-only {o1[0]-base[0]:+3d}/{o1[1]-base[1]:+3d}   peak-only {o2[0]-base[0]:+3d}/{o2[1]-base[1]:+3d}',flush=True)
