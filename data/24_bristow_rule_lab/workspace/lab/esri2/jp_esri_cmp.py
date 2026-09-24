import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.ABSTAIN=True
di=load('/home/claude/lab/esri2/JPN_DI_coincident.csv')
EP=[(p,t) for p,t in JP_M if ts(p)-pd.DateOffset(months=12)>=di.index.min() and ts(t)<=di.index.max()]
print('comparable episodes:',len(EP))
best=[]
for line in (40.,45.,50.,55.,60.):
  for run in (1,2,3,4,5,7):
    hp=ht=0
    for pk_off,tr_off in EP:
        w0=ts(pk_off)-pd.DateOffset(months=12); w1=ts(tr_off)+pd.DateOffset(months=12)
        d=di_dates_censored(di,w0,w1,line,run,run)
        a,_=hit(d['peak'],pk_off,'M'); b,_=hit(d['trough'],tr_off,'M'); hp+=a; ht+=b
    best.append((hp+ht,hp,ht,line,run))
best.sort(reverse=True)
print('ESRI published DI, its own threshold rule, best settings:')
for x in best[:6]: print('   peak %d/%d trough %d/%d  line=%.0f run=%d'%(x[1],len(EP),x[2],len(EP),x[3],x[4]))
# our rule on the same episodes
chs=[(nm,s) for nm,s in channels('Japan') if nm not in bench.SKIP]
hp=ht=0
for pk_off,tr_off in EP:
    w0=ts(pk_off)-pd.DateOffset(months=12); w1=ts(tr_off)+pd.DateOffset(months=12)
    use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=ts(tr_off)] or chs
    d=date_diffusion_panel(use,w0,w1)
    b=date_any('Japan',use,w0,w1,min_depth=5.0,lam=500000.)
    pk=d['peak'] if d['peak'] is not None else b['peak']
    tr=d['trough'] if d['trough'] is not None else b['trough']
    a,_=hit(pk,pk_off,'M'); c,_=hit(tr,tr_off,'M'); hp+=a; ht+=c
print(f'Bristow Rule on the same {len(EP)} episodes:  peak {hp}/{len(EP)}  trough {ht}/{len(EP)}')
