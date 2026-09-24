import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
bench.ABSTAIN=True; bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set()
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
K=dict(min_depth=5.0,lam=500000.)

def run_r2(country, dmin=0, S=None, lead=12, tail=12, cap=12):
    """dmin: a diffusion chronology falls back to the level estimator when the panel
    has fewer than dmin channels - a diffusion index needs components to mean anything.
    S: a level chronology uses the diffusion estimator when the channels' own dates
    span more than S months."""
    cfg=PANELS[country]; chs=[(nm,s) for nm,s in channels(country) if nm not in SKIP]
    cpt=CONCEPT.get(country,'level'); rows=[]
    for _e in cfg['chrono']:
        pk_off,tr_off,freq=ep3(_e,cfg['freq'])
        pkm=ts(pk_off) if freq=='M' else q2m(pk_off); trm=ts(tr_off) if freq=='M' else q2m(tr_off)
        w0=pkm-pd.DateOffset(months=lead); w1=trm+pd.DateOffset(months=tail)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
        if not use: use=[(nm,s) for nm,s in chs if s.index.min()<=w1 and s.index.max()>=w0]
        if not use:
            rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=0,pk=None,tr=None,
                             ep=None,et=None,hp=False,ht=False,depth=None,sp=None,st=None,verdict='no data')); continue
        base=date_any(country,use,w0,w1,peak_cap=cap,**K)
        pk,tr,v=base['peak'],base['trough'],'level'
        sp=max(base['spread_peak'] or 0, base['spread_trough'] or 0)
        if cpt=='growth':
            g=date_any(country,use,w0,w1,peak_cap=cap,**{**K,'min_depth':1e9})
            pk,tr,v=g['peak'] or pk, g['trough'] or tr,'growth'
        elif cpt=='diffusion':
            if len(use)>=dmin:
                d=date_diffusion_panel(use,w0,w1)
                pk,tr,v=d['peak'] or pk, d['trough'] or tr,'diffusion'
        elif S is not None and sp>S:
            d=date_diffusion_panel(use,w0,w1)
            if d['peak'] is not None: pk=d['peak']
            if d['trough'] is not None: tr=d['trough']
            v='diffusion (wide spread)'
        a,ep=hit(pk,pk_off,freq); b,et=hit(tr,tr_off,freq)
        rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=len(use),pk=pk,tr=tr,
                         ep=ep,et=et,hp=a,ht=b,depth=None,sp=None,st=None,verdict=v))
    return rows

print(f'{"dmin":>5s} {"S":>6s}   {"peak":>9s} {"trough":>9s}  sum')
best=None
for dmin in [0,5,6,7,8,10]:
    for S in [None,16,20,24,30]:
        tot=[]
        for c in ALL: tot+=run_r2(c,dmin=dmin,S=S)
        s=score(tot,'',show=False)
        tag='-' if S is None else str(S)
        print(f'{dmin:5d} {tag:>6s}   {s["hp"]:4d}/{s["n"]:<4d} {s["ht"]:4d}/{s["n"]:<4d}  {s["hp"]+s["ht"]}')
        if best is None or s['hp']+s['ht']>best[0]: best=(s['hp']+s['ht'],dmin,S)
print('\nbest:',best)
