"""Which detrended aggregate does Korea's committee behave like?  Test four objects."""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np, pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
ch=dict(channels('Korea'))
def kostat_composite(names):
    """KOSTAT's own construction: symmetric month-on-month change of each component,
    standardised by its own mean absolute change, averaged, then cumulated."""
    cols=[]
    for nm in names:
        s=ch.get(nm)
        if s is None: continue
        g=(s.diff()/((s+s.shift(1))/2.0))*100.0
        m=g.abs().mean()
        if not np.isfinite(m) or m<=0: continue
        cols.append((g/m).rename(nm))
    if not cols: return None
    G=pd.concat(cols,axis=1).mean(axis=1,skipna=True).dropna()
    lvl=(1.0+G/100.0).cumprod()
    return lvl
def ratio_to_trend(s,lam=500000.0):
    y=np.log(s.dropna()); t=pd.Series(hp_filter(y.values,lam),index=y.index)
    return np.exp(y-t)*100.0
OBJ={}
OBJ['OECD RS__T']=load('/home/claude/lab/kei/KOR_RS__T.csv')
comp=kostat_composite(['industrial production','manufacturing production','retail volume',
                       'employment'])
OBJ['KOSTAT-style composite, ratio to trend']=ratio_to_trend(comp) if comp is not None else None
c2=kostat_composite(['industrial production'])
OBJ['industrial production, ratio to trend']=ratio_to_trend(ch['industrial production'])
OBJ['OECD RS__T, ratio to own trend']=ratio_to_trend(OBJ['OECD RS__T'])
for tag,ref in OBJ.items():
    if ref is None: print(tag,'none'); continue
    hp_=ht=0; ep=[]; et=[]; rows=[]
    for _e in PANELS['Korea']['chrono']:
        pk_off,tr_off,freq=ep3(_e,'M')
        pkm=ts(pk_off); trm=ts(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        if ref.index.min()>w0 or ref.index.max()<trm:
            rows.append((pk_off,None,tr_off,None)); continue
        tr=ch_trough(ref,w0,w1,0.0,3,12,abstain=False)
        pk=ch_peak(ref,w0,tr if tr is not None else w1,0.0,3,abstain=False)
        a,e1=hit(pk,pk_off,'M'); b,e2=hit(tr,tr_off,'M')
        hp_+=a; ht+=b
        if e1 is not None: ep.append(abs(e1))
        if e2 is not None: et.append(abs(e2))
        rows.append((pk_off,e1,tr_off,e2))
    print(f'{tag:44s} P{hp_}/11 T{ht}/11 MAD {np.mean(ep):.2f}/{np.mean(et):.2f}  '
          f'w2 {sum(1 for x in ep if x<=2)},{sum(1 for x in et if x<=2)} of {len(ep)}')
    print('     ', ' '.join(f'{r[1]}/{r[3]}' for r in rows))
