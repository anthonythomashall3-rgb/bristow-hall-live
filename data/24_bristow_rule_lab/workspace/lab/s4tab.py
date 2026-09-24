import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(band_t=0.03,band_p=0.01,peak_cap=18,n=3,L=12,min_depth=5.0,lam=500000.)
def run(c,mode):
    cfg=PANELS[c]; chs=[(nm,s) for nm,s in channels(c) if nm not in bench.SKIP]
    hp=ht=0
    for _e in cfg['chrono']:
        pk_off,tr_off,freq=ep3(_e,cfg['freq'])
        pkm=ts(pk_off); trm=ts(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
        if not use: use=[(nm,s) for nm,s in chs if s.index.min()<=trm and s.index.max()>=trm]
        if not use: use=chs
        q=quantity(c,use) or use
        pk=tr=None
        if mode=='level':
            b=date_any(c,use,w0,w1,**K); pk,tr=b['peak'],b['trough']
        elif mode=='cyc_band':
            cy=cyc_hp(q,K['lam'],K['n'])
            if cy is not None and len(cy[w0:w1].dropna())>=6:
                tr=ch_trough(cy,w0,w1,K['band_t'],1,K['L'],abstain=False)
                pk=ch_peak(cy,w0,tr if tr is not None else w1,K['band_p'],1,abstain=False)
        elif mode=='ref0':
            ref=next((s for nm,s in use if nm=='monthly reference GDP'),None)
            if ref is not None:
                tr=ch_trough(ref,w0,w1,0.0,K['n'],K['L'],abstain=False)
                pk=ch_peak(ref,w0,tr if tr is not None else w1,K['band_p'],K['n'],abstain=False)
        elif mode in ('di_last','di_first'):
            di=hist_di(use,5)
            if di is not None:
                tr=ch_trough(di+1.0,w0,w1,0.30,3,12,abstain=False)
                end=tr if tr is not None else w1
                pk=(di_dates_censored(di,w0,end,45.,1,1)['peak'] if mode=='di_last'
                    else di_peak_first(di,w0,end,45.,4))
                b=date_any(c,use,w0,w1,**K)
                if pk is None: pk=b['peak']
                if tr is None: tr=b['trough']
        hp+=hit(pk,pk_off,'M')[0]; ht+=hit(tr,tr_off,'M')[0]
    return hp,ht
for mode in ('level','cyc_band','ref0','di_last','di_first'):
    j=run('Japan',mode); k=run('Korea',mode)
    print(f'{mode:10s}  Japan {j[0]:2d}/16 {j[1]:2d}/16    Korea {k[0]:2d}/11 {k[1]:2d}/11')
