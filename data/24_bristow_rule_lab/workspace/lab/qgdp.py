import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import os, pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_p=0.01,peak_cap=18)
EST='/home/claude/lab/estat'
GDP={'France':'/home/claude/lab/insee/FR_gdp_q_long.csv',
     'Euro area':f'{EST}/EA20_gdp_q.csv','Spain':f'{EST}/ES_gdp_q.csv'}
for c,p in GDP.items():
    if not os.path.exists(p): print(c,'missing'); continue
    g=load(p)
    rows=run_country_concept(c,**K)
    hpG=htG=hpM=htM=n=0
    for r,_e in zip(rows,PANELS[c]['chrono']):
        pk_off,tr_off,freq=ep3(_e,PANELS[c]['freq'])
        pkm=q2m(pk_off); trm=q2m(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        if g.index.min()>w0 or g.index.max()<trm: continue
        n+=1
        tr=ch_trough(g,w0,w1,0.03,1,4,abstain=False)
        pk=ch_peak(g,w0,tr if tr is not None else w1,0.01,1,abstain=False)
        a,_=hit(pk,pk_off,'Q'); b,_=hit(tr,tr_off,'Q')
        hpG+=a; htG+=b; hpM+=r['hp']; htM+=r['ht']
        f=lambda d: d.strftime('%Y-%m') if d is not None else '--'
        print(f"   {c:11s} {pk_off}->{tr_off}  GDP {f(pk)}/{f(tr)} {'P' if a else '-'}{'T' if b else '-'}   panel {f(r['pk'])}/{f(r['tr'])} {'P' if r['hp'] else '-'}{'T' if r['ht'] else '-'}")
    print(f'{c}: on {n} covered episodes  GDP {hpG}/{htG}   monthly panel {hpM}/{htM}')
