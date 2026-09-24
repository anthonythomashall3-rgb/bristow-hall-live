"""A committee that dates quarters is dated at quarterly frequency: the same two clauses,
on quarterly averages of the same channels, no monthly smoothing, four-quarter lookback.
France already works this way because the AFSE names quarterly GDP; this makes the
treatment uniform across the three quarterly chronologies."""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np, pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
_rcc=bench.run_country_concept
_QC={}
def toq(nm,s):
    k=(nm,id(s)); e=_QC.get(k)
    if e is None or e[0] is not s:
        e=(s,s.resample('QS').mean().dropna()); _QC[k]=e
    return e[1]

def run_q(country,**kw):
    cfg=bench.PANELS[country]; chs=[(nm,s) for nm,s in bench.channels(country) if nm not in bench.SKIP]
    rows=[]
    for _e in cfg['chrono']:
        pk_off,tr_off,freq=bench.ep3(_e,cfg['freq'])
        pkm=bench.q2m(pk_off); trm=bench.q2m(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        ds=bench.dating_series(country,w0,trm)
        if ds is not None:
            rows+=[r for r in _rcc(country,**kw) if r['peak_off']==pk_off and r['tr_off']==tr_off]
            continue
        use=[(nm,toq(nm,s)) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
        if not use: use=[(nm,toq(nm,s)) for nm,s in chs]
        bt=kw.get('band_t',.12); bp=kw.get('band_p',.01)
        dt_a=[bench.ch_trough(s,w0,w1,bt,1,4,abstain=True) for nm,s in use]
        dt_b=[bench.ch_trough(s,w0,w1,bt,1,4,abstain=False) for nm,s in use]
        tr=bench.med_fallback(dt_a,dt_b); end=tr if tr is not None else w1
        dp_a=[bench.ch_peak(s,w0,end,bp,1,abstain=True) for nm,s in use]
        dp_b=[bench.ch_peak(s,w0,end,bp,1,abstain=False) for nm,s in use]
        pk=bench.med_fallback(dp_a,dp_b)
        a,e1=bench.hit(pk,pk_off,'Q'); b,e2=bench.hit(tr,tr_off,'Q')
        rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=len(use),pk=pk,tr=tr,
                         ep=e1,et=e2,hp=a,ht=b,depth=None,sp=None,st=None,verdict='quarterly panel'))
    return rows

QUART=[c for c in ALL if PANELS[c]['freq']=='Q']
for tag,useq in (('base',False),('quarterly panel',True)):
    bench._DEV.clear()
    tot=[]
    for c in ALL:
        tot += (run_q(c,**K) if (useq and c in QUART) else _rcc(c,**K))
    s=score(tot,'',show=False)
    ep=[abs(r['ep']) for r in tot if r['ep'] is not None]
    et=[abs(r['et']) for r in tot if r['et'] is not None]
    mo=[r for r in tot if PANELS[r['country']]['freq']=='M']
    mep=[abs(r['ep']) for r in mo if r['ep'] is not None]; met=[abs(r['et']) for r in mo if r['et'] is not None]
    print(f'{tag:16s} peak {s["hp"]}/{s["n"]} trough {s["ht"]}/{s["n"]}   monthly-w2 '
          f'{sum(1 for x in mep if x<=2)},{sum(1 for x in met if x<=2)} of {len(mep)}   '
          f'exact {sum(1 for x in ep if x==0)},{sum(1 for x in et if x==0)}')
    for c in QUART:
        x=score([r for r in tot if r['country']==c],'',show=False)
        print(f'     {c:12s} P{x["hp"]}/{x["n"]} T{x["ht"]}/{x["n"]} MAD {x["mp"]:.2f}/{x["mt"]:.2f}')
