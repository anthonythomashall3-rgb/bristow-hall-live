"""Stage 183: three shapes of dating rule that have not been tried.
(A) Announce when the panel AGREES, rather than at a fixed horizon: the date is published the
    first month in which the members' own turning months fall within one month of each other.
    The horizon then adapts to the episode instead of being the same for all of them.
(B) Anchor the window on the CLAIMS LOW rather than on the alarm.  The last low in the eight-week
    claims average before the rise is weekly, available immediately, and is a labour-market
    object rather than a trigger, so it may be a better centre for the search.
(C) A duration prior for the trough: recessions since 1948 have run six to eighteen months, so
    once the peak is dated the trough is partly known before any trough data arrive."""
exec(open("stage171_faster_dating.py").read().split('print("PEAK')[0])
import numpy as np, pandas as pd, os
ALL4=list(FOUR); FAST=[n for n in ALL4 if n!="real manufacturing and trade sales"]
ENDC2=[pd.Timestamp(x) for x in ["1970-12-17","1975-05-08","1980-07-24","1982-11-18","1991-05-09",
                                 "2001-12-13","2009-05-14","2020-05-28","2024-09-26"]]
def months_at(names,anchor,asof,back,fwd,kind):
    o={}
    for nm in names:
        d=turn(nm,anchor,asof,back,fwd,kind)
        if d is not None: o[nm]=d.to_period("M").ordinal
    return o
print("(A) announce when the panel agrees within one month")
print("%-9s %-10s %-11s %s"%("peak","announced","error","the members' months when it announced"))
errs=[];hz=[]
for i,a in enumerate(ALARM):
    got=None
    for k in range(1,13):
        o=months_at(ALL4,a,a+pd.DateOffset(months=k),180,180,"max")
        if len(o)<3: continue
        v=sorted(o.values())
        if v[-1]-v[0]<=1:
            got=(k,int(round(float(np.median(v)))),v); break
    if got is None:
        o=months_at(ALL4,a,a+pd.DateOffset(months=12),180,180,"max")
        v=sorted(o.values()); got=(12,int(round(float(np.median(v)))),v)
    k,m,v=got
    e=(pd.Period(ordinal=m,freq="M")-pd.Period(PKM[i],"M")).n
    errs.append(e); hz.append(k)
    print("%-9s %-10s %-11s %s"%(PKM[i],"%d mo"%k,"%+d"%e,[str(pd.Period(ordinal=x,freq="M")) for x in v]))
print("   exact %d of 9, within one month %d, median horizon %.0f months"%(
    sum(1 for x in errs if x==0),sum(1 for x in errs if abs(x)<=1),float(np.median(hz))))
ODD2=os.path.expanduser("~/mnt/Onset Detector Data/")
ic=pd.read_csv(ODD2+"01_labor_unemployment/weekly/ICSA.csv",parse_dates=[0]).set_index("date" if "date" in open(ODD2+"01_labor_unemployment/weekly/ICSA.csv").readline() else 0).iloc[:,0]
ic=pd.to_numeric(ic,errors="coerce").dropna()
m8=ic.rolling(8).mean()
def claims_low(a):
    w=m8[(m8.index>=a-pd.Timedelta(days=730))&(m8.index<=a)]
    return None if len(w)<20 else w.idxmin()
print("\n(B) anchor the window on the claims low instead of the alarm")
print("%-9s %-12s %-12s %-9s %s"%("peak","alarm","claims low","error","note"))
errsB=[]
for i,a in enumerate(ALARM):
    cl=claims_low(a)
    if cl is None: errsB.append(None); continue
    d=med(cl,cl+pd.DateOffset(months=12),180,180,"max","earlier")
    e=None if d is None else (d-pd.Period(PKM[i],"M")).n
    errsB.append(e)
    print("%-9s %-12s %-12s %-9s %s"%(PKM[i],str(a.date()),str(cl.date()),("%+d"%e) if e is not None else "-",
          "%d days before the alarm"%((a-cl).days)))
ok=[x for x in errsB if x is not None]
print("   exact %d of 9, within one month %d"%(sum(1 for x in ok if x==0),sum(1 for x in ok if abs(x)<=1)))
print("\n(C) duration prior: months from peak to trough, NBER")
dur=[(pd.Period(t,"M")-pd.Period(p,"M")).n for p,t in T_P1]
print("   %s | median %d, range %d to %d"%(dur,int(np.median(dur)),min(dur),max(dur)))
print("   trough implied by the peak plus the median duration alone:")
imp=[(pd.Period(PKM[i],"M")+int(np.median(dur))-pd.Period(TRM[i],"M")).n for i in range(9)]
print("   %s | exact %d of 9, within one month %d"%(imp,sum(1 for x in imp if x==0),sum(1 for x in imp if abs(x)<=1)))
