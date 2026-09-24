import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np
bench.SKIP={'exports','imports','car registrations','unemployment'}; bench.ABSTAIN=True
CFG=dict(min_depth=0.0,n=3,L=12,band_t=0.02,band_p=0.02,peak_cap=12)

print('--- sample')
tot_ep=0; dated=0
for c in ALL:
    ch=PANELS[c]['chrono']; tot_ep+=len(ch)
    r=run_country2(c,**CFG) if c in CLASSICAL else run_country2(c,**CFG)
    dated+=sum(1 for x in r if x['nch']>0)
print(f'episodes in the nine chronologies: {tot_ep};  with a usable panel: {dated}')

print()
print('--- architecture comparison, classical sample')
A=[];B=[];D=[]
for c in CLASSICAL:
    A+=run_country2(c,**CFG)
    B+=run_country_ci(c,band_t=0.02,band_p=0.02,n=3,peak_cap=12)
    D+=run_country4(c,band_t=0.02,band_p=0.02,n=3,peak_cap=12)
score(A,'A median of channel dates')
score(B,'B date a composite index')
score(D,'D date the median panel')

print()
print('--- channel ablation, classical sample (change in hits when dropped)')
base=score(A,'',show=False)
names=sorted({n for c in CLASSICAL for n,_ in channels(c)} - bench.SKIP)
res=[]
for nm in names:
    bench.SKIP={'exports','imports','car registrations','unemployment'}|{nm}
    t=[]
    for c in CLASSICAL: t+=run_country2(c,**CFG)
    s=score(t,'',show=False); res.append((s['hp']+s['ht']-base['hp']-base['ht'],nm))
bench.SKIP={'exports','imports','car registrations','unemployment'}
for d,nm in sorted(res): print(f'   {d:+3d}  {nm}')

print()
print('--- Japan and Korea: level, diffusion and deviation forms')
lv=[]
for c in DEVIATION: lv+=run_country2(c,**CFG)
score(lv,'level form')
di=[]
for c in DEVIATION: di+=run_country_di(c)
score(di,'diffusion form (ESRI rule)')
dv=[]
for c in DEVIATION: dv+=run_country_hp(c,lam=500000.,n=3)
score(dv,'deviation form (HP cyclical component)')

print()
print('--- standalone: no official dates anywhere, classical sample')
allr=[]; nx=0; xs=[]
for c in CLASSICAL:
    det=standalone(c,thr=1.5,q=0.5,gap=12,band_t=0.02,band_p=0.02)
    det=[d for d in det if d['depth'] is not None and d['depth']<=-2.0]
    rows,extra=match(c,det,window=18); allr+=rows; nx+=len(extra); xs+=[(c,d) for d in extra]
n=len(allr)
print(f'   episodes found {sum(1 for r in allr if r["found"])}/{n}   peak {sum(r["hp"] for r in allr)}/{n}   trough {sum(r["ht"] for r in allr)}/{n}   episodes outside the chronology {nx}')
for c,d in xs: print(f'      outside: {c:24s} {d["peak"]:%Y-%m} .. {d["trough"]:%Y-%m}  depth {d["depth"]:.1f}%')
