import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import os, pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
EST='/home/claude/lab/estat'
SET={'Euro area':['EA20_gdp_q','EA20_emp_q'],'Spain':['ES_gdp_q','ES_emp_q']}
for c,files in SET.items():
    ser=[load(f'{EST}/{f}.csv') for f in files if os.path.exists(f'{EST}/{f}.csv')]
    base=run_country_concept(c,**K)
    print(f'== {c}: the CEPR names "domestic production and employment" as primary')
    for tag,use_set in (('GDP alone',ser[:1]),('GDP and employment',ser)):
        hp=ht=n=0; det=[]
        for r,_e in zip(base,PANELS[c]['chrono']):
            pk_off,tr_off,freq=ep3(_e,PANELS[c]['freq'])
            pkm=q2m(pk_off); trm=q2m(tr_off)
            w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
            u=[s for s in use_set if s.index.min()<=w0 and s.index.max()>=trm]
            if len(u)<len(use_set): continue
            n+=1
            tr=med([ch_trough(s,w0,w1,0.12,1,4,abstain=False) for s in u])
            pk=med([ch_peak(s,w0,tr if tr is not None else w1,0.01,1,abstain=False) for s in u])
            a,ep=hit(pk,pk_off,'Q'); b,et=hit(tr,tr_off,'Q'); hp+=a; ht+=b
            f2=lambda x: ('%+d'%x) if x is not None else ' --'
            det.append(f"   {pk_off}->{tr_off}  routed {f2(ep):>4s}/{f2(et):<4s} {'P' if a else '-'}{'T' if b else '-'}   panel {f2(r['ep']):>4s}/{f2(r['et']):<4s} {'P' if r['hp'] else '-'}{'T' if r['ht'] else '-'}")
        print(f'   {tag}: on {n} covered episodes  peak {hp}/{n} trough {ht}/{n}')
        for d in det: print(d)
