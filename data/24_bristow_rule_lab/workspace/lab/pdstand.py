"""Independent test of the channel-level peak-depth abstention: the standalone task,
which uses no official windows at all and was not used to choose anything."""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
_orig=bench.ch_peak
F=[0.0]
def ch_peak_f(level,w0,w1,band=0.02,n=3,tadj=False,win=120,minp=60,abstain=None,where=None):
    _ab=bench.ABSTAIN if abstain is None else abstain
    if _ab and F[0]>0:
        lv=bench.prep(level,n,tadj,win,minp)
        m=bench.ma(lv,n)[w0:w1].dropna()
        if len(m)>=4:
            hi=float(m.max()); i=m.idxmax()
            lo=float(m[i:].min()) if len(m[i:]) else float(m.min())
            if hi>0 and (hi-lo)/hi*100.0 < F[0]: return None
    return _orig(level,w0,w1,band,n,tadj,win,minp,abstain,where)
bench.ch_peak=ch_peak_f
LEVEL=[c for c in ALL if CONCEPT[c]=='level']
for f in (0.0,0.5,1.0,1.5,2.0,3.0):
    F[0]=f; bench._DEV.clear()
    allr=[]; nx=0
    for c in LEVEL:
        det=standalone(c,thr=1.5,q=0.5,gap=12,band_t=0.03,band_p=0.01)
        det=[d for d in det if d['depth'] is not None and d['depth']<=-2.0]
        rows,extra=match(c,det,window=18); allr+=rows; nx+=len(extra)
    n=len(allr)
    print(f'f={f}:  found {sum(1 for r in allr if r["found"])}/{n}  peak {sum(r["hp"] for r in allr)}/{n}'
          f'  trough {sum(r["ht"] for r in allr)}/{n}  extra {nx}')
