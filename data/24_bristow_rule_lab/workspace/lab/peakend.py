import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.)

def date_pe(country,chs,w0,w1,mode,band_t=0.03,band_p=0.02,n=3,L=12,peak_cap=12,
            min_depth=5.0,lam=500000.):
    q=quantity(country,chs) or chs
    deepest=None
    for nm,s in q:
        m=ma(s,n)[w0:w1].dropna(); d=maxdd(m)
        if d is not None and (deepest is None or d<deepest): deepest=d
    growth = deepest is None or deepest > -abs(min_depth)
    ch_t=chs; ch_p=chs
    dt_a=[ch_trough(s,w0,w1,band_t,n,L,abstain=True) for nm,s in ch_t]
    dt_b=[ch_trough(s,w0,w1,band_t,n,L,abstain=False) for nm,s in ch_t]
    l_tr=med_fallback(dt_a,dt_b)
    end=l_tr if l_tr is not None else w1
    comp=composite_dev(chs,L,n,1)[w0:end].dropna(); cross=None
    for d_,v in comp.items():
        if v>=2.0: cross=d_; break
    p0=w0 if (cross is None or peak_cap is None) else max(w0,cross-pd.DateOffset(months=peak_cap))
    if mode=='cross' and cross is not None: pend=cross
    elif mode=='cross6' and cross is not None: pend=cross+pd.DateOffset(months=6)
    elif mode=='mid' and cross is not None: pend=min(end, cross+pd.DateOffset(months=12))
    else: pend=end
    dp_a=[ch_peak(s,p0,pend,band_p,n,abstain=True) for nm,s in ch_p]
    dp_b=[ch_peak(s,p0,pend,band_p,n,abstain=False) for nm,s in ch_p]
    l_pk=med_fallback(dp_a,dp_b)
    ref=None
    for _nm,_s in chs:
        if _nm=='monthly reference GDP': ref=_s; break
    g_pk=g_tr=None
    if ref is not None and len(ma(ref,n)[w0:w1].dropna())>=6:
        g_tr=ch_trough(ref,w0,w1,0.0,n,L,abstain=False)
        gend=g_tr if g_tr is not None else w1
        g_pk=ch_peak(ref,w0,gend,band_p,n,abstain=False)
    pk,tr=(g_pk,g_tr) if growth else (l_pk,l_tr)
    if pk is None: pk=l_pk if growth else g_pk
    if tr is None: tr=l_tr if growth else g_tr
    if pk is None or tr is None:
        ci=composite_level(q); m=ma(ci,n)[w0:w1].dropna()
        if len(m)>=4:
            if tr is None: tr=m.idxmin()
            if pk is None:
                pre=m[:tr] if tr is not None else m
                pk=(pre.idxmax() if len(pre)>1 else m.idxmax())
    if pk is not None and tr is not None and pk>tr: pk,tr=tr,pk
    return pk,tr

for mode in ['trough','cross','cross6','mid']:
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
            if cpt=='diffusion':
                d=date_diffusion_panel(use,w0,w1)
                bpk,btr=date_pe(c,use,w0,w1,mode,**K)
                pk=d['peak'] if d['peak'] is not None else bpk
                tr=d['trough'] if d['trough'] is not None else btr
            elif cpt=='growth':
                pk,tr=date_pe(c,use,w0,w1,mode,min_depth=1e9,lam=K['lam'])
            else:
                pk,tr=date_pe(c,use,w0,w1,mode,**K)
            a,ep=hit(pk,pk_off,freq); b,et=hit(tr,tr_off,freq)
            tot.append(dict(country=c,hp=a,ht=b,ep=ep,et=et,nch=len(use)))
    s=score(tot,'',show=False)
    per=' '.join(f'{c[:4]} {score([r for r in tot if r["country"]==c],"",show=False)["hp"]}/{score([r for r in tot if r["country"]==c],"",show=False)["ht"]}' for c in ALL)
    print(f'{mode:8s} peak {s["hp"]}/80 trough {s["ht"]}/80  | {per}')
