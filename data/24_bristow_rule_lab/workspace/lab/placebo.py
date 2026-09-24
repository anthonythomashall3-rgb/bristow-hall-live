import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
bench.ABSTAIN=True; bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set()
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
GRID=[]
for concept in ['level','growth','diffusion']:
    for bt in [0.01,0.02,0.03,0.05]:
        for bp in [0.01,0.02,0.03,0.05]:
            for cap in [9,12,18,24]:
                GRID.append(dict(concept=concept,band_t=bt,band_p=bp,peak_cap=cap))

def reach_count(shift_months):
    """How many of the missed episodes can be 'hit' at BOTH ends by some setting,
    when the target is displaced by shift_months?  shift=0 is the real test."""
    cur={}
    for c in ALL:
        for r in run_country_concept(c,**K): cur[(c,str(r['peak_off']))]=r
    n=0; tot=0
    for c in ALL:
        cfg=PANELS[c]; chs=[(nm,s) for nm,s in channels(c) if nm not in bench.SKIP]
        for _e in cfg['chrono']:
            pk,tr,fq=ep3(_e,cfg['freq'])
            r0=cur[(c,str(pk))]
            if r0['hp'] and r0['ht']: continue
            tot+=1
            pkm=ts(pk) if fq=='M' else q2m(pk); trm=ts(tr) if fq=='M' else q2m(tr)
            pkm2=pkm+pd.DateOffset(months=shift_months); trm2=trm+pd.DateOffset(months=shift_months)
            w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
            use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
            if not use: use=[(nm,s) for nm,s in chs if s.index.min()<=w1 and s.index.max()>=w0]
            if not use: continue
            ok=False
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
                a=abs(md(d['peak'],pkm2))<= (3 if fq=='M' else 4)
                b=abs(md(d['trough'],trm2))<= (3 if fq=='M' else 4)
                if a and b: ok=True; break
            n+=ok
    return n,tot

for sh in [0,12,-12,24,-24,36]:
    n,tot=reach_count(sh)
    lab='REAL target' if sh==0 else f'placebo, target shifted {sh:+d} months'
    print(f'{lab:38s}  {n}/{tot} of the missed episodes "reachable"')
