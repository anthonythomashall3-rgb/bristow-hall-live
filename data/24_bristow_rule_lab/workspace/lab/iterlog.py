"""Two structural variants not yet tried.

ITERATE   the peak is searched over a window ending at the trough, so the trough is
          found first.  But the trough's own window starts at w0, not at the peak.
          Iterating - date the trough, date the peak, re-date the trough from the
          peak forward, repeat - lets each end use the other.
LOGS      the band is a fraction of the peak-to-trough amplitude, measured on the
          level.  Measuring it on the log level makes the band proportional rather
          than absolute, which matters when a series has grown a lot inside the
          window.
"""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
from w2 import w2
import numpy as np, pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)

# --- LOGS: run the whole rule on log levels
_origload=None
def run_logs():
    import copy
    cache={}
    orig_ma=bench.ma
    def ma2(x,n):
        k=(id(x),n); e=cache.get(k)
        if e is not None and e[0] is x: return e[1]
        r=np.log(x.clip(lower=1e-9)).rolling(n).mean(); cache[k]=(x,r); return r
    bench.ma=ma2
    try:
        tot=[]
        for c in ALL: tot+=run_country_concept(c,**K)
        return tot
    finally:
        bench.ma=orig_ma

# --- ITERATE
def run_iter(rounds=2):
    tot=[]
    for c in ALL:
        cfg=PANELS[c]; chs=[(nm,s) for nm,s in channels(c) if nm not in bench.SKIP]
        cpt=CONCEPT.get(c,'level')
        for _e in cfg['chrono']:
            pk_off,tr_off,freq=ep3(_e,cfg['freq'])
            pkm=ts(pk_off) if freq=='M' else q2m(pk_off); trm=ts(tr_off) if freq=='M' else q2m(tr_off)
            w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
            r=run_country_concept(c,**K)  # placeholder, replaced below
            break
        break
    # simpler: re-run with an inner iteration on the level route only
    for c in ALL:
        cfg=PANELS[c]; chs=[(nm,s) for nm,s in channels(c) if nm not in bench.SKIP]
        rows=run_country_concept(c,**K)
        i=0
        for _e in cfg['chrono']:
            pk_off,tr_off,freq=ep3(_e,cfg['freq'])
            r=rows[i]; i+=1
            pkm=ts(pk_off) if freq=='M' else q2m(pk_off); trm=ts(tr_off) if freq=='M' else q2m(tr_off)
            w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
            use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
            if not use or CONCEPT.get(c)!='level' or dating_series(c,w0,trm) is not None:
                tot.append(r); continue
            pk,tr=r['pk'],r['tr']
            for _ in range(rounds):
                if pk is None: break
                dt=[ch_trough(s,pk,w1,0.12,3,12,abstain=True) for nm,s in use]
                db=[ch_trough(s,pk,w1,0.12,3,12,abstain=False) for nm,s in use]
                tr2=med_fallback(dt,db)
                if tr2 is None: break
                dp=[ch_peak(s,w0,tr2,0.01,3,abstain=True) for nm,s in use]
                dq=[ch_peak(s,w0,tr2,0.01,3,abstain=False) for nm,s in use]
                pk2=med_fallback(dp,dq)
                if pk2 is None or (pk2==pk and tr2==tr): pk,tr=pk2 or pk,tr2; break
                pk,tr=pk2,tr2
            a,ep=hit(pk,pk_off,freq); b,et=hit(tr,tr_off,freq)
            tot.append(dict(country=c,peak_off=pk_off,tr_off=tr_off,nch=len(use),pk=pk,tr=tr,
                            ep=ep,et=et,hp=a,ht=b))
    return tot

for tag,fn in (('shipped',lambda: [r for c in ALL for r in run_country_concept(c,**K)]),
               ('log levels',run_logs),
               ('iterate peak and trough',run_iter)):
    tot=fn()
    a,na,b,nb,ma_,mb,sa,sb=w2(tot); s=score(tot,'',show=False)
    print(f'{tag:26s} within2 {a}+{b}={a+b}  hits {s["hp"]}/{s["ht"]}  MAE {ma_:.2f}/{mb:.2f}')
