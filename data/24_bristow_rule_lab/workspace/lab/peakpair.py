"""A partner clause for the peak, mirroring clause (a) at the trough.

At the trough the rule takes the LATER of the deviation statistic's maximum and the
plateau.  The peak has no such partner.  The natural mirror is the month before the
deviation statistic first clears a small threshold - the last month before activity
has visibly begun to fall - and the peak would then be the EARLIER of that and the
plateau.
"""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
from w2 import w2
import pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
orig_peak=bench.ch_peak
def make(thr):
    def ch_peak2(level,w0,w1,band=0.02,n=3,tadj=False,win=120,minp=60,abstain=None,where=None):
        p=orig_peak(level,w0,w1,band,n,tadj,win,minp,abstain,where)
        if p is None or thr is None: return p
        d=bench.dev(level,12,n)[w0:w1].dropna()
        first=None
        for t,v in d.items():
            if v>=thr: first=t; break
        if first is None: return p
        cand=d.index[max(0,list(d.index).index(first)-1)]
        return min(p,cand)
    return ch_peak2
for thr in (None,0.5,1.0,2.0,3.0):
    bench.ch_peak=make(thr)
    tot=[]
    for c in ALL: tot+=run_country_concept(c,**K)
    a,na,b,nb,ma_,mb,sa,sb=w2(tot); s=score(tot,'',show=False)
    print(f'peak partner threshold {str(thr):5s}  within2 {a}+{b}={a+b}  hits {s["hp"]}/{s["ht"]}  MAE {ma_:.2f}/{mb:.2f}  bias {sa:+.2f}')
bench.ch_peak=orig_peak
