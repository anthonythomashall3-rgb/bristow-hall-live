"""Abstention is a statement about the episode, not about the search window: a channel
whose high over the FULL episode window sits at an end of it has not turned inside the
episode and carries no information about the peak, wherever the peak is then placed."""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np, pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
_orig=bench.date_any
import types
src=None
def date_any2(country, chs, w0, w1, band_t=0.03, band_p=0.02, n=3, L=12, peak_cap=12,
              min_depth=5.0, max_spread=9, lam=129600.0):
    q=bench.quantity(country,chs) or chs
    deepest=None
    for nm,s in q:
        m=bench.ma(s,n)[w0:w1].dropna(); d=bench.maxdd(m)
        if d is not None and (deepest is None or d<deepest): deepest=d
    growth = deepest is None or deepest > -abs(min_depth)
    ch_t=[(nm,s) for nm,s in chs if nm not in bench.SKIP_TROUGH] or chs
    ch_p=[(nm,s) for nm,s in chs if nm not in bench.SKIP_PEAK] or chs
    dt_a=[bench.ch_trough(s,w0,w1,band_t,n,L,abstain=True) for nm,s in ch_t]
    dt_b=[bench.ch_trough(s,w0,w1,band_t,n,L,abstain=False) for nm,s in ch_t]
    l_tr=bench.med_fallback(dt_a,dt_b)
    end=l_tr if l_tr is not None else w1
    comp=bench.composite_dev(chs,L,n,1)[w0:end].dropna(); cross=None
    for d_,v in comp.items():
        if v>=2.0: cross=d_; break
    p0=w0 if (cross is None or peak_cap is None) else max(w0,cross-pd.DateOffset(months=peak_cap))
    dp_b=[bench.ch_peak(s,p0,end,band_p,n,abstain=False) for nm,s in ch_p]
    keep=[bench.ch_peak(s,w0,w1,band_p,n,abstain=True) is not None for nm,s in ch_p]
    dp_a=[v if k else None for v,k in zip(dp_b,keep)]
    l_pk=bench.med_fallback(dp_a,dp_b)
    r=_orig(country,chs,w0,w1,band_t,band_p,n,L,peak_cap,min_depth,max_spread,lam)
    r=dict(r); r['peak']=l_pk if not growth else r['peak']
    if not growth: r['trough']=l_tr if l_tr is not None else r['trough']
    return r
def run(tag):
    bench._DEV.clear()
    tot=[]
    for c in ALL: tot+=run_country_concept(c,**K)
    s=score(tot,'',show=False)
    ep=[abs(r['ep']) for r in tot if r['ep'] is not None]; et=[abs(r['et']) for r in tot if r['et'] is not None]
    mo=[r for r in tot if PANELS[r['country']]['freq']=='M']
    mep=[abs(r['ep']) for r in mo if r['ep'] is not None]; met=[abs(r['et']) for r in mo if r['et'] is not None]
    print(f'{tag:22s} peak {s["hp"]}/{s["n"]} trough {s["ht"]}/{s["n"]}  MAD {np.mean(ep):.2f}/{np.mean(et):.2f}'
          f'  monthly-w2 {sum(1 for x in mep if x<=2)},{sum(1 for x in met if x<=2)} of {len(mep)}')
    return tot
run('base')
bench.date_any=date_any2
tot=run('abstain on episode')
for r in tot:
    if (r['ep'] is not None and abs(r['ep'])>2) or (r['et'] is not None and abs(r['et'])>2):
        print(f"    {r['country']:24s} {str(r['peak_off']):10s} {r['ep']}   {str(r['tr_off']):10s} {r['et']}")
