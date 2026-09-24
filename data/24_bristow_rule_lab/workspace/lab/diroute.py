import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(band_t=0.03,band_p=0.01,peak_cap=18,n=3,L=12,min_depth=5.0,lam=500000.)
def run(mode,minch=0):
    tot=[]
    for c in ALL:
        cfg=PANELS[c]; chs=[(nm,s) for nm,s in channels(c) if nm not in bench.SKIP]
        cpt=CONCEPT.get(c,'level')
        for _e in cfg['chrono']:
            pk_off,tr_off,freq=ep3(_e,cfg['freq'])
            pkm=ts(pk_off) if freq=='M' else q2m(pk_off); trm=ts(tr_off) if freq=='M' else q2m(tr_off)
            w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
            use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
            if not use: use=[(nm,s) for nm,s in chs if s.index.min()<=trm and s.index.max()>=trm]
            if not use: use=chs
            if cpt=='growth':
                b=date_any(c,use,w0,w1,**{**K,'min_depth':1e9}); pk,tr=b['peak'],b['trough']
            elif cpt=='diffusion':
                d=date_diffusion_panel(use,w0,w1); b=date_any(c,use,w0,w1,**K)
                pk=d['peak'] if d['peak'] is not None else b['peak']
                tr=d['trough'] if d['trough'] is not None else b['trough']
            else:
                b=date_any(c,use,w0,w1,**K); pk,tr=b['peak'],b['trough']
                if mode!='off' and len(use)>=minch:
                    d=date_diffusion_panel(use,w0,w1)
                    if mode in ('peak','both') and d['peak'] is not None: pk=d['peak']
                    if mode in ('trough','both') and d['trough'] is not None: tr=d['trough']
                    if pk is not None and tr is not None and pk>tr: pk,tr=tr,pk
            a,ep=hit(pk,pk_off,freq); bb,et=hit(tr,tr_off,freq)
            tot.append(dict(country=c,hp=a,ht=bb,nch=len(use),ep=ep,et=et))
    return score(tot,'',show=False),tot
for mode in ('off','peak','trough','both'):
  for minch in ((0,) if mode=='off' else (0,5,8,10)):
    s,tot=run(mode,minch)
    per=' '.join(f'{c[:4]}{score([r for r in tot if r["country"]==c],"",show=False)["hp"]}/{score([r for r in tot if r["country"]==c],"",show=False)["ht"]}' for c in ALL)
    print(f'diffusion clause on level chronologies: {mode:7s} minch={minch:2d}  peak {s["hp"]}/83 trough {s["ht"]}/83 | {per}')
