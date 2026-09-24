"""A committee that dates quarters reads quarterly data.  Test: for the quarterly
chronologies, aggregate every monthly channel to quarterly means and date at quarterly
frequency (no monthly smoothing, four-quarter lookback)."""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np, pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
def toq(s):
    r=s.resample('QS').mean()
    return r.dropna()
def run(country,nq,Lq,bt,bp):
    cfg=PANELS[country]; chs=[(nm,s) for nm,s in channels(country) if nm not in bench.SKIP]
    out=[]
    for _e in cfg['chrono']:
        pk_off,tr_off,freq=ep3(_e,cfg['freq'])
        pkm=q2m(pk_off); trm=q2m(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        use=[(nm,toq(s)) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm] or [(nm,toq(s)) for nm,s in chs]
        dt_a=[ch_trough(s,w0,w1,bt,nq,Lq,abstain=True) for nm,s in use]
        dt_b=[ch_trough(s,w0,w1,bt,nq,Lq,abstain=False) for nm,s in use]
        tr=med_fallback(dt_a,dt_b); end=tr if tr is not None else w1
        dp_a=[ch_peak(s,w0,end,bp,nq,abstain=True) for nm,s in use]
        dp_b=[ch_peak(s,w0,end,bp,nq,abstain=False) for nm,s in use]
        pk=med_fallback(dp_a,dp_b)
        a,e1=hit(pk,pk_off,'Q'); b,e2=hit(tr,tr_off,'Q')
        out.append((pk_off,e1,tr_off,e2,a,b))
    return out
print('base (monthly panel, converted to quarters):  Euro P6/6 T5/6   Spain P6/6 T5/6')
for nq in (1,2):
  for Lq in (3,4,5):
    tot=[]
    for c in ('Euro area','Spain','France'):
        tot+=run(c,nq,Lq,0.12,0.01)
    hp=sum(1 for r in tot if r[4]); ht=sum(1 for r in tot if r[5])
    ep=[abs(r[1]) for r in tot if r[1] is not None]; et=[abs(r[3]) for r in tot if r[3] is not None]
    print(f'  nq={nq} Lq={Lq}:  P{hp}/17 T{ht}/17  MAD {np.mean(ep):.2f}/{np.mean(et):.2f} '
          f' exact {sum(1 for x in ep if x==0)},{sum(1 for x in et if x==0)}')
print()
for r in run('Euro area',1,4,0.12,0.01): print('  EZ',r[:4])
for r in run('Spain',1,4,0.12,0.01): print('  ES',r[:4])
