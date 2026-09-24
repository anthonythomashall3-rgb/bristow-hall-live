import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.)
chs=[(nm,s) for nm,s in channels('Japan') if nm not in bench.SKIP]
print(f'{"line":>5s} {"run":>4s}   Japan peak (threshold, else level route)')
for line in (40.,45.,50.):
  for run in (2,3,4,5,6,7):
    hp=ht=0; det=[]
    for pk_off,tr_off in JP_M:
        w0=ts(pk_off)-pd.DateOffset(months=12); w1=ts(tr_off)+pd.DateOffset(months=12)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=ts(tr_off)]
        if not use: use=[(nm,s) for nm,s in chs if s.index.min()<=ts(tr_off) and s.index.max()>=ts(tr_off)]
        if not use: use=chs
        di=hist_di(use,5)
        base=date_any('Japan',use,w0,w1,**K)
        if di is None: pk,tr=base['peak'],base['trough']
        else:
            tr=ch_trough(di+1.0,w0,w1,0.30,3,12,abstain=False)
            end=tr if tr is not None else w1
            pk=di_peak_first(di,w0,end,line,run)
            if pk is None: pk=base['peak']
            if tr is None: tr=base['trough']
        a,_=hit(pk,pk_off,'M'); b,_=hit(tr,tr_off,'M'); hp+=a; ht+=b
        det.append((pk_off,pk.strftime('%Y-%m') if pk is not None else '--',a))
    print(f'{line:5.0f} {run:4d}   peak {hp:2d}/16  trough {ht:2d}/16')
    if line==45. and run==5:
        for d in det: print('      ',d)
