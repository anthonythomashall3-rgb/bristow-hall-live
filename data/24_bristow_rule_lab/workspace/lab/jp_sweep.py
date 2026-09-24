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
res=[]
for line in (40.,45.,50.,55.):
  for run in (1,2,3,4,5,6,7):
    for band in (0.20,0.30,0.40):
      for n_di in (3,5,7):
        hp=ht=0
        for pk_off,tr_off in JP_M:
            pkm=ts(pk_off); trm=ts(tr_off)
            w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
            use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
            if not use: use=[(nm,s) for nm,s in chs if s.index.min()<=trm and s.index.max()>=trm]
            if not use: use=chs
            d=date_diffusion_panel(use,w0,w1,line=line,run=run,band=band,n_di=n_di)
            b=date_any('Japan',use,w0,w1,**K)
            pk=d['peak'] if d['peak'] is not None else b['peak']
            tr=d['trough'] if d['trough'] is not None else b['trough']
            a,_=hit(pk,pk_off,'M'); c,_=hit(tr,tr_off,'M'); hp+=a; ht+=c
        res.append((hp+ht,hp,ht,line,run,band,n_di))
res.sort(reverse=True)
for x in res[:18]: print('tot=%2d peak=%2d/16 trough=%2d/16  line=%.0f run=%d band=%.2f n_di=%d'%x)
print('--- shipped line=45 run=1 band=0.30 n_di=5:',[r for r in res if r[3:]==(45.,1,0.30,5)])
