"""Stage 184: a slope break on the coincident composite.  A break was tried on claims (stage 123)
and failed because claims turn a year early.  It has never been tried on the object that actually
defines the turning point.  A continuous two-segment least-squares fit is run on each coincident
series and on their composite, and the break month compared with the committee's."""
exec(open("stage124_datemonth.py").read().split("def report(")[0])
import numpy as np, pandas as pd
ALL4=[n for n in ["payrolls","real income less transfers","industrial production",
                  "real manufacturing and trade sales"] if n in M]
ENDC2=[pd.Timestamp(x) for x in ["1970-12-17","1975-05-08","1980-07-24","1982-11-18","1991-05-09",
                                 "2001-12-13","2009-05-14","2020-05-28","2024-09-26"]]
def comp(names):
    fr={}
    for n in names:
        s=M[n].astype(float); fr[n]=np.log(s).diff() if (s>0).all() else s.diff()
    d=pd.DataFrame(fr).dropna(how="all"); z=(d-d.mean())/d.std()
    return z.mean(axis=1,skipna=True).dropna().cumsum()
def brk(y,minseg=4):
    n=len(y); t=np.arange(n,dtype=float); best=(np.inf,None)
    for k in range(minseg,n-minseg):
        X=np.column_stack([np.ones(n),t,np.maximum(t-k,0.0)])
        b,_,_,_=np.linalg.lstsq(X,y,rcond=None); r=y-X@b; s=float(r@r)
        if s<best[0]: best=(s,k)
    return best[1]
C=comp(ALL4)
print("%-30s %-8s %-8s %s"%("object","exact","<=1 mo","months from the NBER date"))
for lab,anch,ref,back,fwd in [("PEAK",ALARM,PKM,365,365),("TROUGH",ENDC2,TRM,365,365)]:
    print("\n%s (window %d/%d around the call)"%(lab,back,fwd))
    for nm,s in [("the composite",C)]+[(n,np.log(M[n].astype(float))) for n in ALL4]:
        mo=[]
        for i,a in enumerate(anch):
            w=s[(s.index>=a-pd.Timedelta(days=back))&(s.index<=a+pd.Timedelta(days=fwd))].dropna()
            if len(w)<14: mo.append(None); continue
            k=brk(w.values)
            mo.append(None if k is None else (w.index[k].to_period("M")-pd.Period(ref[i],"M")).n)
        ok=[x for x in mo if x is not None]
        print("%-30s %-8s %-8d %s"%(nm,"%d of 9"%sum(1 for x in ok if x==0),sum(1 for x in ok if abs(x)<=1),mo))
    mo=[]
    for i,a in enumerate(anch):
        o=[]
        for n in ALL4:
            s=np.log(M[n].astype(float))
            w=s[(s.index>=a-pd.Timedelta(days=back))&(s.index<=a+pd.Timedelta(days=fwd))].dropna()
            if len(w)<14: continue
            k=brk(w.values)
            if k is not None: o.append(w.index[k].to_period("M").ordinal)
        mo.append(None if not o else (pd.Period(ordinal=int(round(float(np.median(o)))),freq="M")-pd.Period(ref[i],"M")).n)
    ok=[x for x in mo if x is not None]
    print("%-30s %-8s %-8d %s"%("median of the four breaks","%d of 9"%sum(1 for x in ok if x==0),sum(1 for x in ok if abs(x)<=1),mo))
