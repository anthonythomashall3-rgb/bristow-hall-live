import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd
CORE={'exports','imports','car registrations','unemployment','construction production',
      'construction output','capital goods production','intermediate goods production',
      'consumer durables production'}
bench.SKIP=CORE; bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.)
ORIG=list(PANELS['Japan']['ch'])
IMFJP=[('IMF industrial production','/home/claude/lab/imf/JPN_IND_IX.csv','level')]

def run_dw(country, wide_diffusion, lead=12, tail=12, **kw):
    cfg=PANELS[country]; allch=channels(country)
    core=[(nm,s) for nm,s in allch if nm not in CORE]
    cpt=CONCEPT.get(country,'level'); rows=[]
    for _e in cfg['chrono']:
        pk_off,tr_off,freq=ep3(_e,cfg['freq'])
        pkm=ts(pk_off) if freq=='M' else q2m(pk_off); trm=ts(tr_off) if freq=='M' else q2m(tr_off)
        w0=pkm-pd.DateOffset(months=lead); w1=trm+pd.DateOffset(months=tail)
        def av(ch):
            u=[(nm,s) for nm,s in ch if s.index.min()<=w0 and s.index.max()>=trm]
            if not u: u=[(nm,s) for nm,s in ch if s.index.min()<=trm and s.index.max()>=trm]
            return u or ch
        use=av(core); wide=av(allch)
        if cpt=='diffusion':
            d=date_diffusion_panel(wide if wide_diffusion else use,w0,w1)
            b=date_any(country,use,w0,w1,**kw)
            pk=d['peak'] if d['peak'] is not None else b['peak']
            tr=d['trough'] if d['trough'] is not None else b['trough']
        elif cpt=='growth':
            b=date_any(country,use,w0,w1,min_depth=1e9,**{k:v for k,v in kw.items() if k!='min_depth'})
            pk,tr=b['peak'],b['trough']
        else:
            b=date_any(country,use,w0,w1,**kw); pk,tr=b['peak'],b['trough']
        a,ep=hit(pk,pk_off,freq); c,et=hit(tr,tr_off,freq)
        rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=len(use),hp=a,ht=c,ep=ep,et=et,pk=pk,tr=tr))
    return rows

for panel_tag,ch in [('base',ORIG),('+IMF',ORIG+IMFJP)]:
  PANELS['Japan']['ch']=ch; bench._cache.pop('Japan',None)
  for wd in (False,True):
    tot=[]
    for c in ALL: tot+=run_dw(c,wd,**K)
    s=score(tot,'',show=False)
    j=score([r for r in tot if r['country']=='Japan'],'',show=False)
    print(f'{panel_tag:5s} wide_diffusion={str(wd):5s}  ALL peak {s["hp"]}/80 trough {s["ht"]}/80   Japan {j["hp"]}/16 {j["ht"]}/16')
    if wd and panel_tag=='+IMF':
        for x in [r for r in tot if r['country']=='Japan']:
            pk=x['pk'].strftime('%Y-%m') if x['pk'] is not None else '--'
            tr=x['tr'].strftime('%Y-%m') if x['tr'] is not None else '--'
            print(f"     {x['peak_off']}->{x['tr_off']}  {pk}/{tr}  {'P' if x['hp'] else '-'}{'T' if x['ht'] else '-'}")
PANELS['Japan']['ch']=ORIG; bench._cache.pop('Japan',None)
