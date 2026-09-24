import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np, pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
chs=[(nm,s) for nm,s in channels('Japan') if nm not in bench.SKIP]
res=[]
for line in (40.,45.,50.):
 for run_p in (3,4,5):
  for band in (0.05,0.10,0.20,0.30,0.45):
   for wt in ('last','mid'):
    for n_di in (3,5,7):
      ep=[];et=[]
      for pk_off,tr_off in JP_M:
        w0=ts(pk_off)-pd.DateOffset(months=12); w1=ts(tr_off)+pd.DateOffset(months=12)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=ts(tr_off)]
        if not use: use=[(nm,s) for nm,s in chs if s.index.min()<=ts(tr_off) and s.index.max()>=ts(tr_off)]
        if not use: use=chs
        di=hist_di(use,n_di); base=date_any('Japan',use,w0,w1,**K)
        if di is None: pk,tr=base['peak'],base['trough']
        else:
            tr=ch_trough(di+1.0,w0,w1,band,3,12,abstain=False,where=wt)
            end=tr if tr is not None else w1
            pk=di_peak_first(di,w0,end,line,run_p)
            if pk is None: pk=base['peak']
            if tr is None: tr=base['trough']
        a,e1=hit(pk,pk_off,'M'); b,e2=hit(tr,tr_off,'M')
        if e1 is not None: ep.append(abs(e1))
        if e2 is not None: et.append(abs(e2))
      w2p=sum(1 for x in ep if x<=2); w2t=sum(1 for x in et if x<=2)
      res.append((w2p+w2t,w2p,w2t,np.mean(ep),np.mean(et),line,run_p,band,wt,n_di))
res.sort(reverse=True)
print(f'{"w2":>3s} {"pk":>3s} {"tr":>3s} {"MAEp":>5s} {"MAEt":>5s}  line run band  where n_di')
for x in res[:16]:
    print(f'{x[0]:3d} {x[1]:3d} {x[2]:3d} {x[3]:5.2f} {x[4]:5.2f}  {x[5]:.0f}   {x[6]}  {x[7]:.2f} {x[8]:5s} {x[9]}')
print('current line=45 run=4 band=0.30 where=last n_di=5:',
      [r for r in res if r[5:]==(45.,4,0.30,'last',5)])
