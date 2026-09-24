import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np
bench.ABSTAIN=True; bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set()
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
K=dict(min_depth=5.0,lam=500000.)

def run_disc(country, G=None, S=None, lead=12, tail=12, **kw):
    """Route to the diffusion estimator when the trend gap is more than G times the
    level fall AND the channels' own dates span more than S months - both observable
    when the date is made."""
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
        q=quantity(country,use) or use
        base=date_any(country,use,w0,w1,**{**K,**kw})
        pk,tr,v=base['peak'],base['trough'],base['verdict']
        if cpt=='growth':
            g=date_any(country,use,w0,w1,**{**K,**kw,'min_depth':1e9}); pk,tr=g['peak'] or pk,g['trough'] or tr; v='growth'
        elif cpt=='diffusion':
            d=date_diffusion_panel(use,w0,w1)
            pk,tr=d['peak'] or pk, d['trough'] or tr; v='diffusion'
        elif G is not None:
            ci=composite_level(q); m=ma(ci,3)[w0:w1].dropna()
            cdep=maxdd(m) or 0
            try: cyd=maxdd(cyc_hp(q,500000.,3)[w0:w1].dropna()) or 0
            except Exception: cyd=0
            gr=cyd/(cdep-1e-9) if cdep<0 else 9.9
            sp=max(base['spread_peak'] or 0, base['spread_trough'] or 0)
            if gr>G and sp>S:
                d=date_diffusion_panel(use,w0,w1)
                if d['peak'] is not None: pk=d['peak']
                if d['trough'] is not None: tr=d['trough']
                v='diffusion (gap rule)'
        a,ep=hit(pk,pk_off,freq); b,et=hit(tr,tr_off,freq)
        rows.append(dict(country=country,peak_off=pk_off,tr_off=tr_off,nch=len(use),pk=pk,tr=tr,
                         ep=ep,et=et,hp=a,ht=b,depth=None,sp=None,st=None,verdict=v))
    return rows

print(f'{"G (gap ratio)":>14s} {"S (spread)":>11s}   {"peak":>9s} {"trough":>9s}  sum')
base=[]
for c in ALL: base+=run_country_concept(c,**K)
s=score(base,'',show=False); print(f'{"no gap rule":>14s} {"":>11s}   {s["hp"]:4d}/{s["n"]:<4d} {s["ht"]:4d}/{s["n"]:<4d}  {s["hp"]+s["ht"]}')
res=[]
for G in [2.5,3.0,4.0,5.0]:
    for S in [8,12,16,20]:
        tot=[]
        for c in ALL: tot+=run_disc(c,G=G,S=S)
        s=score(tot,'',show=False)
        res.append((s['hp']+s['ht'],G,S))
        print(f'{G:14.1f} {S:11d}   {s["hp"]:4d}/{s["n"]:<4d} {s["ht"]:4d}/{s["n"]:<4d}  {s["hp"]+s["ht"]}')
res.sort(reverse=True); print('\nbest:',res[0])
