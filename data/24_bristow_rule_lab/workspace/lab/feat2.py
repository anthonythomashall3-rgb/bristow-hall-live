import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd, numpy as np
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
rows=[]
for c in ALL:
    cfg=PANELS[c]; chs=[(nm,s) for nm,s in channels(c) if nm not in bench.SKIP]
    cpt=CONCEPT.get(c,'level')
    shipped=run_country_concept(c,**K); i=0
    for _e in cfg['chrono']:
        pk_off,tr_off,freq=ep3(_e,cfg['freq']); r=shipped[i]; i+=1
        pkm=ts(pk_off) if freq=='M' else q2m(pk_off); trm=ts(tr_off) if freq=='M' else q2m(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
        if not use: use=[(nm,s) for nm,s in chs if s.index.min()<=trm and s.index.max()>=trm]
        if not use: use=chs
        di=hist_di(use,5)
        dimin=float(di[w0:w1].dropna().min()) if di is not None and len(di[w0:w1].dropna()) else np.nan
        q=quantity(c,use) or use
        deepest=None
        for nm,s in q:
            m=ma(s,3)[w0:w1].dropna(); d=maxdd(m)
            if d is not None and (deepest is None or d<deepest): deepest=d
        # diffusion branch answer
        d=date_diffusion_panel(use,w0,w1); b=date_any(c,use,w0,w1,**K)
        dpk=d['peak'] if d['peak'] is not None else b['peak']
        dtr=d['trough'] if d['trough'] is not None else b['trough']
        dhit=hit(dpk,pk_off,freq)[0] and hit(dtr,tr_off,freq)[0]
        shit=r['hp'] and r['ht']
        rows.append(dict(country=c,ep=str(pk_off),nch=len(use),dimin=dimin,
                         deepest=deepest if deepest is not None else np.nan,
                         sp=r['sp'],shit=shit,dhit=dhit,cpt=cpt,
                         length=(trm.year-pkm.year)*12+(trm.month-pkm.month)))
df=pd.DataFrame(rows)
lv=df[df.cpt=='level']
g1=lv[(~lv.shit)&(lv.dhit)]   # diffusion would fix it
g2=lv[lv.shit]                # already right
print(f'level chronologies: {len(lv)} episodes; diffusion would fix {len(g1)}; already right {len(g2)}')
for col in ('nch','dimin','deepest','length'):
    print(f'   {col:9s} diffusion-would-fix median {g1[col].median():8.2f}   already-right median {g2[col].median():8.2f}')
print()
print(g1[['country','ep','nch','dimin','deepest','length']].to_string(index=False))
