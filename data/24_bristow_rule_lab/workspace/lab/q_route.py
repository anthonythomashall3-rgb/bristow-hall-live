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
for c,files in Q.items():
    chs=[(f,load(f'{EST}/{f}.csv')) for f in files if os.path.exists(f'{EST}/{f}.csv')]
    for f,s in chs: print(f'   {c} {f}: {len(s)} {s.index.min().date()}..{s.index.max().date()}')
print()
mon=[]
for c in Q: mon+=run_country_concept(c,**K)
print('monthly panel, all 17 quarterly episodes: peak %d trough %d'%(sum(r['hp'] for r in mon),sum(r['ht'] for r in mon)))
hpQ=htQ=nQ=0; hpM=htM=0
for c,files in Q.items():
    chs=[(f,load(f'{EST}/{f}.csv')) for f in files if os.path.exists(f'{EST}/{f}.csv')]
    rows=[r for r in mon if r['country']==c]
    for r,_e in zip(rows,PANELS[c]['chrono']):
        pk_off,tr_off,freq=ep3(_e,PANELS[c]['freq'])
        pkm=q2m(pk_off); trm=q2m(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        use=[(n_,s_) for n_,s_ in chs if s_.index.min()<=w0 and s_.index.max()>=trm]
        if not use: continue
        nQ+=1
        tr=med([ch_trough(s_,w0,w1,0.03,1,4,abstain=False) for n_,s_ in use])
        pk=med([ch_peak(s_,w0,tr if tr is not None else w1,0.02,1,abstain=False) for n_,s_ in use])
        a,_=hit(pk,pk_off,'Q'); b,_=hit(tr,tr_off,'Q'); hpQ+=a; htQ+=b
        hpM+=r['hp']; htM+=r['ht']
        f=lambda d: d.strftime('%Y-%m') if d is not None else '--'
        print(f"{c:12s} {pk_off}->{tr_off}  quarterly {f(pk)}/{f(tr)} {'P' if a else '-'}{'T' if b else '-'}   monthly {f(r['pk'])}/{f(r['tr'])} {'P' if r['hp'] else '-'}{'T' if r['ht'] else '-'}")
print(f'\non the {nQ} episodes with quarterly GDP:  quarterly peak {hpQ} trough {htQ}   monthly peak {hpM} trough {htM}')
