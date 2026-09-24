"""Stage 133: which small panel of coincident series names the peak month best?  Every subset
of the plausible objects is scored by how often the median of their individual highs is the
NBER's own peak month."""
exec(open("stage124_datemonth.py").read().split('def report(')[0])
import numpy as np, pandas as pd, itertools
M["unemployment rate"]=load(ODD+"01_labor_unemployment/monthly/UNRATE.csv")
def pick(s,a,back,fwd,kind):
    w=s[(s.index>=a-pd.Timedelta(days=back))&(s.index<=a+pd.Timedelta(days=fwd))].dropna()
    if len(w)<6: return None
    return w.idxmax() if kind=="max" else w.idxmin()
POOL=[n for n in ["real income less transfers","payrolls","household employment","industrial production",
                  "real manufacturing and trade sales","capacity use","employment-population ratio",
                  "manufacturing employment","real consumption","retail sales","average weekly hours"] if n in M]
def med_peak(names,a,back,fwd):
    ds=[]
    for nm in names:
        d=pick(M[nm],a,back,fwd,"max")
        if d is not None: ds.append(d.to_period("M").ordinal)
    if not ds: return None
    return pd.Period(ordinal=int(round(float(np.median(ds)))),freq="M").to_timestamp()
res=[]
for r in range(1,6):
  for names in itertools.combinations(POOL,r):
    for back,fwd in [(180,180),(150,210),(210,150),(120,240)]:
        mo=[]
        for i,a in enumerate(ALARM):
            d=med_peak(names,a,back,fwd)
            mo.append(np.nan if d is None else (d.to_period("M")-pd.Period(PKM[i],"M")).n)
        if any(x!=x for x in mo): continue
        ex=sum(1 for x in mo if x==0); w1=sum(1 for x in mo if abs(x)<=1)
        res.append((ex,w1,-float(np.mean(np.abs(mo))),names,back,fwd,[int(x) for x in mo]))
res.sort(reverse=True)
print("PEAK: best panels (median of the individual highs)")
print("%-6s %-6s %-8s %-58s %s"%("exact","<=1m","mean|m|","panel","months from the NBER peak"))
seen=set()
for ex,w1,nm_,names,back,fwd,mo in res[:60]:
    k=tuple(mo)
    if k in seen: continue
    seen.add(k)
    print("%-6d %-6d %-8.2f %-58s %s"%(ex,w1,-nm_," + ".join(n[:18] for n in names),mo))
    if len(seen)>=12: break
POOLT=[n for n in ["capacity use","industrial production","manufacturing output","real manufacturing and trade sales",
                   "payrolls","household employment","real income less transfers"] if n in M]
def med_tr(names,a,back,fwd):
    ds=[]
    for nm in names:
        d=pick(M[nm],a,back,fwd,"min")
        if d is not None: ds.append(d.to_period("M").ordinal)
    if not ds: return None
    return pd.Period(ordinal=int(round(float(np.median(ds)))),freq="M").to_timestamp()
res2=[]
for r in range(1,6):
  for names in itertools.combinations(POOLT,r):
    for back,fwd in [(365,180),(300,240),(420,120)]:
        mo=[]
        for i,a in enumerate(ENDC):
            d=med_tr(names,a,back,fwd)
            mo.append(np.nan if d is None else (d.to_period("M")-pd.Period(TRM[i],"M")).n)
        if any(x!=x for x in mo): continue
        res2.append((sum(1 for x in mo if x==0),sum(1 for x in mo if abs(x)<=1),-float(np.mean(np.abs(mo))),names,back,fwd,[int(x) for x in mo]))
res2.sort(reverse=True)
print("\nTROUGH: best panels (median of the individual lows)")
print("%-6s %-6s %-8s %-58s %s"%("exact","<=1m","mean|m|","panel","months from the NBER trough"))
seen=set()
for ex,w1,nm_,names,back,fwd,mo in res2[:60]:
    k=tuple(mo)
    if k in seen: continue
    seen.add(k)
    print("%-6d %-6d %-8.2f %-58s %s"%(ex,w1,-nm_," + ".join(n[:18] for n in names),mo))
    if len(seen)>=10: break
