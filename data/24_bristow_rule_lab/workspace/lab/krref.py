"""Which detrended reference object does Korea date best?  OECD publishes three."""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np, pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
for tag in ('RS__T','RSRT','RSNOR'):
    ref=load(f'/home/claude/lab/kei/KOR_{tag}.csv')
    hp=ht=0; ep=[]; et=[]; rows=[]
    for _e in PANELS['Korea']['chrono']:
        pk_off,tr_off,freq=ep3(_e,'M')
        pkm=ts(pk_off); trm=ts(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        if ref.index.min()>w0 or ref.index.max()<trm:
            rows.append((pk_off,None,tr_off,None)); continue
        tr=ch_trough(ref,w0,w1,0.0,3,12,abstain=False)
        pk=ch_peak(ref,w0,tr if tr is not None else w1,0.0,3,abstain=False)
        a,e1=hit(pk,pk_off,'M'); b,e2=hit(tr,tr_off,'M')
        hp+=a; ht+=b
        if e1 is not None: ep.append(abs(e1))
        if e2 is not None: et.append(abs(e2))
        rows.append((pk_off,e1,tr_off,e2))
    print(f'{tag:8s} P{hp}/11 T{ht}/11  MAD {np.mean(ep):.2f}/{np.mean(et):.2f}  '
          f'w2 {sum(1 for x in ep if x<=2)},{sum(1 for x in et if x<=2)} of {len(ep)}')
    for r in rows: print('    ',r)
