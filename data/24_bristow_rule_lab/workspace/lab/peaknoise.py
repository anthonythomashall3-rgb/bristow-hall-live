"""A fall smaller than the channel's own month-to-month variation is not a turn.
Abstain at the peak when the fall from the high to the subsequent low is below
kappa standard deviations of the channel's own monthly changes."""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np, collections
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
_orig=bench.ch_peak
KAP=[0.0]
def ch_peak_k(level,w0,w1,band=0.02,n=3,tadj=False,win=120,minp=60,abstain=None,where=None):
    _ab=bench.ABSTAIN if abstain is None else abstain
    if _ab and KAP[0]>0:
        lv=bench.prep(level,n,tadj,win,minp)
        m=bench.ma(lv,n)[w0:w1].dropna()
        if len(m)>=6:
            hi=float(m.max()); i=m.idxmax()
            lo=float(m[i:].min()) if len(m[i:]) else float(m.min())
            sd=float(m.diff().std())
            if np.isfinite(sd) and sd>0 and (hi-lo) < KAP[0]*sd: return None
    return _orig(level,w0,w1,band,n,tadj,win,minp,abstain,where)
bench.ch_peak=ch_peak_k
CAND=[0.0,1.0,2.0,3.0,4.0,6.0]
res={}
for k in CAND:
    KAP[0]=k; bench._DEV.clear()
    t=[]
    for c in ALL: t+=run_country_concept(c,**K)
    res[k]=t
    s=score(t,'',show=False)
    mo=[r for r in t if PANELS[r['country']]['freq']=='M']
    mep=[abs(r['ep']) for r in mo if r['ep'] is not None]; met=[abs(r['et']) for r in mo if r['et'] is not None]
    print(f'kappa={k}:  peak {s["hp"]}/83 trough {s["ht"]}/83  monthly MAD {np.mean(mep):.2f}/{np.mean(met):.2f}'
          f'  w2 {sum(1 for x in mep if x<=2)},{sum(1 for x in met if x<=2)}')
def sc(rows,c): return sum(x['hp']+x['ht'] for x in rows if x['country']==c)
def w2(rows,c):
    r=[x for x in rows if x['country']==c]
    return (sum(1 for x in r if x['ep'] is not None and abs(x['ep'])<=2)
           +sum(1 for x in r if x['et'] is not None and abs(x['et'])<=2))
picks=collections.Counter(); oos=0
for c in ALL:
    best=max(CAND,key=lambda k:(sum(sc(res[k],o) for o in ALL if o!=c),
                                sum(w2(res[k],o) for o in ALL if o!=c),-k))
    picks[best]+=1; oos+=sc(res[best],c)
print('LOCO picks:',dict(picks),' out-of-sample total',oos,' shipped in sample',sum(sc(res[0.0],c) for c in ALL))
