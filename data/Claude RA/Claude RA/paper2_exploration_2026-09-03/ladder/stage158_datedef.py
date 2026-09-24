"""Stage 158: does a different definition of 'the turning month' beat the plain high and low?
The committee does not take an argmax; it asks when a series began a sustained decline.  Three
a-priori definitions are tried on the same four coincident series -- the plain extremum, the last
month at the running extremum not regained for k months, and the last month before the series has
fallen a fixed fraction from its window high."""
exec(open("stage124_datemonth.py").read().split("def report(")[0])
import numpy as np, pandas as pd
FOUR=[n for n in ["payrolls","real income less transfers","industrial production",
                  "real manufacturing and trade sales"] if n in M]
def win(s,a,back,fwd):
    return s[(s.index>=a-pd.Timedelta(days=back))&(s.index<=a+pd.Timedelta(days=fwd))].dropna()
def turn_argmax(w,kind,**kw): return w.idxmax() if kind=="max" else w.idxmin()
def turn_lasthigh(w,kind,k=6):
    v=w.values if kind=="max" else -w.values
    n=len(v); best=None
    for i in range(n):
        if v[i]!=max(v[:i+1]): continue
        if i+1>=n: continue
        if max(v[i+1:min(n,i+1+k)])<=v[i]: best=i
    return w.index[best] if best is not None else w.index[int(np.argmax(v))]
def turn_drop(w,kind,frac=0.01):
    v=w.values if kind=="max" else -w.values
    run=-np.inf; pk=0; out=None
    for i in range(len(v)):
        if v[i]>run: run=v[i]; pk=i
        if run>0 and (run-v[i])/abs(run)>=frac and out is None: out=pk
    return w.index[out if out is not None else int(np.argmax(v))]
DEFS={"plain high or low":(turn_argmax,{}),
      "last extremum not regained for 6 months":(turn_lasthigh,{"k":6}),
      "last extremum not regained for 9 months":(turn_lasthigh,{"k":9}),
      "the month before a 0.5 per cent fall":(turn_drop,{"frac":0.005}),
      "the month before a 1 per cent fall":(turn_drop,{"frac":0.01}),
      "the month before a 2 per cent fall":(turn_drop,{"frac":0.02})}
ENDC2=[pd.Timestamp(x) for x in ["1970-12-17","1975-05-08","1980-07-24","1982-11-18","1991-05-09",
                                 "2001-12-13","2009-05-14","2020-05-28","2024-09-26"]]
for lab2,anch,ref,kind,bw in [("PEAK",ALARM,PKM,"max",(180,180)),("TROUGH",ENDC2,TRM,"min",(365,180))]:
    print("\n%s"%lab2)
    print("%-42s %-8s %-8s %s"%("definition","exact","<=1 mo","months from the NBER date"))
    for lab,(fn,kw) in DEFS.items():
        mo=[]
        for i,a in enumerate(anch):
            o=[]
            for nm in FOUR:
                w=win(M[nm],a,bw[0],bw[1])
                if len(w)<8: continue
                o.append(fn(w,kind,**kw).to_period("M").ordinal)
            if not o: mo.append(None); continue
            d=pd.Period(ordinal=int(round(float(np.median(o)))),freq="M")
            mo.append((d-pd.Period(ref[i],"M")).n)
        ok=[x for x in mo if x is not None]
        print("%-42s %-8d %-8d %s"%(lab,sum(1 for x in ok if x==0),sum(1 for x in ok if abs(x)<=1),mo))
