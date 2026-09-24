import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
ch=dict(channels('Canada'))
gdp=ch['monthly GDP']; ip=ch['industrial production']; emp=ch['employment']
base=run_country_concept('Canada',**K)
print('C.D. Howe: "monthly GDP starting in 1961 or industrial production prior to 1961"')
for tag,mode in (('monthly GDP where it exists, else industrial production','gdp'),
                 ('GDP for the peak, GDP and employment for the trough','split')):
    hp=ht=0; det=[]
    for i,(pk_off,tr_off) in enumerate(CA_M):
        pkm=ts(pk_off); trm=ts(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        use=[]
        if gdp.index.min()<=w0 and gdp.index.max()>=trm: use=[gdp]
        else: use=[ip]
        ut=list(use)
        if mode=='split' and emp.index.min()<=w0 and emp.index.max()>=trm: ut=use+[emp]
        tr=med([ch_trough(s,w0,w1,0.12,3,12,abstain=False) for s in ut])
        pk=med([ch_peak(s,w0,tr if tr is not None else w1,0.01,3,abstain=False) for s in use])
        a,ep=hit(pk,pk_off,'M'); b,et=hit(tr,tr_off,'M'); hp+=a; ht+=b
        r=base[i]
        f2=lambda x: ('%+d'%x) if x is not None else ' --'
        det.append(f"   {pk_off}->{tr_off}  routed {f2(ep):>4s}/{f2(et):<4s} {'P' if a else '-'}{'T' if b else '-'}   panel {f2(r['ep']):>4s}/{f2(r['et']):<4s} {'P' if r['hp'] else '-'}{'T' if r['ht'] else '-'}")
    print(f'{tag}: peak {hp}/12 trough {ht}/12')
    for d in det: print(d)
s=score(base,'',show=False)
print(f'monthly panel (shipped): peak {s["hp"]}/12 trough {s["ht"]}/12')
