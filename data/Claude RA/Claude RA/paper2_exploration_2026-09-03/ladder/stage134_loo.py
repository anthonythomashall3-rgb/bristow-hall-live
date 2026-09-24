"""Stage 134: is the dating panel fitted?  The panels of stage 133 were chosen by searching
subsets against all nine episodes.  Here the choice is made nine times over, each time using
only the other eight, and the held-out episode is dated by a panel that never saw it."""
exec(open("stage124_datemonth.py").read().split('def report(')[0])
import numpy as np, pandas as pd, itertools
M["unemployment rate"]=load(ODD+"01_labor_unemployment/monthly/UNRATE.csv")
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
POOLP=[n for n in ["real income less transfers","payrolls","household employment","industrial production",
                   "real manufacturing and trade sales","capacity use","employment-population ratio",
                   "manufacturing employment","real consumption","retail sales","average weekly hours"] if n in M]
POOLT=[n for n in ["capacity use","industrial production","manufacturing output","real manufacturing and trade sales",
                   "payrolls","household employment","real income less transfers"] if n in M]
def table(pool,anchors,refm,kind,wins,maxr=5):
    cache={}
    for r in range(1,maxr+1):
        for names in itertools.combinations(pool,r):
            for back,fwd in wins:
                mo=[]
                for i,a in enumerate(anchors):
                    d=med(names,a,back,fwd,kind)
                    mo.append(np.nan if d is None else (d.to_period("M")-pd.Period(refm[i],"M")).n)
                if any(x!=x for x in mo): continue
                cache[(names,back,fwd)]=[int(x) for x in mo]
    return cache
CP=table(POOLP,ALARM,PKM,"max",[(180,180),(150,210),(210,150),(120,240)])
CT=table(POOLT,ENDC,TRM,"min",[(365,180),(300,240),(420,120)])
def loo(cache):
    out=[]
    for h in range(9):
        best=None
        for key,mo in cache.items():
            o=[mo[j] for j in range(9) if j!=h]
            sc=(sum(1 for x in o if x==0),sum(1 for x in o if abs(x)<=1),-float(np.mean(np.abs(o))),
                -len(key[0]))
            if best is None or sc>best[0]: best=(sc,key,mo)
        out.append(best[2][h])
    return out
lp=loo(CP); lt=loo(CT)
print("leave-one-out dating (the panel is re-chosen from the other eight each time)")
print("peak   months from the NBER peak:   %s   exact %d of 9, within one month %d of 9"%(lp,sum(1 for x in lp if x==0),sum(1 for x in lp if abs(x)<=1)))
print("trough months from the NBER trough: %s   exact %d of 9, within one month %d of 9"%(lt,sum(1 for x in lt if x==0),sum(1 for x in lt if abs(x)<=1)))
bp=max(CP.items(),key=lambda kv:(sum(1 for x in kv[1] if x==0),sum(1 for x in kv[1] if abs(x)<=1),-np.mean(np.abs(kv[1]))))
bt=max(CT.items(),key=lambda kv:(sum(1 for x in kv[1] if x==0),sum(1 for x in kv[1] if abs(x)<=1),-np.mean(np.abs(kv[1]))))
print("\nin-sample best peak panel  : %s  window %d/%d  %s"%(" + ".join(bp[0][0]),bp[0][1],bp[0][2],bp[1]))
print("in-sample best trough panel: %s  window %d/%d  %s"%(" + ".join(bt[0][0]),bt[0][1],bt[0][2],bt[1]))
print("\nhow much of the pool matters: the median across ALL objects, no selection at all")
allp=[]; allt=[]
for i,a in enumerate(ALARM):
    d=med(POOLP,a,180,180,"max"); allp.append(None if d is None else (d.to_period("M")-pd.Period(PKM[i],"M")).n)
for i,a in enumerate(ENDC):
    d=med(POOLT,a,365,180,"min"); allt.append(None if d is None else (d.to_period("M")-pd.Period(TRM[i],"M")).n)
print("peak   %s  exact %d of 9"%(allp,sum(1 for x in allp if x==0)))
print("trough %s  exact %d of 9"%(allt,sum(1 for x in allt if x==0)))
