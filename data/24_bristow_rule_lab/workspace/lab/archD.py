import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)

def date_D(country,chs,w0,w1,band_t=0.12,band_p=0.01,n=3,L=12,peak_cap=18,
           min_depth=5.0,lam=500000.,growth_force=False):
    """Architecture D inside the same cascade: date the cross-channel median level."""
    q=quantity(country,chs) or chs
    deepest=None
    for nm,s in q:
        m=ma(s,n)[w0:w1].dropna(); d=maxdd(m)
        if d is not None and (deepest is None or d<deepest): deepest=d
    growth = growth_force or deepest is None or deepest > -abs(min_depth)
    z=norm_med(chs,w0-pd.DateOffset(months=L),w1,n)
    l_pk=l_tr=None
    if z is not None and len(z)>=8:
        l_tr=ch_trough(z,w0,w1,band_t,1,L,abstain=False)
        end=l_tr if l_tr is not None else w1
        d=dev(z,L,1)[w0:end].dropna(); cross=None
        for dd,v in d.items():
            if v>=2.0: cross=dd; break
        p0=w0 if cross is None else max(w0,cross-pd.DateOffset(months=peak_cap))
        l_pk=ch_peak(z,p0,end,band_p,1,abstain=False)
    ref=None
    for _nm,_s in chs:
        if _nm=='monthly reference GDP': ref=_s; break
    g_pk=g_tr=None
    if ref is not None and len(ma(ref,n)[w0:w1].dropna())>=6:
        g_tr=ch_trough(ref,w0,w1,0.0,n,L,abstain=False)
        gend=g_tr if g_tr is not None else w1
        g_pk=ch_peak(ref,w0,gend,band_p,n,abstain=False)
    else:
        cy=cyc_hp(q,lam,n)
        if cy is not None and len(cy[w0:w1].dropna())>=6:
            g_tr=ch_trough(cy,w0,w1,0.0,1,L,abstain=False)
            gend=g_tr if g_tr is not None else w1
            g_pk=ch_peak(cy,w0,gend,band_p,1,abstain=False)
    pk,tr=(g_pk,g_tr) if growth else (l_pk,l_tr)
    if pk is None: pk=l_pk if growth else g_pk
    if tr is None: tr=l_tr if growth else g_tr
    if pk is not None and tr is not None and pk>tr: pk,tr=tr,pk
    return pk,tr

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
        pk,tr=date_D(c,use,w0,w1,growth_force=(cpt=='growth'))
        if cpt=='diffusion':
            d=date_diffusion_panel(use,w0,w1)
            if d['peak'] is not None: pk=d['peak']
            if d['trough'] is not None: tr=d['trough']
        a,ep=hit(pk,pk_off,freq); b,et=hit(tr,tr_off,freq)
        tot.append(dict(country=c,hp=a,ht=b,nch=len(use),ep=ep,et=et))
s=score(tot,'',show=False)
print(f'architecture D inside the same cascade: peak {s["hp"]}/83 trough {s["ht"]}/83')
print('shipped (architecture A):              peak 75/83 trough 72/83')
