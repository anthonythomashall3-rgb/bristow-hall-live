import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
E='/home/claude/lab/esri'
LEV=['industrial_production','producer_goods_shipments','durable_consumer_goods_shipments',
     'labor_input','investment_goods_shipments','operating_profits','effective_job_offer_rate',
     'exports_volume']
esri=[(n,load(f'{E}/JPN_{n}.csv')) for n in LEV]
chs=[(nm,s) for nm,s in channels('Japan') if nm not in bench.SKIP]
base=run_country_concept('Japan',**K)
for tag,mode in (('OECD panel (shipped)','panel'),
                 ("ESRI's own eight components where they exist",'esri'),
                 ("ESRI's eight plus the OECD channels",'both')):
    hp=ht=0; det=[]
    for i,(pk_off,tr_off) in enumerate(JP_M):
        pkm=ts(pk_off); trm=ts(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        av=lambda cc:[(n,s) for n,s in cc if s.index.min()<=w0 and s.index.max()>=trm]
        ue=av(esri); up=av(chs)
        if mode=='esri' and len(ue)==len(esri): use=ue
        elif mode=='both' and len(ue)==len(esri): use=ue+up
        else:
            use=up
            if not use: use=[(n,s) for n,s in chs if s.index.min()<=trm and s.index.max()>=trm] or chs
        d=date_diffusion_panel(use,w0,w1); b=date_any('Japan',use,w0,w1,**K)
        pk=d['peak'] if d['peak'] is not None else b['peak']
        tr=d['trough'] if d['trough'] is not None else b['trough']
        a,ep=hit(pk,pk_off,'M'); c,et=hit(tr,tr_off,'M'); hp+=a; ht+=c
        f2=lambda x: ('%+d'%x) if x is not None else ' --'
        r=base[i]
        det.append(f"   {pk_off}->{tr_off}  {f2(ep):>4s}/{f2(et):<4s} {'P' if a else '-'}{'T' if c else '-'}   shipped {f2(r['ep']):>4s}/{f2(r['et']):<4s}  n={len(use)}")
    print(f'{tag}: peak {hp}/16 trough {ht}/16')
    for x in det: print(x)
