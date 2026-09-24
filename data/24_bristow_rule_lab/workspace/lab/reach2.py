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
        if not (x['hp'] and x['ht']): miss.append((c,x['peak_off'],x['tr_off']))
print('misses:',len(miss))
GRID=[]
for bt in (0.01,0.02,0.03,0.05):
  for bp in (0.01,0.02,0.03,0.05):
    for cap in (9,12,18,24):
      for md in (3.0,5.0,8.0):
        for cpt in ('level','growth','diffusion'):
            GRID.append((bt,bp,cap,md,cpt))
print('settings per episode:',len(GRID))
cnt=collections.Counter(); tot=collections.Counter()
for c,pk_off,tr_off in miss:
    cfg=PANELS[c]; chs=[(nm,s) for nm,s in channels(c) if nm not in bench.SKIP]
    freq=cfg['freq']
    for _e in cfg['chrono']:
        p,t,f=ep3(_e,freq)
        if str(p)==str(pk_off) and str(t)==str(tr_off): freq=f; break
    pkm=ts(pk_off) if freq=='M' else q2m(pk_off); trm=ts(tr_off) if freq=='M' else q2m(tr_off)
    w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
    use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
    if not use: use=[(nm,s) for nm,s in chs if s.index.min()<=trm and s.index.max()>=trm]
    if not use: use=chs
    for bt,bp,cap,md,cpt in GRID:
        tot[(c,pk_off)]+=1
        if cpt=='diffusion':
            d=date_diffusion_panel(use,w0,w1)
            b=date_any(c,use,w0,w1,band_t=bt,band_p=bp,peak_cap=cap,min_depth=md,lam=K['lam'])
            pk=d['peak'] if d['peak'] is not None else b['peak']
            tr=d['trough'] if d['trough'] is not None else b['trough']
        elif cpt=='growth':
            b=date_any(c,use,w0,w1,band_t=bt,band_p=bp,peak_cap=cap,min_depth=1e9,lam=K['lam'])
            pk,tr=b['peak'],b['trough']
        else:
            b=date_any(c,use,w0,w1,band_t=bt,band_p=bp,peak_cap=cap,min_depth=md,lam=K['lam'])
            pk,tr=b['peak'],b['trough']
        if hit(pk,pk_off,freq)[0] and hit(tr,tr_off,freq)[0]: cnt[(c,pk_off)]+=1
reach=[k for k in tot if cnt[k]>0]
big=[k for k in tot if cnt[k]>=tot[k]/3]
small=[k for k in tot if 0<cnt[k]<tot[k]/10]
print(f'reachable by some setting: {len(reach)}/{len(miss)}')
print(f'reachable by a third or more of settings: {len(big)}')
print(f'reachable only by fewer than a tenth: {len(small)}')
for k in sorted(reach): print(f'   {k[0]:26s} {str(k[1]):12s} {cnt[k]}/{tot[k]}')
