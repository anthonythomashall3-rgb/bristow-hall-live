"""The growth-cycle form as a PANEL: each channel detrended on its own, the two clauses
applied to each, and the median taken - the same structure the level route uses."""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np, pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
def rtt(s,lam):
    y=np.log(s.dropna()); y=y[np.isfinite(y)]
    t=pd.Series(hp_filter(y.values,lam),index=y.index)
    return np.exp(y-t)*100.0
chs=[(nm,s) for nm,s in channels('Korea') if nm not in bench.SKIP]
ref=load('/home/claude/lab/kei/KOR_RS__T.csv')
for lam in (129600.,500000.,1e6):
  for withref in (False,True):
    hp_=ht=0; ep=[]; et=[]; rows=[]
    for _e in PANELS['Korea']['chrono']:
        pk_off,tr_off,freq=ep3(_e,'M')
        pkm=ts(pk_off); trm=ts(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm] or chs
        objs=[rtt(s,lam) for nm,s in use]
        if withref and ref.index.min()<=w0 and ref.index.max()>=trm: objs.append(ref)
        dt=[ch_trough(o,w0,w1,0.0,3,12,abstain=False) for o in objs]
        tr=med(dt); end=tr if tr is not None else w1
        dp=[ch_peak(o,w0,end,0.0,3,abstain=False) for o in objs]
        pk=med(dp)
        a,e1=hit(pk,pk_off,'M'); b,e2=hit(tr,tr_off,'M')
        hp_+=a; ht+=b
        if e1 is not None: ep.append(abs(e1))
        if e2 is not None: et.append(abs(e2))
        rows.append((e1,e2,len(objs)))
    print(f'lam={lam:9.0f} ref={withref}:  P{hp_}/11 T{ht}/11 MAD {np.mean(ep):.2f}/{np.mean(et):.2f} '
          f' w2 {sum(1 for x in ep if x<=2)},{sum(1 for x in et if x<=2)}')
    print('    ', ' '.join(f'{r[0]}/{r[1]}' for r in rows))
print('current shipped: P8/11 T9/11 MAD 4.09/1.82')
