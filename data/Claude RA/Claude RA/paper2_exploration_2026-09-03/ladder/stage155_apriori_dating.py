"""Stage 155: an a-priori dating step.  Stage 134 showed that choosing the panel by searching
subsets does not survive leave-one-out.  The committee names four monthly coincident series in
its own documents; using exactly those four, with no selection at all, is the honest form of the
dating step.  This stage measures it, and also asks what the machine would do in 2020 without
the volatility lane."""
exec(open("stage124_datemonth.py").read().split("def report(")[0])
import numpy as np, pandas as pd
FOUR=[n for n in ["payrolls","real income less transfers","industrial production",
                  "real manufacturing and trade sales"] if n in M]
print("the committee's four coincident series, as named in its own procedure: %s"%", ".join(FOUR))
def pick(s,a,back,fwd,kind):
    w=s[(s.index>=a-pd.Timedelta(days=back))&(s.index<=a+pd.Timedelta(days=fwd))].dropna()
    if len(w)<6: return None
    return w.idxmax() if kind=="max" else w.idxmin()
def med(names,a,back,fwd,kind):
    ds=[]
    for nm in names:
        d=pick(M[nm],a,back,fwd,kind)
        if d is not None: ds.append(d.to_period("M").ordinal)
    if not ds: return None
    return pd.Period(ordinal=int(round(float(np.median(ds)))),freq="M").to_timestamp()
print("\nPEAK, median of the four highs")
print("%-10s %-10s %s"%("window","exact","months from the NBER peak"))
for back,fwd in [(180,180),(150,210),(210,150),(120,240),(240,120)]:
    mo=[]
    for i,a in enumerate(ALARM):
        d=med(FOUR,a,back,fwd,"max")
        mo.append(None if d is None else (d.to_period("M")-pd.Period(PKM[i],"M")).n)
    if any(x is None for x in mo): continue
    print("%-10s %-10s %s"%("%d/%d"%(back,fwd),"%d of 9"%sum(1 for x in mo if x==0),mo))
print("\nTROUGH, median of the four lows")
print("%-10s %-10s %s"%("window","exact","months from the NBER trough"))
for back,fwd in [(365,180),(300,240),(420,120),(365,240)]:
    mo=[]
    for i,a in enumerate(ENDC):
        d=med(FOUR,a,back,fwd,"min")
        mo.append(None if d is None else (d.to_period("M")-pd.Period(TRM[i],"M")).n)
    if any(x is None for x in mo): continue
    print("%-10s %-10s %s"%("%d/%d"%(back,fwd),"%d of 9"%sum(1 for x in mo if x==0),mo))
print("\nsingle a-priori objects, for comparison")
for nm,kind,ref,anch,bw in [("real income less transfers","max",PKM,ALARM,(180,180)),
                            ("payrolls","max",PKM,ALARM,(180,180)),
                            ("industrial production","min",TRM,ENDC,(365,180)),
                            ("capacity use","min",TRM,ENDC,(365,180))]:
    if nm not in M: continue
    mo=[]
    for i,a in enumerate(anch):
        d=pick(M[nm],a,bw[0],bw[1],kind)
        mo.append(None if d is None else (d.to_period("M")-pd.Period(ref[i],"M")).n)
    print("  %-36s %-8s %s"%(nm,"%d of 9"%sum(1 for x in mo if x==0),mo))
