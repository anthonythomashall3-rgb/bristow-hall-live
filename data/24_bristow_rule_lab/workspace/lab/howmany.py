import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np
bench.ABSTAIN=True; bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set()
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
K=dict(min_depth=5.0,lam=500000.)
GRID=[]
for concept in ['level','growth','diffusion']:
    for bt in [0.01,0.02,0.03,0.05]:
        for bp in [0.01,0.02,0.03,0.05]:
            for cap in [9,12,18,24]:
                GRID.append(dict(concept=concept,band_t=bt,band_p=bp,peak_cap=cap))
cur={}
for c in ALL:
    for r in run_country_concept(c,**K): cur[(c,str(r['peak_off']))]=r
print('for each missed episode: how many of the 192 settings date it right at BOTH ends')
print(f'{"chronology":22s} {"episode":20s} {"hits/192":>9s}  {"share":>6s}')
tot=[]
for c in ALL:
    cfg=PANELS[c]; chs=[(nm,s) for nm,s in channels(c) if nm not in bench.SKIP]
    for _e in cfg['chrono']:
        pk,tr,fq=ep3(_e,cfg['freq'])
        r0=cur[(c,str(pk))]
        if r0['hp'] and r0['ht']: continue
        pkm=ts(pk) if fq=='M' else q2m(pk); trm=ts(tr) if fq=='M' else q2m(tr)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
        if not use: use=[(nm,s) for nm,s in chs if s.index.min()<=w1 and s.index.max()>=w0]
        if not use: continue
        k=0
        for g in GRID:
            cpt=g['concept']
            try:
                if cpt=='diffusion': d=date_diffusion_panel(use,w0,w1)
                else:
                    kk=dict(K); kk.update({k2:v2 for k2,v2 in g.items() if k2!='concept'})
                    kk['min_depth']=1e9 if cpt=='growth' else 0.0
                    d=date_any(c,use,w0,w1,**kk)
            except Exception: continue
            if d['peak'] is None or d['trough'] is None: continue
            a,_=hit(d['peak'],pk,fq); b,_=hit(d['trough'],tr,fq)
            k+=(a and b)
        if k>0: tot.append(k)
        print(f'{c:22s} {str(pk)+" "+str(tr):20s} {k:9d}  {100*k/len(GRID):5.1f}%')
print()
if tot:
    print(f'reachable episodes: {len(tot)};  median share of settings that hit: {np.median(tot)/len(GRID)*100:.0f}%')
    print(f'   hit by fewer than 10% of settings (a lucky corner): {sum(1 for t in tot if t<0.10*len(GRID))}')
    print(f'   hit by more than 25% of settings (a real region):   {sum(1 for t in tot if t>0.25*len(GRID))}')
