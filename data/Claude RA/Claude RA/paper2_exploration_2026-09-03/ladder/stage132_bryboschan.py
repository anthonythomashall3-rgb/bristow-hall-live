"""Stage 132: dating by the standard mechanical algorithm.  Bry and Boschan's monthly turning
point routine -- local extrema in a five-month neighbourhood, alternation enforced, phases of
at least five months and cycles of at least fifteen -- is the discipline's own answer to
'where did the series turn'.  It is run here on each coincident series and on the composite,
and its peaks and troughs are compared with the NBER's."""
exec(open("stage124_datemonth.py").read().split('def report(')[0])
import numpy as np, pandas as pd
M["unemployment rate"]=load(ODD+"01_labor_unemployment/monthly/UNRATE.csv")
def bb(s, k=5, minphase=5, mincycle=15):
    x=s.dropna(); v=x.values; n=len(v)
    cand=[]
    for i in range(k,n-k):
        w=v[i-k:i+k+1]
        if v[i]==w.max() and (w.max()>w.min()): cand.append((i,+1))
        elif v[i]==w.min() and (w.max()>w.min()): cand.append((i,-1))
    out=[]
    for i,t in cand:
        if out and out[-1][1]==t:
            j,_=out[-1]
            keep=i if ((t==+1 and v[i]>=v[j]) or (t==-1 and v[i]<=v[j])) else j
            out[-1]=(keep,t)
        else: out.append((i,t))
    ch=True
    while ch:
        ch=False
        for a in range(len(out)-1):
            i,t=out[a]; j,u=out[a+1]
            if j-i<minphase:
                drop=a if ((t==+1 and v[i]<v[j]) or (t==-1 and v[i]>v[j])) else a+1
                out.pop(drop); ch=True; break
    return [(x.index[i],t) for i,t in out]
def near(turns, target, kind, tol=12):
    c=[d for d,t in turns if t==kind and abs((d.to_period("M")-pd.Period(target,"M")).n)<=tol]
    if not c: return None
    return min(c,key=lambda d: abs((d.to_period("M")-pd.Period(target,"M")).n))
print("Bry-Boschan turning points, matched to the NBER date within a year")
print("%-38s %-7s %-8s %-7s %s"%("series","peaks","mean|m|","troughs","peak months / trough months"))
rows=[]
def comp(names):
    fr={}
    for n in names:
        s=M[n].astype(float); fr[n]=np.log(s).diff() if (s>0).all() else s.diff()
    d=pd.DataFrame(fr).dropna(how="all"); z=(d-d.mean())/d.std()
    return z.mean(axis=1,skipna=True).dropna().cumsum()
OBJ=dict(M)
OBJ["committee four composite"]=comp(["payrolls","real income less transfers","industrial production","real manufacturing and trade sales"])
OBJ["output pair composite"]=comp(["industrial production","capacity use"])
OBJ["jobs and income composite"]=comp(["payrolls","real income less transfers","household employment"])
for nm,s in OBJ.items():
    ss=np.log(s.astype(float)) if (s.dropna()>0).all() else s.astype(float)
    inv = nm in ("unemployment rate",)
    t=bb(-ss if inv else ss)
    pk=[near(t,p,+1) for p in PKM]; tr=[near(t,q,-1) for q in TRM]
    mp=[np.nan if d is None else (d.to_period("M")-pd.Period(PKM[i],"M")).n for i,d in enumerate(pk)]
    mt=[np.nan if d is None else (d.to_period("M")-pd.Period(TRM[i],"M")).n for i,d in enumerate(tr)]
    okp=[x for x in mp if x==x]; okt=[x for x in mt if x==x]
    rows.append((sum(1 for x in okp if x==0)+sum(1 for x in okt if x==0),
                 len(okp),len(okt),float(np.mean(np.abs(okp))) if okp else 9e9,
                 float(np.mean(np.abs(okt))) if okt else 9e9,nm,
                 [None if x!=x else int(x) for x in mp],[None if x!=x else int(x) for x in mt]))
rows.sort(key=lambda r:-r[0])
for ex,np_,nt,ap,at,nm,mp,mt in rows[:12]:
    print("%-38s %-7s %-8.2f %-7s %s"%(nm,"%d/9"%np_,ap,"%d/9"%nt,"peak %s"%mp))
    print("%-38s %-7s %-8.2f %-7s %s"%("","",at,"","trough %s"%mt))
