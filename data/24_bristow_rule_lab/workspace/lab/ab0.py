"""Test: a channel whose low sits at the START of the window has not turned in it."""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np, pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
_orig=bench.ch_trough
KLEAD=[0]

def mk(k):
    def f(level,w0,w1,band=0.02,n=3,L=12,tadj=False,win=120,minp=60,abstain=None,where=None):
        _ab = bench.ABSTAIN if abstain is None else abstain
        lv=bench.prep(level,n,tadj,win,minp)
        m=bench.ma(lv,n)[w0:w1].dropna()
        if _ab and len(m)>k:
            i=m.idxmin()
            if i in list(m.index[:k+1]): return None
        return _orig(level,w0,w1,band,n,L,tadj,win,minp,abstain,where)
    return f

def run(tag):
    bench._DEV.clear()
    tot=[]
    for c in ALL: tot+=run_country_concept(c,**K)
    s=score(tot,'',show=False)
    ep=[abs(r['ep']) for r in tot if r['ep'] is not None]
    et=[abs(r['et']) for r in tot if r['et'] is not None]
    print(f'{tag:12s} peak {s["hp"]}/{s["n"]} trough {s["ht"]}/{s["n"]}  '
          f'mean|e| {np.mean(ep):.2f}/{np.mean(et):.2f}  '
          f'w2 {sum(1 for x in ep if x<=2)},{sum(1 for x in et if x<=2)} of {len(ep)},{len(et)}')
    return tot

run('base')
for k in (0,1,2,3):
    bench.ch_trough=mk(k)
    tot=run(f'abstain k={k}')
bench.ch_trough=mk(0); tot=run('final k=0')
for r in tot:
    if not r['ht']: print(f"   T {r['country']:24s} {r['tr_off']} err {r['et']}")
