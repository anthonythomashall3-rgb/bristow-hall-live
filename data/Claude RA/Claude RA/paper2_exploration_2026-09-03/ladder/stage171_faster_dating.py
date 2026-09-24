"""Stage 171: how soon can the right month be named?  The dating step reads a window that reaches
forward past the call, so the date is not final until that window fills.  A shorter forward
window makes the date final sooner -- if it costs no accuracy.  This stage sweeps the window and
the rounding jointly against the horizon, allowing each series only the months actually published
by then, and reports the earliest horizon at which each configuration reaches its final answer."""
exec(open("stage124_datemonth.py").read().split("def report(")[0])
import numpy as np, pandas as pd
FOUR={"payrolls":7,"real income less transfers":30,"industrial production":17,
      "real manufacturing and trade sales":47}
FOUR={k:v for k,v in FOUR.items() if k in M}
PUB={}
for nm,lag in FOUR.items():
    s=M[nm]
    PUB[nm]=pd.Series([(d+pd.offsets.MonthEnd(1))+pd.Timedelta(days=lag) for d in s.index],index=s.index)
def known(nm,asof):
    s=M[nm]; return s[PUB[nm]<=asof]
def turn(nm,anchor,asof,back,fwd,kind):
    s=known(nm,asof)
    w=s[(s.index>=anchor-pd.Timedelta(days=back))&(s.index<=min(asof,anchor+pd.Timedelta(days=fwd)))].dropna()
    return None if len(w)<6 else (w.idxmax() if kind=="max" else w.idxmin())
def med(anchor,asof,back,fwd,kind,how):
    o=[]
    for nm in FOUR:
        d=turn(nm,anchor,asof,back,fwd,kind)
        if d is not None: o.append(d.to_period("M").ordinal)
    if not o: return None
    x=float(np.median(o))
    v=int(np.floor(x)) if how=="earlier" else (int(np.ceil(x)) if how=="later" else int(round(x)))
    return pd.Period(ordinal=v,freq="M")
ENDC2=[pd.Timestamp(x) for x in ["1970-12-17","1975-05-08","1980-07-24","1982-11-18","1991-05-09",
                                 "2001-12-13","2009-05-14","2020-05-28","2024-09-26"]]
KS=[0,1,2,3,4,6,9,12]
def profile(anch,ref,kind,back,fwd,how):
    out=[]
    for k in KS:
        n=0
        for i,a in enumerate(anch):
            d=med(a,a+pd.DateOffset(months=k),back,fwd,kind,how)
            if d is not None and (d-pd.Period(ref[i],"M")).n==0: n+=1
        out.append(n)
    return out
print("PEAK — exact months by horizon (months after the alarm)")
print("%-6s %-6s %-9s %s"%("back","fwd","rounding"," ".join("%4d"%k for k in KS)))
bestP=[]
for back in [120,180,240,300]:
  for fwd in [30,60,90,120,180]:
    for how in ["earlier","nearest"]:
        p=profile(ALARM,PKM,"max",back,fwd,how)
        bestP.append((max(p),next(i for i,v in enumerate(p) if v==max(p)),back,fwd,how,p))
        print("%-6d %-6d %-9s %s"%(back,fwd,how," ".join("%4d"%v for v in p)))
print("\nTROUGH — exact months by horizon (months after the end call)")
print("%-6s %-6s %-9s %s"%("back","fwd","rounding"," ".join("%4d"%k for k in KS)))
bestT=[]
for back in [300,365,420,480]:
  for fwd in [30,60,90,120,180]:
    for how in ["nearest","earlier"]:
        p=profile(ENDC2,TRM,"min",back,fwd,how)
        bestT.append((max(p),next(i for i,v in enumerate(p) if v==max(p)),back,fwd,how,p))
        print("%-6d %-6d %-9s %s"%(back,fwd,how," ".join("%4d"%v for v in p)))
bestP.sort(key=lambda t:(-t[0],t[1])); bestT.sort(key=lambda t:(-t[0],t[1]))
print("\nfastest configurations that reach their best score earliest")
for lab,b in [("peak",bestP[0]),("trough",bestT[0])]:
    print("  %-7s best %d of 9, first reached at horizon %d months | window %d/%d, %s | profile %s"%(
        lab,b[0],KS[b[1]],b[2],b[3],b[4],b[5]))
