"""Test: restrict the trailing maximum to months at or after the window start."""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np, pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)

_orig_ch_trough = bench.ch_trough
_orig_dev = bench.dev
CLIP=[None]

def dev_clip(x, L=12, n=3):
    w0=CLIP[0]
    if w0 is None: return _orig_dev(x,L,n)
    m=bench.ma(x,n)
    mm=m.copy(); mm[mm.index<w0]=np.nan
    parts=[]
    for h in bench.HORIZONS:
        w=L+h
        if w<2: continue
        mx=mm.shift(1).rolling(w,min_periods=1).max()
        parts.append((mx-m)/mx*100.0)
    return parts[0] if len(parts)==1 else pd.concat(parts,axis=1).mean(axis=1)

def ch_trough_clip(level,w0,w1,band=0.02,n=3,L=12,tadj=False,win=120,minp=60,abstain=None,where=None):
    CLIP[0]=w0
    try:  return _orig_ch_trough(level,w0,w1,band,n,L,tadj,win,minp,abstain,where)
    finally: CLIP[0]=None

for tag,patch in (('base',False),('clipped',True)):
    if patch:
        bench.dev=dev_clip; bench.ch_trough=ch_trough_clip
    bench._cache.clear() if hasattr(bench,'_cache') else None
    bench._DEV.clear()
    tot=[]
    for c in ALL: tot+=run_country_concept(c,**K)
    s=score(tot,'',show=False)
    ep=[abs(r['ep']) for r in tot if r['ep'] is not None]
    et=[abs(r['et']) for r in tot if r['et'] is not None]
    print(f'{tag:9s} peak {s["hp"]}/{s["n"]} trough {s["ht"]}/{s["n"]}  '
          f'mean|e| {np.mean(ep):.2f}/{np.mean(et):.2f}  '
          f'w2 {sum(1 for x in ep if x<=2)}/{len(ep)},{sum(1 for x in et if x<=2)}/{len(et)}')
    if patch:
        for r in tot:
            if not r['ht']: print(f"   T miss {r['country']:24s} {r['tr_off']} err {r['et']}")
            if not r['hp']: print(f"   P miss {r['country']:24s} {r['peak_off']} err {r['ep']}")
