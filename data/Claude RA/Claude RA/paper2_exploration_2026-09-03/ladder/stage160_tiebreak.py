"""Stage 160: the median of four series is an average of two months, and how that average is
rounded is a free choice worth one month.  With an even panel the four series often straddle.
Rounding up, rounding down and rounding to nearest are all a-priori conventions; this stage
reports what each costs, on both ends."""
exec(open("stage124_datemonth.py").read().split("def report(")[0])
import numpy as np, pandas as pd
FOUR=[n for n in ["payrolls","real income less transfers","industrial production",
                  "real manufacturing and trade sales"] if n in M]
ENDC2=[pd.Timestamp(x) for x in ["1970-12-17","1975-05-08","1980-07-24","1982-11-18","1991-05-09",
                                 "2001-12-13","2009-05-14","2020-05-28","2024-09-26"]]
def months(a,back,fwd,kind):
    o=[]
    for nm in FOUR:
        w=M[nm][(M[nm].index>=a-pd.Timedelta(days=back))&(M[nm].index<=a+pd.Timedelta(days=fwd))].dropna()
        if len(w)>=6: o.append((w.idxmax() if kind=="max" else w.idxmin()).to_period("M").ordinal)
    return sorted(o)
def agg(o,how):
    if not o: return None
    x=float(np.median(o))
    v={"nearest":int(round(x)),"earlier":int(np.floor(x)),"later":int(np.ceil(x)),
       "earliest":int(min(o)),"latest":int(max(o))}[how]
    return pd.Period(ordinal=v,freq="M")
for lab,anch,ref,kind,bw in [("PEAK",ALARM,PKM,"max",(180,180)),("TROUGH",ENDC2,TRM,"min",(365,180))]:
    print("\n%s"%lab)
    print("%-12s %-8s %-8s %s"%("convention","exact","<=1 mo","months from the NBER date"))
    for how in ["nearest","earlier","later","earliest","latest"]:
        mo=[]
        for i,a in enumerate(anch):
            o=months(a,bw[0],bw[1],kind); d=agg(o,how)
            mo.append(None if d is None else (d-pd.Period(ref[i],"M")).n)
        ok=[x for x in mo if x is not None]
        print("%-12s %-8d %-8d %s"%(how,sum(1 for x in ok if x==0),sum(1 for x in ok if abs(x)<=1),mo))
print("\nthe four individual months, per episode (peak)")
for i,a in enumerate(ALARM):
    o=months(a,180,180,"max")
    print("  %-8s %s"%(PKM[i],[str(pd.Period(ordinal=x,freq="M")) for x in o]))
