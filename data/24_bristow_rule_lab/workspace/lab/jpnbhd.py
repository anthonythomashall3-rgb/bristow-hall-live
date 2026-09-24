"""Robustness of the two Japan diffusion settings that tie on hits."""
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
EPS=[]
for _e in cfg['chrono']:
    pk_off,tr_off,freq=ep3(_e,'M')
    pkm=ts(pk_off); trm=ts(tr_off)
    w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
    use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm] or chs
    EPS.append((pk_off,tr_off,w0,w1,{k:hist_di(use,k) for k in (1,3,5)},
                date_any('Japan',use,w0,w1,**K)))
def sc(line,run_p,band,n_di,n_band,where='last',detail=False):
    hp=ht=0; ep=[]; et=[]; rows=[]
    for pk_off,tr_off,w0,w1,dis,b in EPS:
        di=dis[n_di]
        tr=ch_trough(di+1.0,w0,w1,band,n_band,12,abstain=False,where=where)
        end=tr if tr is not None else w1
        pk=di_peak_first(di,w0,end,line,run_p)
        if pk is None: pk=b['peak']
        if tr is None: tr=b['trough']
        a,e1=hit(pk,pk_off,'M'); c,e2=hit(tr,tr_off,'M')
        hp+=a; ht+=c
        if e1 is not None: ep.append(abs(e1))
        if e2 is not None: et.append(abs(e2))
        rows.append((pk_off,e1,tr_off,e2))
    r=(hp,ht,sum(1 for x in ep if x<=2)+sum(1 for x in et if x<=2),np.mean(ep),np.mean(et))
    return (r,rows) if detail else r
print('SHIPPED    line=45 run_p=4 band=0.30 n_di=5 n_band=3 ->',sc(45,4,.30,5,3))
print('CANDIDATE  line=45 run_p=1 band=0.40 n_di=1 n_band=5 ->',sc(45,1,.40,1,5))
print()
print('neighbourhood of the candidate (P,T,w2,MADp,MADt):')
for line in (40,45,50):
    for run_p in (1,2,3,4):
        row=[]
        for band in (.30,.35,.40,.45,.50):
            r=sc(line,run_p,band,1,5)
            row.append(f'{r[0]}/{r[1]}:{r[2]}')
        print(f'  line={line} run_p={run_p}  '+'  '.join(row))
print()
print('n_band sensitivity at line=45 run_p=1 band=0.40 n_di=1:')
for nb in (1,3,5):
    print('   n_band=',nb,sc(45,1,.40,1,nb))
print('n_di sensitivity at line=45 run_p=1 band=0.40 n_band=5:')
for nd in (1,3,5):
    print('   n_di=',nd,sc(45,1,.40,nd,5))
r,rows=sc(45,1,.40,1,5,detail=True)
print(); print('candidate per-episode errors:')
for x in rows: print('   ',x)

print()
print('one-at-a-time perturbation robustness (total hits P+T; base in brackets):')
GRID=dict(line=[35,40,45,50,55],run_p=[1,2,3,4,5,6,7],band=[.10,.15,.20,.25,.30,.35,.40,.45,.50],
          n_di=[1,3,5],n_band=[1,3,5])
for tag,base in (('shipped  ',dict(line=45,run_p=4,band=.30,n_di=5,n_band=3)),
                 ('candidate',dict(line=45,run_p=1,band=.40,n_di=1,n_band=5))):
    b=sc(**base); tot=b[0]+b[1]
    out=[]
    ok=n=0
    for k,vals in GRID.items():
        line=[]
        for v in vals:
            if v==base[k]: line.append('  *'); continue
            d=dict(base); d[k]=v; r=sc(**d); n+=1; ok+= (r[0]+r[1]>=tot-1)
            line.append(f'{r[0]+r[1]:3d}')
        out.append(f'   {k:7s} '+' '.join(line))
    print(f'  {tag} base total {tot}  neighbours within one hit: {ok}/{n}')
    print('\n'.join(out))
