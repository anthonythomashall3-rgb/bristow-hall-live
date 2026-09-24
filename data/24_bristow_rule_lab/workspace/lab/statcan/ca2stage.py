"""C.D. Howe's own two-step method: quarterly GDP identifies the recession, the monthly
series then fixes the month.  Stage 1 dates the quarter on quarterly real GDP; stage 2
searches the monthly series inside that quarter (and k months either side)."""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np, pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
GQ=pd.read_csv('/home/claude/lab/statcan/CA_gdp_q_long.csv',index_col=0,parse_dates=True)['v']
ch=dict(channels('Canada'))

def qmonths(q, k):
    a=q-pd.DateOffset(months=k); b=q+pd.DateOffset(months=2+k)
    return a,b

def run(k, use_emp):
    rows=[]
    for _e in PANELS['Canada']['chrono']:
        pk_off,tr_off,freq=ep3(_e,'M')
        pkm=ts(pk_off); trm=ts(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        core=None
        for nm in ('monthly GDP','industrial production'):
            s=ch.get(nm)
            if s is not None and s.index.min()<=w0 and s.index.max()>=trm: core=s; break
        emp=ch.get('employment')
        okemp = use_emp and emp is not None and emp.index.min()<=w0 and emp.index.max()>=trm
        if GQ.index.min()<=w0 and GQ.index.max()>=trm and core is not None:
            qt=ch_trough(GQ,w0,w1,K['band_t'],1,4,abstain=False)
            qp=ch_peak(GQ,w0,qt if qt is not None else w1,K['band_p'],1,abstain=False)
            if qp is not None and qt is not None:
                a0,a1=qmonths(qp,k); b0,b1=qmonths(qt,k)
                mp=ma(core,3)[a0:a1].dropna()
                pk=mp.idxmax() if len(mp) else None
                tl=[ma(core,3)[b0:b1].dropna()]
                if okemp: tl.append(ma(emp,3)[b0:b1].dropna())
                tr=med([x.idxmin() for x in tl if len(x)])
                a,ep=hit(pk,pk_off,'M'); b,et=hit(tr,tr_off,'M')
                rows.append((pk_off,tr_off,ep,et,a,b)); continue
        rows.append((pk_off,tr_off,None,None,False,False))
    return rows

for k in (0,1,2):
    for ue in (False,True):
        rs=run(k,ue)
        ok=[r for r in rs if r[2] is not None]
        hp=sum(1 for r in ok if r[4]); ht=sum(1 for r in ok if r[5])
        print(f'k={k} emp={ue}:  {hp}/{len(ok)} peaks {ht}/{len(ok)} troughs   '
              f'MAD {np.mean([abs(r[2]) for r in ok]):.2f}/{np.mean([abs(r[3]) for r in ok]):.2f}')
print()
for r in run(0,True): print('  k=0 emp ',r[:4])
print()
for r in run(0,False): print('  k=0 noemp',r[:4])
