import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd, collections
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
miss=[]
for c in ALL:
    for x in run_country_concept(c,**K):
        if not (x['hp'] and x['ht']): miss.append((c,x['peak_off'],x['tr_off'],x['nch'],CONCEPT[c],x['ep'],x['et']))
GRID=[(bt,bp,cap,md) for bt in (0.03,0.08,0.12,0.16) for bp in (0.005,0.01,0.02,0.04)
      for cap in (9,12,18,24) for md in (3.0,5.0,8.0)]
print(f'{"chronology":24s} {"episode":12s} {"nch":>3s} {"routed":10s} {"err":>9s} {"level":>8s} {"growth":>8s} {"diff":>8s}')
for c,pk_off,tr_off,nch,cpt,ep,et in miss:
    cfg=PANELS[c]; chs=[(nm,s) for nm,s in channels(c) if nm not in bench.SKIP]
    freq=cfg['freq']
    for _e in cfg['chrono']:
        p,t,f=ep3(_e,cfg['freq'])
        if str(p)==str(pk_off) and str(t)==str(tr_off): freq=f; break
    pkm=ts(pk_off) if freq=='M' else q2m(pk_off); trm=ts(tr_off) if freq=='M' else q2m(tr_off)
    w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
    use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
    if not use: use=[(nm,s) for nm,s in chs if s.index.min()<=trm and s.index.max()>=trm]
    if not use: use=chs
    cnt=collections.Counter()
    for bt,bp,cap,md in GRID:
        for br in ('level','growth','diffusion'):
            if br=='diffusion':
                d=date_diffusion_panel(use,w0,w1)
                b=date_any(c,use,w0,w1,band_t=bt,band_p=bp,peak_cap=cap,min_depth=md,lam=K['lam'])
                pk=d['peak'] if d['peak'] is not None else b['peak']
                tr=d['trough'] if d['trough'] is not None else b['trough']
            elif br=='growth':
                b=date_any(c,use,w0,w1,band_t=bt,band_p=bp,peak_cap=cap,min_depth=1e9,lam=K['lam'])
                pk,tr=b['peak'],b['trough']
            else:
                b=date_any(c,use,w0,w1,band_t=bt,band_p=bp,peak_cap=cap,min_depth=md,lam=K['lam'])
                pk,tr=b['peak'],b['trough']
            if hit(pk,pk_off,freq)[0] and hit(tr,tr_off,freq)[0]: cnt[br]+=1
    n=len(GRID)
    print(f'{c:24s} {str(pk_off):12s} {nch:3d} {cpt:10s} {str(ep):>4s}/{str(et):<4s} {cnt["level"]:5d}/{n} {cnt["growth"]:5d}/{n} {cnt["diffusion"]:5d}/{n}')
