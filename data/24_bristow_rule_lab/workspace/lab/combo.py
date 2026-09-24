import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd, os
CORE={'exports','imports','car registrations','unemployment','construction production',
      'construction output','capital goods production','intermediate goods production',
      'consumer durables production'}
bench.SKIP=CORE; bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.)
IMFDIR='/home/claude/lab/imf'
AREA={'Korea':'KOR','Japan':'JPN','Brazil':'BRA','Canada':'CAN','Spain':'ESP','United States':'USA'}
EAA=['DEU','NLD','BEL','AUT','ITA']
def imfch(a,label=None):
    for code in ('IND_SA_IX','IND_IX'):
        p=f'{IMFDIR}/{a}_{code}.csv'
        if os.path.exists(p): return [(label or 'IMF industrial production',p,'level')]
    return []
ORIG={c:list(PANELS[c]['ch']) for c in ALL}
def setp(which):
    for c in ALL: PANELS[c]['ch']=list(ORIG[c]); bench._cache.pop(c,None)
    if which=='none': return
    for c,a in AREA.items():
        if which=='japan' and c!='Japan': continue
        PANELS[c]['ch']=ORIG[c]+imfch(a); bench._cache.pop(c,None)
    if which=='all':
        add=[]
        for a in EAA: add+=imfch(a,f'{a} IMF production')
        PANELS['Euro area']['ch']=ORIG['Euro area']+add; bench._cache.pop('Euro area',None)

def run_dw(country, wd, lead=12, tail=12, **kw):
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
            d=date_diffusion_panel(wide if wd else use,w0,w1)
            b=date_any(country,use,w0,w1,**kw)
            pk=d['peak'] if d['peak'] is not None else b['peak']
            tr=d['trough'] if d['trough'] is not None else b['trough']
        elif cpt=='growth':
            b=date_any(country,use,w0,w1,min_depth=1e9,**{k:v for k,v in kw.items() if k!='min_depth'})
            pk,tr=b['peak'],b['trough']
        else:
            b=date_any(country,use,w0,w1,**kw); pk,tr=b['peak'],b['trough']
        a,ep=hit(pk,pk_off,freq); c,et=hit(tr,tr_off,freq)
        rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=len(use),hp=a,ht=c,ep=ep,et=et))
    return rows

for which in ('none','japan','panel','all'):
  for wd in (False,True):
    setp('panel' if which=='panel' else which)
    tot=[]
    for c in ALL: tot+=run_dw(c,wd,**K)
    s=score(tot,'',show=False)
    per=' '.join(f'{c[:4]}{score([r for r in tot if r["country"]==c],"",show=False)["hp"]}/{score([r for r in tot if r["country"]==c],"",show=False)["ht"]}' for c in ALL)
    print(f'imf={which:6s} wide_di={str(wd):5s}  peak {s["hp"]}/80 trough {s["ht"]}/80  | {per}')
