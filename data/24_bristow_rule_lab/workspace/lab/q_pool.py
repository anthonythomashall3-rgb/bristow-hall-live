import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import os, pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.)
EST='/home/claude/lab/estat'
Q={'Euro area':['EA20_gdp_q','EA20_emp_q'],'Spain':['ES_gdp_q','ES_emp_q'],'France':['FR_gdp_q']}
def qchs(c):
    return [(f,load(f'{EST}/{f}.csv')) for f in Q.get(c,[]) if os.path.exists(f'{EST}/{f}.csv')]
for mode in ('monthly only','pool monthly + quarterly'):
    hp=ht=n=0
    for c in Q:
        cfg=PANELS[c]; chs=[(nm,s) for nm,s in channels(c) if nm not in bench.SKIP]
        qq=qchs(c)
        for _e in cfg['chrono']:
            pk_off,tr_off,freq=ep3(_e,cfg['freq'])
            pkm=q2m(pk_off); trm=q2m(tr_off)
            w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
            use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm] or chs
            dt=[ch_trough(s,w0,w1,0.03,3,12,abstain=True) for nm,s in use]
            db=[ch_trough(s,w0,w1,0.03,3,12,abstain=False) for nm,s in use]
            if mode.startswith('pool'):
                uq=[(nm,s) for nm,s in qq if s.index.min()<=w0 and s.index.max()>=trm]
                dt+= [ch_trough(s,w0,w1,0.03,1,4,abstain=True) for nm,s in uq]
                db+= [ch_trough(s,w0,w1,0.03,1,4,abstain=False) for nm,s in uq]
            tr=med_fallback(dt,db); end=tr if tr is not None else w1
            comp=composite_dev(use,12,3,1)[w0:end].dropna(); cross=None
            for d_,v in comp.items():
                if v>=2.0: cross=d_; break
            p0=w0 if cross is None else max(w0,cross-pd.DateOffset(months=12))
            pa=[ch_peak(s,p0,end,0.02,3,abstain=True) for nm,s in use]
            pb=[ch_peak(s,p0,end,0.02,3,abstain=False) for nm,s in use]
            if mode.startswith('pool'):
                uq=[(nm,s) for nm,s in qq if s.index.min()<=w0 and s.index.max()>=trm]
                pa+=[ch_peak(s,p0,end,0.02,1,abstain=True) for nm,s in uq]
                pb+=[ch_peak(s,p0,end,0.02,1,abstain=False) for nm,s in uq]
            pk=med_fallback(pa,pb)
            a,_=hit(pk,pk_off,'Q'); b,_=hit(tr,tr_off,'Q'); hp+=a; ht+=b; n+=1
    print(f'{mode:28s} peak {hp}/{n} trough {ht}/{n}')
