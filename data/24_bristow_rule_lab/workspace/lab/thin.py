import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd
CORE={'exports','imports','car registrations','unemployment','construction production',
      'construction output','capital goods production','intermediate goods production',
      'consumer durables production'}
bench.SKIP=CORE; bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.)

def run_country_thin(country, minch, lead=12, tail=12, **kw):
    cfg=PANELS[country]
    allch=channels(country)
    core=[(nm,s) for nm,s in allch if nm not in CORE]
    cpt=CONCEPT.get(country,'level'); rows=[]
    for _e in cfg['chrono']:
        pk_off,tr_off,freq=ep3(_e,cfg['freq'])
        pkm=ts(pk_off) if freq=='M' else q2m(pk_off); trm=ts(tr_off) if freq=='M' else q2m(tr_off)
        w0=pkm-pd.DateOffset(months=lead); w1=trm+pd.DateOffset(months=tail)
        def avail(ch): return [(nm,s) for nm,s in ch if s.index.min()<=w0 and s.index.max()>=trm]
        use=avail(core)
        if len(use)<minch:
            wide=avail(allch)
            if len(wide)>len(use): use=wide
        if not use: use=[(nm,s) for nm,s in allch if s.index.min()<=trm and s.index.max()>=trm]
        if not use: use=allch
        if cpt=='diffusion':
            d=date_diffusion_panel(use,w0,w1); b=date_any(country,use,w0,w1,**kw)
            pk=d['peak'] if d['peak'] is not None else b['peak']
            tr=d['trough'] if d['trough'] is not None else b['trough']
        elif cpt=='growth':
            b=date_any(country,use,w0,w1,min_depth=1e9,**{k:v for k,v in kw.items() if k!='min_depth'})
            pk,tr=b['peak'],b['trough']
        else:
            b=date_any(country,use,w0,w1,**kw); pk,tr=b['peak'],b['trough']
        a,ep=hit(pk,pk_off,freq); c,et=hit(tr,tr_off,freq)
        rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=len(use),
                         pk=pk,tr=tr,ep=ep,et=et,hp=a,ht=c))
    return rows

for minch in [0,3,4,5,6]:
    tot=[]
    for c in ALL: tot+=run_country_thin(c,minch,**K)
    s=score(tot,'',show=False)
    line=f'minch={minch}  peak {s["hp"]}/80  trough {s["ht"]}/80'
    per=[]
    for c in ALL:
        x=score([r for r in tot if r['country']==c],'',show=False)
        per.append(f'{c[:4]} {x["hp"]}/{x["ht"]}')
    print(line,' | ',' '.join(per))
