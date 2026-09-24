"""The monthly detectors, tuned only on 1973-1982, run over the whole record 1971-2026.
Everything from 1986 on is out of sample for these settings."""
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
exec(open('/home/claude/lab/dol/mcall2.py').read().split('bp=None')[0])
PKA={'1973-11':'NBER','1980-01':'NBER','1981-07':'NBER','1990-07':'NBER','2001-03':'NBER',
     '2007-12':'NBER','2020-02':'NBER','2023-06':'Paper 1 rolling onset'}
TRA={'1975-03':'NBER','1980-07':'NBER','1982-11':'NBER','1991-03':'NBER','2001-11':'NBER',
     '2009-06':'NBER','2020-04':'NBER','2026-05':'Paper 1 rolling end'}
P=peak_calls(breadth(2,24,30.),50.,40.,1,2)
T=trough_calls(natgap(1,18),1,1.,50.,15.,3)
def show(calls,T_,label):
    hits={}; fa=[]
    print(f'--- {label}')
    for pub,dt in calls:
        if pub<pd.Timestamp('1973-01-01'): continue
        near=min(T_,key=lambda k: abs(md(dt,pd.Timestamp(k+'-01'))))
        lag=md(pub,pd.Timestamp(near+'-01')); err=md(dt,pd.Timestamp(near+'-01'))
        ok=abs(lag)<=2 and abs(err)<=2 and near not in hits
        if ok: hits[near]=(lag,err)
        else: fa.append((pub,dt,near,lag,err))
        print(f'   {"HIT " if ok else "miss"} pub {pub:%Y-%m} dated {dt:%Y-%m}  vs {near} '
              f'({T_[near]})  lag {lag:+3d} err {err:+3d}')
    miss=[k for k in T_ if k not in hits]
    print(f'   -> {len(hits)}/{len(T_)} hit, {len(fa)} other calls; never called: {miss}')
    return hits,fa
show(P,PKA,'PEAK calls, settings tuned on 1973-1982 only')
show(T,TRA,'TROUGH calls, settings tuned on 1973-1982 only')
