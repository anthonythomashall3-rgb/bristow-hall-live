"""Stage 131: v12.  The machine now returns three things instead of one: an ALARM, which is
v11's trigger and is meant to be early; a PEAK DATE; and a TROUGH DATE.  The two dates are
measurements, placed by the monthly coincident series, and are allowed to be revised as data
arrive.  This stage picks the dating objects and reports the whole record."""
exec(open("stage124_datemonth.py").read().split('def report(')[0])
import numpy as np, pandas as pd
M["unemployment rate"]=load(ODD+"01_labor_unemployment/monthly/UNRATE.csv")
def comp(names):
    fr={}
    for n in names:
        s=M[n].astype(float); fr[n]=np.log(s).diff() if (s>0).all() else s.diff()
    d=pd.DataFrame(fr).dropna(how="all"); z=(d-d.mean())/d.std()
    return z.mean(axis=1,skipna=True).dropna().cumsum()
def pick(s,a,back,fwd,kind):
    w=s[(s.index>=a-pd.Timedelta(days=back))&(s.index<=a+pd.Timedelta(days=fwd))].dropna()
    if len(w)<6: return None
    return w.idxmax() if kind=="max" else w.idxmin()
def evalpeak(lab,f):
    mo=[]
    for i,a in enumerate(ALARM):
        d=f(a,i)
        mo.append(np.nan if d is None else (d.to_period("M")-pd.Period(PKM[i],"M")).n)
    if any(x!=x for x in mo): return None
    return (sum(1 for x in mo if x==0),float(np.mean(np.abs(mo))),lab,[int(x) for x in mo])
CANDP=[]
for nm in ["real income less transfers","payrolls","household employment","industrial production",
           "real manufacturing and trade sales","employment-population ratio","capacity use"]:
    if nm in M: CANDP.append(("%s, high"%nm, lambda a,i,s=M[nm]: pick(s,a,180,180,"max")))
CANDP.append(("unemployment rate, low", lambda a,i: pick(M["unemployment rate"],a,180,180,"min")))
CANDP.append(("committee four composite, high", lambda a,i,c=comp(["payrolls","real income less transfers","industrial production","real manufacturing and trade sales"]): pick(c,a,180,180,"max")))
def medmonth(a,i,names):
    ds=[]
    for nm in names:
        d=pick(M[nm],a,180,180,"max")
        if d is not None: ds.append(d.to_period("M").ordinal)
    if not ds: return None
    return pd.Period(ordinal=int(np.median(ds)),freq="M").to_timestamp()
CANDP.append(("panel median of six, high", lambda a,i: medmonth(a,i,[n for n in ["real income less transfers","payrolls","household employment","industrial production","real manufacturing and trade sales","capacity use"] if n in M])))
R=[r for r in (evalpeak(l,f) for l,f in CANDP) if r]
R.sort(key=lambda t:(-t[0],t[1]))
print("PEAK dating candidates (window: 180 days either side of the alarm)")
print("%-40s %-7s %-8s %s"%("object","exact","mean|m|","months from the NBER peak"))
for ex,ma,lab,mo in R: print("%-40s %-7d %-8.2f %s"%(lab,ex,ma,mo))
def evaltr(lab,f):
    mo=[]
    for i,a in enumerate(ENDC):
        d=f(a,i)
        mo.append(np.nan if d is None else (d.to_period("M")-pd.Period(TRM[i],"M")).n)
    if any(x!=x for x in mo): return None
    return (sum(1 for x in mo if x==0),float(np.mean(np.abs(mo))),lab,[int(x) for x in mo])
CANDT=[]
for nm in ["capacity use","industrial production","real manufacturing and trade sales","payrolls","manufacturing output"]:
    if nm in M: CANDT.append(("%s, low"%nm, lambda a,i,s=M[nm]: pick(s,a,365,180,"min")))
CANDT.append(("unemployment rate, high", lambda a,i: pick(M["unemployment rate"],a,365,180,"max")))
CANDT.append(("output pair composite, low", lambda a,i,c=comp(["industrial production","capacity use"]): pick(c,a,365,180,"min")))
R2=[r for r in (evaltr(l,f) for l,f in CANDT) if r]
R2.sort(key=lambda t:(-t[0],t[1]))
print("\nTROUGH dating candidates (window: 365 days back, 180 forward from the end call)")
print("%-40s %-7s %-8s %s"%("object","exact","mean|m|","months from the NBER trough"))
for ex,ma,lab,mo in R2: print("%-40s %-7d %-8.2f %s"%(lab,ex,ma,mo))
bp=R[0]; bt=R2[0]
print("\n=== v12 record ===")
print("alarm (v11 trigger)        days from the recession's first day: %s"%[-87,-37,-29,17,2,-58,3,-2,2])
print("peak  dated by %-26s months from the NBER peak:   %s"%(bp[2],bp[3]))
print("trough dated by %-25s months from the NBER trough: %s"%(bt[2],bt[3]))
dp=[x*0 for x in bp[3]]
print("peak  date exact in %d of 9; within one month in %d of 9"%(sum(1 for x in bp[3] if x==0),sum(1 for x in bp[3] if abs(x)<=1)))
print("trough date exact in %d of 9; within one month in %d of 9"%(sum(1 for x in bt[3] if x==0),sum(1 for x in bt[3] if abs(x)<=1)))
