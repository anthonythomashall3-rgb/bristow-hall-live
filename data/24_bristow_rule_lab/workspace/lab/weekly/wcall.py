"""The Bristow Rule on a weekly panel, in real time, at both ends.

Composite deviation D(t): each channel's own deviation from its trailing L-week maximum
of the smoothed level, in percent, averaged across the channels that exist that week.
Claims enter negated, so every channel is pro-cyclical.

  PEAK    D has held at or above theta_p for rp weeks; the peak is the month given by
          the panel median of the channels' own low-band dates (the rule's peak clause).
  TROUGH  after a peak call, D reaches a maximum and then falls for rt weeks and by
          delta points; the trough is the month given by the panel median of the
          channels' own high-band dates since the peak (the rule's trough clause).
  CENSOR  mp weeks minimum between calls.
Data for week W is published the following week, so a call on week W is charged to W+7d.
"""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import ch_trough, ch_peak, med
import pandas as pd, numpy as np, itertools, warnings
warnings.filterwarnings("ignore")
W=pd.read_csv('/home/claude/lab/weekly/US_weekly_panel.csv',index_col=0,parse_dates=True)
SIGN={'initial claims':-1,'continued claims':-1,'petroleum products supplied':1,
      'withheld taxes':1}
PK=['1990-07','2001-03','2007-12','2020-02']
TR=['1991-03','2001-11','2009-06','2020-04']
def mo(t): return pd.Timestamp(t.year,t.month,1)
def md(x,y): return (x.year-y.year)*12+(x.month-y.month)
def channels(sm):
    out={}
    for c in W.columns:
        s=W[c].dropna()
        v=np.log(s)*SIGN[c]*100.0
        out[c]=v.rolling(sm).mean().dropna()
    return out
def composite(ch,L):
    cols=[]
    for c,v in ch.items():
        mx=v.rolling(L,min_periods=L//2).max()
        cols.append((mx-v).rename(c))
    D=pd.concat(cols,axis=1,sort=True)
    return D.mean(axis=1,skipna=True).dropna(), D.notna().sum(axis=1)
def run(ch,L,thp,rp,rt,delta,band,mp,pub=7):
    D,ncol=composite(ch,L); idx=D.index; d=D.values; n=len(d)
    calls=[]; state='exp'; last=-10**9; pk=None; dmax=-1e9; dmax_at=None; fall=0; prev=None
    for i in range(1,n):
        t=idx[i]
        if state=='exp':
            if i-last<mp: continue
            if i-rp+1>=0 and all(d[j]>=thp for j in range(i-rp+1,i+1)):
                w0=idx[max(0,i-L)]
                ds=[ch_peak(v[w0:t],w0,t,band,1,abstain=False) for v in ch.values()
                    if len(v[w0:t])>4]
                p=med([x for x in ds if x is not None]) or t
                calls.append(('peak',t+pd.Timedelta(days=pub),mo(p)))
                state='con'; last=i; pk=p; dmax=d[i]; dmax_at=t; fall=0; prev=d[i]
        else:
            if d[i]>dmax: dmax=d[i]; dmax_at=t; fall=0
            elif d[i]<prev: fall+=1
            else: fall=0
            prev=d[i]
            if i-last>=mp and fall>=rt and (dmax-d[i])>=delta:
                ds=[ch_trough(v[pk:t],pk,t,band,1,L,abstain=False) for v in ch.values()
                    if len(v[pk:t])>4]
                q=med([x for x in ds if x is not None]) or t
                calls.append(('trough',t+pd.Timedelta(days=pub),mo(q)))
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
for sm in (4,13):
    ch=channels(sm)
    for L,thp,rp,rt,delta,band,mp in itertools.product(
            (52,78,104),(3.,5.,8.,12.),(2,3,4),(4,6,8),(1.,3.),(0.12,0.25),(26,39)):
        got,fa=score(run(ch,L,thp,rp,rt,delta,band,mp))
        if len(got)<5: continue
        lags=[md(mo(v[0]),pd.Timestamp(kk+'-01')) for kk,v in got.items()]
        errs=[abs(v[1]) for v in got.values()]
        rows.append((len(got),-max(lags),-fa,sm,L,thp,rp,rt,delta,band,mp,
                     np.mean(lags),max(lags),np.mean(errs),max(errs),fa))
rows.sort(reverse=True)
print(f'{"hit":>4s} {"sm":>3s} {"L":>4s} {"th":>5s} {"rp":>3s} {"rt":>3s} {"del":>4s} {"band":>5s} {"mp":>4s} {"lagmu":>6s} {"lagmx":>6s} {"errmu":>6s} {"errmx":>6s} {"false":>6s}')
for b in rows[:22]:
    print(f'{b[0]:2d}/8 {b[3]:3d} {b[4]:4d} {b[5]:5.1f} {b[6]:3d} {b[7]:3d} {b[8]:4.1f} {b[9]:5.2f} {b[10]:4d} {b[11]:6.2f} {b[12]:6d} {b[13]:6.2f} {b[14]:6d} {b[15]:6d}')
