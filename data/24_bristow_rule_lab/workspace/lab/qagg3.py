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
    if e is None or e[0] is not s: e=(s,s.resample('QS').mean().dropna()); _QC[k]=e
    return e[1]
def run_q(country,mode,**kw):
    cfg=bench.PANELS[country]; chs=[(nm,s) for nm,s in bench.channels(country) if nm not in bench.SKIP]
    rows=[]
    for _e in cfg['chrono']:
        pk_off,tr_off,freq=bench.ep3(_e,cfg['freq'])
        pkm=bench.q2m(pk_off); trm=bench.q2m(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        if bench.dating_series(country,w0,trm) is not None:
            rows+=[r for r in _rcc(country,**kw) if r['peak_off']==pk_off and r['tr_off']==tr_off]; continue
        use=[(nm,toq(nm,s)) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
        if not use: use=[(nm,toq(nm,s)) for nm,s in chs]
        r=bench.date_any(country,use,w0,w1,band_t=kw['band_t'],band_p=kw['band_p'],n=1,L=4,
                         peak_cap=(18 if mode=='cap' else None),min_depth=kw['min_depth'],lam=kw['lam'])
        pk,tr=r['peak'],r['trough']
        a,e1=bench.hit(pk,pk_off,'Q'); b,e2=bench.hit(tr,tr_off,'Q')
        rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=len(use),pk=pk,tr=tr,
                         ep=e1,et=e2,hp=a,ht=b,depth=None,sp=None,st=None,verdict=r['verdict']))
    return rows
QUART=[c for c in ALL if PANELS[c]['freq']=='Q']
for mode in ('cap','nocap'):
    bench._DEV.clear()
    tot=[]
    for c in ALL: tot += (run_q(c,mode,**K) if c in QUART else _rcc(c,**K))
    s=score(tot,'',show=False)
    ep=[abs(r['ep']) for r in tot if r['ep'] is not None]; et=[abs(r['et']) for r in tot if r['et'] is not None]
    print(f'date_any quarterly, peak_cap={mode}:  peak {s["hp"]}/{s["n"]} trough {s["ht"]}/{s["n"]}'
          f'  exact {sum(1 for x in ep if x==0)},{sum(1 for x in et if x==0)}')
    for c in QUART:
        x=score([r for r in tot if r['country']==c],'',show=False)
        print(f'    {c:12s} P{x["hp"]}/{x["n"]} T{x["ht"]}/{x["n"]} MAD {x["mp"]:.2f}/{x["mt"]:.2f}   '
              +' '.join(f"{r['ep']}/{r['et']}" for r in tot if r['country']==c))
