"""Weekly claims caller, Sahm form.

K(t) = 100 x log of the four-week mean of seasonally adjusted initial claims.
S(t) = K(t) - min K over the trailing L weeks   (claims are counter-cyclical, so a rise
       in S is a fall in activity: this is Paper 1's D written for a counter-cyclical
       series, which on the unemployment rate is the Sahm indicator).

PEAK   S >= theta for rp consecutive weeks.  The peak is the month of the trailing
       minimum, that is the month claims were lowest before the rise.
TROUGH after a peak call, K reaches a maximum and then falls for rt consecutive weeks
       and by at least delta log points.  The trough is the month K peaked.
Minimum phase mp weeks between calls.  Publication: week + 7 days.
"""
import sys; sys.path.insert(0,'/home/claude/lab')
import pandas as pd, numpy as np, itertools
C=pd.read_csv('/home/claude/lab/dol/US_weekly_claims_sa.csv',index_col=0,parse_dates=True)
SER={'initial':C['initial_claims'],'continued':C['continued_claims'],
     'sum':C['initial_claims']*4+C['continued_claims']}
PK=['1990-07','2001-03','2007-12','2020-02']
TR=['1991-03','2001-11','2009-06','2020-04']
def mo(t): return pd.Timestamp(t.year,t.month,1)
def md(x,y): return (x.year-y.year)*12+(x.month-y.month)
def build(s,sm):
    K=(np.log(s.rolling(sm).mean())*100.0).dropna()
    return K
def run(K,L,thp,rp,rt,delta,mp,pub=7):
    k=K.values; idx=K.index; n=len(k); calls=[]; state='exp'; last=-10**9
    lo=pd.Series(k,index=idx).rolling(L,min_periods=L//2)
    mn=lo.min().values
    am=lo.apply(lambda w: float(np.argmin(w)),raw=True).values
    S=k-mn
    kmax=-1e9; kmax_i=None; fall=0; prev=None
    for i in range(L,n):
        if not np.isfinite(S[i]): continue
        if state=='exp':
            if i-last<mp: continue
            if i-rp+1>=L and all(np.isfinite(S[j]) and S[j]>=thp for j in range(i-rp+1,i+1)):
                w0=max(0,i-L+1); lo_i=w0+int(am[i]) if np.isfinite(am[i]) else i
                calls.append(('peak',idx[i]+pd.Timedelta(days=pub),mo(idx[min(lo_i,n-1)])))
                state='con'; last=i; kmax=k[i]; kmax_i=i; fall=0; prev=k[i]
        else:
            if k[i]>kmax: kmax=k[i]; kmax_i=i; fall=0
            elif k[i]<prev: fall+=1
            else: fall=0
            prev=k[i]
            if i-last>=mp and fall>=rt and (kmax-k[i])>=delta:
                calls.append(('trough',idx[i]+pd.Timedelta(days=pub),mo(idx[kmax_i])))
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
for name,s in SER.items():
  for sm in (4,8,13):
    K=build(s,sm)
    for L,thp,rp,rt,delta,mp in itertools.product((52,78,104),(8.,12.,15.,20.,25.),(2,3,4),
                                                  (4,6,8),(3.,6.,10.),(26,39,52)):
        got,fa=score(run(K,L,thp,rp,rt,delta,mp))
        if len(got)<6: continue
        lags=[md(mo(v[0]),pd.Timestamp(kk+'-01')) for kk,v in got.items()]
        errs=[abs(v[1]) for v in got.values()]
        rows.append((len(got),-fa,-max(lags),name,sm,L,thp,rp,rt,delta,mp,
                     np.mean(lags),max(lags),np.mean(errs),max(errs),fa))
rows.sort(reverse=True)
print(f'{"hit":>4s} {"series":>10s} {"sm":>3s} {"L":>4s} {"th":>5s} {"rp":>3s} {"rt":>3s} {"del":>5s} {"mp":>4s} {"lagmu":>6s} {"lagmx":>6s} {"errmu":>6s} {"errmx":>6s} {"false":>6s}')
for b in rows[:25]:
    print(f'{b[0]:2d}/8 {b[3]:>10s} {b[4]:3d} {b[5]:4d} {b[6]:5.1f} {b[7]:3d} {b[8]:3d} {b[9]:5.1f} {b[10]:4d} {b[11]:6.2f} {b[12]:6d} {b[13]:6.2f} {b[14]:6d} {b[15]:6d}')

print()
print('DETAIL: initial, sm=13, L=104, th=15, rp=3, rt=8, delta=3, mp=26')
K=build(SER['initial'],13)
cs=run(K,104,15.,3,8,3.,26)
for kind,pub,dt in cs:
    print(f'   {kind:7s} dated {dt:%Y-%m}  publishable {pub:%Y-%m-%d}')
