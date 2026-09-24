"""Japan diffusion route sweep, with the historical DI precomputed per (episode, n_di)."""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np, pandas as pd, itertools
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
cfg=PANELS['Japan']; chs=[(nm,s) for nm,s in channels('Japan') if nm not in bench.SKIP]
NDI=(1,3,5,7,9)
EPS=[]
for _e in cfg['chrono']:
    pk_off,tr_off,freq=ep3(_e,'M')
    pkm=ts(pk_off); trm=ts(tr_off)
    w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
    use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm] or chs
    dis={k:hist_di(use,k) for k in NDI}
    b=date_any('Japan',use,w0,w1,**K)
    EPS.append((pk_off,tr_off,w0,w1,dis,b))
print('episodes ready',flush=True)
grid=list(itertools.product((35.,40.,45.,50.,55.),(1,2,3,4,5,6,7),
                            (0.05,0.10,0.15,0.20,0.25,0.30,0.40,0.50),NDI,(1,3,5),('last','mid')))
print(len(grid),'configs',flush=True)
res=[]
for gi,(line,run_p,band,n_di,n_band,where) in enumerate(grid):
    hp=ht=0; ep=[]; et=[]
    for pk_off,tr_off,w0,w1,dis,b in EPS:
        di=dis[n_di]
        if di is None: pk=b['peak']; tr=b['trough']
        else:
            tr=ch_trough(di+1.0,w0,w1,band,n_band,12,abstain=False,where=where)
            end=tr if tr is not None else w1
            pk=di_peak_first(di,w0,end,line,run_p)
            if pk is None: pk=b['peak']
            if tr is None: tr=b['trough']
        a,e1=hit(pk,pk_off,'M'); c,e2=hit(tr,tr_off,'M')
        hp+=a; ht+=c
        if e1 is not None: ep.append(abs(e1))
        if e2 is not None: et.append(abs(e2))
    res.append((hp+ht,hp,ht,sum(1 for x in ep if x<=2)+sum(1 for x in et if x<=2),
                np.mean(ep),np.mean(et),line,run_p,band,n_di,n_band,where))
    if gi%400==0: print('  ...',gi,flush=True)
def show(tag,key):
    res.sort(key=key)
    print(tag,flush=True)
    for r in res[:15]:
        print(f'  tot={r[0]:2d} P{r[1]:2d} T{r[2]:2d} w2={r[3]:2d} MAD {r[4]:.2f}/{r[5]:.2f}  '
              f'line={r[6]} run_p={r[7]} band={r[8]} n_di={r[9]} n_band={r[10]} where={r[11]}',flush=True)
show('BY HITS',      lambda r:(-r[0],-r[3],r[4]+r[5]))
show('BY WITHIN-2',  lambda r:(-r[3],-r[0],r[4]+r[5]))
show('BY MEAN ERROR',lambda r:(r[4]+r[5],-r[0]))
print('shipped:',[r[:6] for r in res if (r[6],r[7],r[8],r[9],r[10],r[11])==(45.,4,0.30,5,3,'last')],flush=True)
