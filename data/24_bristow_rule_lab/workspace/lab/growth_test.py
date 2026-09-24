import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd, numpy as np
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True

def growth_dates(chs,w0,w1,mode,lam=500000.,n=3,L=12,band_t=0.03,band_p=0.02):
    q=quantity('Korea',chs) or chs
    cy=cyc_hp(q,lam,n)
    if cy is None: return None,None
    m=cy[w0:w1].dropna()
    if len(m)<6: return None,None
    if mode=='maxswing':
        v=m.values; idx=m.index
        best=None; runmax=0
        for j in range(1,len(v)):
            if v[j-1]>v[runmax]: runmax=j-1
            d=v[runmax]-v[j]
            if best is None or d>best[0]: best=(d,runmax,j)
        if best is None: return None,None
        return idx[best[1]], idx[best[2]]
    if mode=='extremum':
        tr=m.idxmin(); pre=m[:tr]
        pk=pre.idxmax() if len(pre)>1 else m.idxmax()
        return pk,tr
    if mode=='band0':
        tr=ch_trough(cy,w0,w1,0.0,1,L,abstain=False)
        gend=tr if tr is not None else w1
        pk=ch_peak(cy,w0,gend,0.0,1,abstain=False)
        return pk,tr
    tr=ch_trough(cy,w0,w1,band_t,1,L,abstain=False)
    gend=tr if tr is not None else w1
    pk=ch_peak(cy,w0,gend,band_p,1,abstain=False)
    return pk,tr

ORIG=list(PANELS['Korea']['ch'])
for panel_tag,ch in [('base',ORIG),('+IMF',ORIG+imf('KOR'))]:
    PANELS['Korea']['ch']=ch; bench._cache.pop('Korea',None)
    chs=[(nm,s) for nm,s in channels('Korea') if nm not in bench.SKIP]
    for mode in ['current','band0','extremum','maxswing']:
        for lam in [129600.,500000.]:
            hp=ht=0; det=[]
            for pk_off,tr_off in KR_M:
                pkm=ts(pk_off); trm=ts(tr_off)
                w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
                use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
                if not use: use=[(nm,s) for nm,s in chs if s.index.min()<=trm and s.index.max()>=trm]
                if not use: use=chs
                pk,tr=growth_dates(use,w0,w1,mode,lam=lam)
                a,_=hit(pk,pk_off,'M'); b,_=hit(tr,tr_off,'M')
                hp+=a; ht+=b
                det.append((pk_off,tr_off,pk.strftime('%Y-%m') if pk is not None else '--',
                            tr.strftime('%Y-%m') if tr is not None else '--',a,b))
            print(f'{panel_tag:5s} {mode:9s} lam={lam:8.0f}  peak {hp:2d}/11  trough {ht:2d}/11')
            if mode=='maxswing' and lam==500000.:
                for d in det: print('        ',d)
PANELS['Korea']['ch']=ORIG; bench._cache.pop('Korea',None)
