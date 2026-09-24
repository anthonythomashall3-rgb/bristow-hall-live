"""The band clause says the centre month of the RUN in which the level stays within the
band.  Test making that run contiguous around the extremum, as the words say."""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np, pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)

def _block(sel, anchor_pos):
    """maximal contiguous True block of `sel` containing anchor_pos"""
    n=len(sel); i=anchor_pos
    if not sel[i]: return (i,i)
    a=i
    while a-1>=0 and sel[a-1]: a-=1
    b=i
    while b+1<n and sel[b+1]: b+=1
    return (a,b)

def pick(idx,a,b,where):
    return idx[b] if where=='last' else idx[a+(b-a)//2]

MODE=['base']
def ch_peak_c(level,w0,w1,band=0.02,n=3,tadj=False,win=120,minp=60,abstain=None,where=None):
    _ab=bench.ABSTAIN if abstain is None else abstain
    where=bench.PLATEAU_P if where is None else where
    lv=bench.prep(level,n,tadj,win,minp)
    m=bench.ma(lv,n)[w0:w1].dropna()
    if len(m)<4: return None
    hi=float(m.max()); i=m.idxmin() if False else m.idxmax()
    if _ab and (i==m.index[0] or i==m.index[-1]): return None
    lo=float(m[i:].min()) if len(m[i:]) else float(m.min())
    amp=max(hi-lo,1e-9)
    sel=(m.values>=hi-band*amp)
    a,b=_block(sel,list(m.index).index(i))
    return pick(list(m.index),a,b,where)

def ch_trough_c(level,w0,w1,band=0.02,n=3,L=12,tadj=False,win=120,minp=60,abstain=None,where=None):
    _ab=bench.ABSTAIN if abstain is None else abstain
    where=bench.PLATEAU_T if where is None else where
    lv=bench.prep(level,n,tadj,win,minp)
    d=bench.dev(lv,L,n)[w0:w1].dropna()
    if len(d)==0: return None
    d_peak=d.idxmax()
    m=bench.ma(lv,n)[w0:w1].dropna()
    if len(m)<4: return d_peak
    lo=float(m.min()); i=m.idxmin()
    if _ab and i==m.index[-1]: return None
    hi=float(m[:i].max()) if len(m[:i]) else float(m.max())
    amp=max(hi-lo,1e-9)
    sel=(m.values<=lo+band*amp)
    a,b=_block(sel,list(m.index).index(i))
    p=pick(list(m.index),a,b,where)
    return max(d_peak,p) if p is not None else d_peak

_op,_ot=bench.ch_peak,bench.ch_trough
def run(tag):
    bench._DEV.clear()
    tot=[]
    for c in ALL: tot+=run_country_concept(c,**K)
    s=score(tot,'',show=False)
    ep=[abs(r['ep']) for r in tot if r['ep'] is not None]
    et=[abs(r['et']) for r in tot if r['et'] is not None]
    print(f'{tag:16s} peak {s["hp"]}/{s["n"]} trough {s["ht"]}/{s["n"]}  MAD {np.mean(ep):.2f}/{np.mean(et):.2f}'
          f'  w2 {sum(1 for x in ep if x<=2)},{sum(1 for x in et if x<=2)} of {len(ep)}'
          f'  w3 {sum(1 for x in ep if x<=3)},{sum(1 for x in et if x<=3)}')
    return tot
run('base')
bench.ch_peak=ch_peak_c;                        run('contig peak')
bench.ch_peak=_op; bench.ch_trough=ch_trough_c; run('contig trough')
bench.ch_peak=ch_peak_c;                        tot=run('contig both')
for r in tot:
    if (r['ep'] is not None and abs(r['ep'])>2) or (r['et'] is not None and abs(r['et'])>2):
        print(f"    {r['country']:24s} {str(r['peak_off']):10s} {r['ep']}  {str(r['tr_off']):10s} {r['et']}")
