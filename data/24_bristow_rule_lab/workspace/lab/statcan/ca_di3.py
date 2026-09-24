"""Canada dated on the three pieces of evidence the Council names: the monthly output
series, monthly employment, and the industry diffusion index."""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np, pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
DI=pd.read_csv('/home/claude/lab/statcan/CA_gdp_diffusion.csv',index_col=0,parse_dates=True)['value']
ch=dict(channels('Canada'))
def score_ca(n_s, use_in_peak, band_di):
    rows=[]
    d=ma(DI,n_s).dropna() if n_s>1 else DI
    for _e in PANELS['Canada']['chrono']:
        pk_off,tr_off,freq=ep3(_e,'M')
        pkm=ts(pk_off); trm=ts(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        gdp=ch.get('monthly GDP'); ip=ch.get('industrial production'); emp=ch.get('employment')
        ok=lambda s: s is not None and s.index.min()<=w0 and s.index.max()>=trm
        core = gdp if ok(gdp) else (ip if ok(ip) else None)
        if core is None: rows.append((pk_off,None,tr_off,None)); continue
        gt=[core]+([emp] if ok(emp) else [])
        gp=[core]
        if d.index.min()<=w0 and d.index.max()>=trm:
            dt=ch_trough(d,w0,w1,band_di,1,12,abstain=False,where='last')
            if dt is not None: gt=gt+[None]  # placeholder, handled below
        tr_dates=[ch_trough(x,w0,w1,0.12,3,12,abstain=False) for x in gt if x is not None]
        if d.index.min()<=w0 and d.index.max()>=trm:
            x=ch_trough(d,w0,w1,band_di,1,12,abstain=False,where='last')
            if x is not None: tr_dates.append(x)
        tr=med(tr_dates)
        pk_dates=[ch_peak(x,w0,tr if tr is not None else w1,0.01,3,abstain=False) for x in gp]
        if use_in_peak and d.index.min()<=w0 and d.index.max()>=trm:
            p=di_peak_first(d,w0,tr if tr is not None else w1,50.,4)
            if p is not None: pk_dates.append(p)
        pk=med(pk_dates)
        a,e1=hit(pk,pk_off,'M'); b,e2=hit(tr,tr_off,'M')
        rows.append((pk_off,e1,tr_off,e2))
    ep=[abs(r[1]) for r in rows if r[1] is not None]; et=[abs(r[3]) for r in rows if r[3] is not None]
    return (sum(1 for x in ep if x<=3), sum(1 for x in et if x<=3), np.mean(ep), np.mean(et),
            sum(1 for x in ep if x<=2), sum(1 for x in et if x<=2), rows)
print('current Canada: P11/12 MAD 1.58   T10/12 MAD 2.75   within2 P?,T?')
for n_s in (1,3,6,9,12,15,18):
    for bd in (0.30,):
        r=score_ca(n_s,False,bd)
        print(f'  DI smoothing {n_s:2d}  band {bd}:  P{r[0]}/12 T{r[1]}/12  MAD {r[2]:.2f}/{r[3]:.2f}  w2 {r[4]},{r[5]}')
print()
r=score_ca(12,False,0.30)
for x in r[6]: print('   ',x)
