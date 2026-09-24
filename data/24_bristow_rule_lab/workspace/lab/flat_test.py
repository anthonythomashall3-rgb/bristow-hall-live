import sys,os; sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab')
import bench, itertools, json, subprocess
from bench import *
bench.SKIP={'exports','imports','car registrations','unemployment','construction production','construction output','capital goods production','intermediate goods production','consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
LEVEL=['United States','United States (interwar)','Canada','Brazil']
def score(tag):
    ep=[];et=[];per={}
    for c in LEVEL:
        r=run_country_concept(c,**K); cfg=PANELS[c]
        for _e,b in zip(cfg['chrono'],r):
            pk,tr,f=ep3(_e,cfg['freq'])
            if f=='Q': continue
            ep.append(b['ep']); et.append(b['et'])
        per[c]=[x['et'] for x in r]
    g=lambda e,t: sum(1 for x in e if x is not None and abs(x)<=t)
    print(f"{tag:26s} level troughs {g(et,0):2d}/{g(et,1):2d}/{g(et,3):2d} of {len([x for x in et if x is not None])} | peaks {g(ep,0):2d}/{g(ep,1):2d}/{g(ep,3):2d}   {per}",flush=True)
score('off')
for beta,mn in itertools.product((0.01,0.02,0.03,0.05),(9,12,18)):
    bench.FLAT_BETA=beta; bench.FLAT_MIN=mn; score(f'beta {beta} min {mn}')
