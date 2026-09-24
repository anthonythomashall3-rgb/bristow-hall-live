import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_p=0.01,peak_cap=18)
di=load('/home/claude/lab/esri2/JPN_DI_coincident.csv')
EP=[(p,t) for p,t in JP_M if ts(p)-pd.DateOffset(months=12)>=di.index.min() and ts(t)<=di.index.max()]
best=[]
for line in (40.,45.,50.,55.,60.):
  for run in (1,2,3,4,5,7):
    hp=ht=0
    for pk_off,tr_off in EP:
        w0=ts(pk_off)-pd.DateOffset(months=12); w1=ts(tr_off)+pd.DateOffset(months=12)
        d=di_dates_censored(di,w0,w1,line,run,run)
        hp+=hit(d['peak'],pk_off,'M')[0]; ht+=hit(d['trough'],tr_off,'M')[0]
    best.append((hp+ht,hp,ht,line,run))
    # also the first-sustained-fall reading of ESRI's own rule
best.sort(reverse=True)
print(f'ESRI published coincident DI ({len(EP)} contractions it covers), its own threshold rule')
for x in best[:4]: print(f'   peak {x[1]}/{len(EP)}  trough {x[2]}/{len(EP)}   line={x[3]:.0f} run={x[4]}')
b2=[]
for line in (40.,45.,50.,55.,60.):
  for run in (1,2,3,4,5,7):
    hp=ht=0
    for pk_off,tr_off in EP:
        w0=ts(pk_off)-pd.DateOffset(months=12); w1=ts(tr_off)+pd.DateOffset(months=12)
        tr=ch_trough(di+1.0,w0,w1,0.30,3,12,abstain=False)
        end=tr if tr is not None else w1
        pk=di_peak_first(di,w0,end,line,run)
        hp+=hit(pk,pk_off,'M')[0]; ht+=hit(tr,tr_off,'M')[0]
    b2.append((hp+ht,hp,ht,line,run))
b2.sort(reverse=True)
print('ESRI published coincident DI, the Bristow reading of the same threshold')
for x in b2[:4]: print(f'   peak {x[1]}/{len(EP)}  trough {x[2]}/{len(EP)}   line={x[3]:.0f} run={x[4]}')
chs=[(nm,s) for nm,s in channels('Japan') if nm not in bench.SKIP]
hp=ht=0
for pk_off,tr_off in EP:
    w0=ts(pk_off)-pd.DateOffset(months=12); w1=ts(tr_off)+pd.DateOffset(months=12)
    use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=ts(tr_off)] or chs
    d=date_diffusion_panel(use,w0,w1); b=date_any('Japan',use,w0,w1,**K)
    pk=d['peak'] if d['peak'] is not None else b['peak']
    tr=d['trough'] if d['trough'] is not None else b['trough']
    hp+=hit(pk,pk_off,'M')[0]; ht+=hit(tr,tr_off,'M')[0]
print(f'Bristow Rule on the OECD panel, same {len(EP)} contractions:  peak {hp}/{len(EP)}  trough {ht}/{len(EP)}')
