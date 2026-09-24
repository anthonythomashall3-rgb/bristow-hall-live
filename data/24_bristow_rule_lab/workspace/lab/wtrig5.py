"""The Bristow Rule itself, on weekly claims, in real time, at both ends.

Claims are counter-cyclical, so the rule's TROUGH clause on claims dates the peak of
activity and its PEAK clause on claims dates the trough of activity.  Nothing new is
introduced: the same two clauses, the same statistic, weekly periods instead of months.

  ARM     S(t) = K(t) - min K over the trailing L weeks reaches theta, where K is
          100 x log of the smoothed seasonally adjusted claims series.
  PEAK    called when S has held above theta for rp weeks; dated by the low-band clause
          on K over the trailing window.
  TROUGH  called when K has fallen for rt weeks and by delta from its maximum; dated by
          the high-band clause on K since the peak.
  CENSOR  mp weeks minimum between calls.
"""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import ch_trough, ch_peak
import pandas as pd, numpy as np, itertools
C=pd.read_csv('/home/claude/lab/dol/US_weekly_claims_sa.csv',index_col=0,parse_dates=True)
PK=['1990-07','2001-03','2007-12','2020-02']
TR=['1991-03','2001-11','2009-06','2020-04']
def mo(t): return pd.Timestamp(t.year,t.month,1)
def md(x,y): return (x.year-y.year)*12+(x.month-y.month)
def run(K,L,W,thp,rp,rt,delta,band,mp,pub=7):
    k=K.values; idx=K.index; n=len(k)
    S=(k-pd.Series(k,index=idx).rolling(L,min_periods=L//2).min().values)
    calls=[]; state='exp'; last=-10**9; pk_date=None
    kmax=-1e9; fall=0; prev=None
    for i in range(L,n):
        if not np.isfinite(S[i]): continue
        t=idx[i]
        if state=='exp':
            if i-last<mp: continue
            if i-rp+1>=L and all(np.isfinite(S[j]) and S[j]>=thp for j in range(i-rp+1,i+1)):
                w0=idx[max(0,i-W)]
                d=ch_trough(K[w0:t],w0,t,band,1,L,abstain=False)
                if d is None: d=t
                calls.append(('peak',t+pd.Timedelta(days=pub),mo(d)))
                state='con'; last=i; pk_date=d; kmax=k[i]; fall=0; prev=k[i]
        else:
            if k[i]>kmax: kmax=k[i]; fall=0
            elif k[i]<prev: fall+=1
            else: fall=0
            prev=k[i]
            if i-last>=mp and fall>=rt and (kmax-k[i])>=delta:
                d=ch_peak(K[pk_date:t],pk_date,t,band,1,abstain=False)
                if d is None: d=t
                calls.append(('trough',t+pd.Timedelta(days=pub),mo(d)))
                state='exp'; last=i
    return calls
def score(calls,tol=2):
    got={}; false_=0
    for kind,pub,dt in calls:
        tgt=PK if kind=='peak' else TR
        best=None
        for kk in tgt:
            if kk in got: continue
            e=md(dt,pd.Timestamp(kk+'-01'))
            if abs(e)<=tol and (best is None or abs(e)<abs(best[1])): best=(kk,e)
        if best: got[best[0]]=(pub,best[1])
        else: false_+=1
    return got,false_
rows=[]
for nm,sm in (('initial',4),('initial',13),('continued',4),('continued',13)):
    K=(np.log(C[nm+'_claims'].rolling(sm).mean())*100.0).dropna()
    for L,thp,rp,rt,delta,band,mp in itertools.product(
            (52,78,104),(10.,15.,20.),(2,3,4),(4,6,8),(3.,6.),(0.05,0.12,0.25),(26,39)):
        got,fa=score(run(K,L,156,thp,rp,rt,delta,band,mp))
        if len(got)<6: continue
        lags=[md(mo(v[0]),pd.Timestamp(kk+'-01')) for kk,v in got.items()]
        errs=[abs(v[1]) for v in got.values()]
        rows.append((len(got),-max(lags),-fa,nm,sm,L,thp,rp,rt,delta,band,mp,
                     np.mean(lags),max(lags),np.mean(errs),max(errs),fa))
rows.sort(reverse=True)
print(f'{"hit":>4s} {"series":>10s} {"sm":>3s} {"L":>4s} {"th":>5s} {"rp":>3s} {"rt":>3s} {"del":>4s} {"band":>5s} {"mp":>4s} {"lagmu":>6s} {"lagmx":>6s} {"errmu":>6s} {"errmx":>6s} {"false":>6s}')
for b in rows[:20]:
    print(f'{b[0]:2d}/8 {b[3]:>10s} {b[4]:3d} {b[5]:4d} {b[6]:5.1f} {b[7]:3d} {b[8]:3d} {b[9]:4.1f} {b[10]:5.2f} {b[11]:4d} {b[12]:6.2f} {b[13]:6d} {b[14]:6.2f} {b[15]:6d} {b[16]:6d}')
