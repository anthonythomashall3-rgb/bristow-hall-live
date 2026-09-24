"""A channel that does not fall after its high has no peak to contribute.
Test: abstain at the peak when the fall from the high to the subsequent low, inside the
peak window, is below `f` percent of the level."""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np, pandas as pd, collections
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
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
def run():
    bench._DEV.clear()
    tot=[]
    for c in ALL: tot+=run_country_concept(c,**K)
    return tot
def rep(tag,tot):
    s=score(tot,'',show=False)
    mo=[r for r in tot if PANELS[r['country']]['freq']=='M']
    mep=[abs(r['ep']) for r in mo if r['ep'] is not None]; met=[abs(r['et']) for r in mo if r['et'] is not None]
    print(f'{tag:10s} peak {s["hp"]}/83 trough {s["ht"]}/83  monthly MAD {np.mean(mep):.2f}/{np.mean(met):.2f}'
          f'  w2 {sum(1 for x in mep if x<=2)},{sum(1 for x in met if x<=2)} of {len(mep)}')
    return s['hp']+s['ht']
for f in (0.0,0.5,1.0,1.5,2.0,2.5,3.0,4.0,5.0):
    F[0]=f; rep(f'f={f}',run())
F[0]=2.0
tot=run()
print('\nUS episodes at f=2.0:')
for r in tot:
    if r['country']=='United States': print(f"   {r['peak_off']} ep={r['ep']} et={r['et']}")
