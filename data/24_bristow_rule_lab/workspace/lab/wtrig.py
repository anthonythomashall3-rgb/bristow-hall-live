"""A real-time caller on weekly claims, for BOTH ends.

Activity proxy A(t) = -log(4-week mean of seasonally adjusted initial claims): claims are
counter-cyclical, so the negative log is a pro-cyclical activity index, and the Bristow
deviation statistic on it is the same object Paper 1 computes on the unemployment rate.

  PEAK   D(t) = (trailing max of A over L weeks) - A(t), in log points x100, first
         crosses theta_p and stays above it for r_p weeks.  The peak is the month in
         which A last stood at that trailing maximum.
  TROUGH after a peak call, D reaches its own maximum and then falls for r_t weeks.
         The trough is the month in which D peaked.
Data for week W is published the following Thursday, so a call made on week W is
publishable in the month containing W + 7 days.
"""
import sys; sys.path.insert(0,'/home/claude/lab')
import pandas as pd, numpy as np, itertools
C=pd.read_csv('/home/claude/lab/dol/US_weekly_claims_sa.csv',index_col=0,parse_dates=True)
A=-np.log(C['initial_claims'].rolling(4).mean().dropna())*100.0
PK=['1990-07','2001-03','2007-12','2020-02']
TR=['1991-03','2001-11','2009-06','2020-04']
def mo(ts): return pd.Timestamp(ts.year,ts.month,1)
def md(a,b): return (a.year-b.year)*12+(a.month-b.month)
def run(L,thp,rp,rt,pub=7):
    """Walk forward one week at a time; never look ahead."""
    calls=[]; state='expansion'; armed_from=A.index[L]
    hi_at=None
    for i in range(L,len(A)):
        t=A.index[i]
        w=A.iloc[max(0,i-L):i+1]
        hi=w.max(); hi_i=w.idxmax()
        D=(hi-A.iloc[i])
        if state=='expansion':
            seg=A.iloc[max(0,i-rp+1):i+1]
            hs=[(A.iloc[max(0,j-L):j+1].max()-A.iloc[j]) for j in range(max(L,i-rp+1),i+1)]
            if len(hs)>=rp and all(x>=thp for x in hs):
                calls.append(('peak', t+pd.Timedelta(days=pub), mo(hi_i)))
                state='contraction'; dmax=D; dmax_at=t; fall=0
        else:
            if D>dmax: dmax=D; dmax_at=t; fall=0
            elif D<prevD: fall+=1
            else: fall=0
            if fall>=rt:
                calls.append(('trough', t+pd.Timedelta(days=pub), mo(dmax_at)))
                state='expansion'
        prevD=D
    return calls
def score(calls):
    got={}; extra=0
    for kind,pub,dt in calls:
        tgt=PK if kind=='peak' else TR
        best=None
        for k in tgt:
            e=md(dt,pd.Timestamp(k+'-01'))
            if abs(e)<=6 and k not in got:
                if best is None or abs(e)<abs(best[1]): best=(k,e)
        if best: got[best[0]]=(pub,best[1],dt)
        else: extra+=1
    return got,extra
best=[]
for L,thp,rp,rt in itertools.product((26,39,52,78),(4.,6.,8.,10.,12.),(2,3,4,6),(4,6,8,12)):
    got,extra=score(run(L,thp,rp,rt))
    npk=sum(1 for k in PK if k in got); ntr=sum(1 for k in TR if k in got)
    if npk+ntr==0: continue
    lags=[md(mo(v[0]),pd.Timestamp(k+'-01')) for k,v in got.items()]
    errs=[abs(v[1]) for v in got.values()]
    best.append((npk+ntr,-extra,-max(lags),-max(errs),L,thp,rp,rt,np.mean(lags),max(lags),np.mean(errs),max(errs),extra))
best.sort(reverse=True)
print(f'{"P":>2s} {"T":>2s} {"L":>3s} {"th":>5s} {"rp":>3s} {"rt":>3s} {"lag mean":>9s} {"lag max":>8s} {"err mean":>9s} {"err max":>8s} {"extra":>6s}')
for b in best[:15]:
    print(f'{b[0]:2d}/8      {b[4]:3d} {b[5]:5.1f} {b[6]:3d} {b[7]:3d} {b[8]:9.2f} {b[9]:8d} {b[10]:9.2f} {b[11]:8d} {b[12]:6d}')
