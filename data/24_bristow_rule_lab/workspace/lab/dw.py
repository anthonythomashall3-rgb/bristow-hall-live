import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
bench.ABSTAIN=True
CORE={'exports','imports','car registrations','unemployment','construction production',
      'construction output','capital goods production','intermediate goods production',
      'consumer durables production'}
bench.SKIP=CORE; bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set()

def run_width(country, dmin=99, cap=12, lead=12, tail=12, **kw):
    """Use the diffusion estimator when the panel has at least dmin channels."""
    cfg=PANELS[country]; chs=[(nm,s) for nm,s in channels(country) if nm not in SKIP]
    cpt=CONCEPT.get(country,'level')
    rows=[]
    for _e in cfg['chrono']:
        pk_off,tr_off,freq=ep3(_e,cfg['freq'])
        pkm=ts(pk_off) if freq=='M' else q2m(pk_off); trm=ts(tr_off) if freq=='M' else q2m(tr_off)
        w0=pkm-pd.DateOffset(months=lead); w1=trm+pd.DateOffset(months=tail)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
        if not use: use=[(nm,s) for nm,s in chs if s.index.min()<=trm and s.index.max()>=trm]
        if not use: use=[(nm,s) for nm,s in chs if s.index.min()<=w1 and s.index.max()>=w0]
        if not use:
            rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=0,pk=None,tr=None,
                             ep=None,et=None,hp=False,ht=False,depth=None,sp=None,st=None,verdict='no data')); continue
        base=date_any(country,use,w0,w1,peak_cap=cap,**kw)
        pk,tr=base['peak'],base['trough']
        if cpt=='diffusion' or (cpt=='level' and len(use)>=dmin):
            d=date_diffusion_panel(use,w0,w1)
            if d['peak'] is not None: pk=d['peak']
            if d['trough'] is not None: tr=d['trough']
        elif cpt=='growth':
            g=date_any(country,use,w0,w1,peak_cap=cap,**{**kw,'min_depth':1e9})
            pk,tr=g['peak'] or pk, g['trough'] or tr
        a,ep=hit(pk,pk_off,freq); b,et=hit(tr,tr_off,freq)
        rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=len(use),pk=pk,tr=tr,
                         ep=ep,et=et,hp=a,ht=b,depth=None,sp=None,st=None,verdict='w'))
    return rows

print(f'{"diffusion when nch >=":22s} {"cap":>4s}  {"peak":>9s} {"trough":>9s}  sum')
for dmin in [99,4,5,6,7,8,9,10]:
    for cap in [9,12]:
        tot=[]
        for c in ALL: tot+=run_width(c,dmin=dmin,cap=cap,min_depth=5.0,lam=500000.)
        s=score(tot,'',show=False)
        tag='never' if dmin==99 else str(dmin)
        print(f'{tag:22s} {cap:4d}  {s["hp"]:4d}/{s["n"]:<4d} {s["ht"]:4d}/{s["n"]:<4d}  {s["hp"]+s["ht"]}')
