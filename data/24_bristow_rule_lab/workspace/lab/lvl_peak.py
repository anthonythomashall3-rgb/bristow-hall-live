import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.)

def ch_peak_first(level,w0,w1,band=0.02,n=3,run=4):
    """The peak read as the last month within band of the high before the first
    run of `run` consecutive monthly declines."""
    m=ma(prep(level,n),n)[w0:w1].dropna()
    if len(m)<run+2: return None
    v=m.values; idx=m.index
    for i in range(len(v)-1):
        if v[i+1]<v[i]:
            j=i+1; c=0
            while j<len(v) and v[j]<v[j-1]: c+=1; j+=1
            if c>=run:
                pre=m[:idx[i]]
                hi=float(pre.max()); on=pre[pre>=hi-band*max(hi-float(m.min()),1e-9)]
                return on.index[-1] if len(on) else idx[i]
    return None

for mode in ('base','firstfall'):
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
            r=run_country_concept.__wrapped__ if False else None
            base=date_any(c,use,w0,w1,**(dict(min_depth=1e9,lam=K['lam']) if cpt=='growth' else K))
            if cpt=='diffusion':
                d=date_diffusion_panel(use,w0,w1)
                pk=d['peak'] if d['peak'] is not None else base['peak']
                tr=d['trough'] if d['trough'] is not None else base['trough']
            else:
                pk,tr=base['peak'],base['trough']
            if mode=='firstfall' and cpt=='level':
                tr2=base['trough']
                cand=[ch_peak_first(s,w0,tr2 if tr2 is not None else w1,0.02,3,4) for nm,s in use]
                cand=[x for x in cand if x is not None]
                if cand: pk=_median(cand) if '_median' in dir(bench) else med(cand)
            a,_=hit(pk,pk_off,freq); b,_=hit(tr,tr_off,freq)
            tot.append(dict(country=c,hp=a,ht=b,nch=len(use),ep=None,et=None))
    s=score(tot,'',show=False)
    per=' '.join(f'{c[:4]}{score([r for r in tot if r["country"]==c],"",show=False)["hp"]}' for c in ALL)
    print(f'{mode:10s} peak {s["hp"]}/80 trough {s["ht"]}/80  | {per}')
