"""Real-time caller on weekly claims, both ends, with a minimum-phase guard.
Scored to Anthony's bar: a turning point counts only if some call of the right kind
lands within 2 months of it, and the lag is months from the event to publication."""
import sys; sys.path.insert(0,'/home/claude/lab')
import pandas as pd, numpy as np, itertools
C=pd.read_csv('/home/claude/lab/dol/US_weekly_claims_sa.csv',index_col=0,parse_dates=True)
A=(-np.log(C['initial_claims'].rolling(4).mean())*100.0).dropna()
idx=A.index; a=A.values; n=len(a)
PK=['1990-07','2001-03','2007-12','2020-02']
TR=['1991-03','2001-11','2009-06','2020-04']
def mo(t): return pd.Timestamp(t.year,t.month,1)
def md(x,y): return (x.year-y.year)*12+(x.month-y.month)
DEV={}; ARG={}
for L in (26,39,52,78,104):
    DEV[L]=(A.rolling(L,min_periods=L//2).max().values-a)
    ARG[L]=A.rolling(L,min_periods=L//2).apply(lambda w: float(np.argmax(w)),raw=True).values
def run(L,thp,rp,rt,mp,pub=7):
    D=DEV[L]; AG=ARG[L]; calls=[]; state='exp'; last=-10**9
    dmax=-1e9; dmax_at=None; fall=0; prev=None
    for i in range(L,n):
        d=D[i]
        if not np.isfinite(d): continue
        if state=='exp':
            if i-last<mp: continue
            if i-rp+1>=L and all(np.isfinite(D[j]) and D[j]>=thp for j in range(i-rp+1,i+1)):
                w0=max(0,i-L+1); hi_i=w0+int(AG[i]) if np.isfinite(AG[i]) else i
                calls.append(('peak',idx[i]+pd.Timedelta(days=pub),mo(idx[min(hi_i,n-1)])))
                state='con'; last=i; dmax=d; dmax_at=idx[i]; fall=0; prev=d
        else:
            if i-last<mp: prev=d; continue
            if d>dmax: dmax=d; dmax_at=idx[i]; fall=0
            elif d<prev: fall+=1
            else: fall=0
            prev=d
            if fall>=rt:
                calls.append(('trough',idx[i]+pd.Timedelta(days=pub),mo(dmax_at)))
                state='exp'; last=i
    return calls
def score(calls,tol=2):
    got={}; used=set(); false_=0
    for j,(kind,pub,dt) in enumerate(calls):
        tgt=PK if kind=='peak' else TR
        best=None
        for k in tgt:
            if k in got: continue
            e=md(dt,pd.Timestamp(k+'-01'))
            if abs(e)<=tol and (best is None or abs(e)<abs(best[1])): best=(k,e)
        if best: got[best[0]]=(pub,best[1])
        else: false_+=1
    return got,false_
rows=[]
for L,thp,rp,rt,mp in itertools.product((26,39,52,78,104),(3.,5.,8.,10.,12.,15.),(2,3,4,6),(4,6,8,12),(26,39,52,78)):
    got,fa=score(run(L,thp,rp,rt,mp))
    if not got: continue
    lags=[md(mo(v[0]),pd.Timestamp(k+'-01')) for k,v in got.items()]
    errs=[abs(v[1]) for v in got.values()]
    rows.append((len(got),-fa,-max(lags),L,thp,rp,rt,mp,np.mean(lags),max(lags),
                 np.mean(errs),max(errs),fa))
rows.sort(reverse=True)
print(f'{"hit":>4s} {"L":>4s} {"th":>5s} {"rp":>3s} {"rt":>3s} {"mp":>4s} {"lag mu":>7s} {"lag max":>8s} {"err mu":>7s} {"err max":>8s} {"false":>6s}')
for b in rows[:22]:
    print(f'{b[0]:2d}/8 {b[3]:4d} {b[4]:5.1f} {b[5]:3d} {b[6]:3d} {b[7]:4d} {b[8]:7.2f} {b[9]:8d} {b[10]:7.2f} {b[11]:8d} {b[12]:6d}')
