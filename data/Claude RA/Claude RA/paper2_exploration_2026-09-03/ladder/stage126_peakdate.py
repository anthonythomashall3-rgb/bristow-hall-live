"""Stage 126: dating the PEAK.  The trough is easy because output turns sharply; the peak is
a plateau, so an argmax over a noisy level is unstable.  This stage tries peak definitions
that do not depend on a single month's reading: smoothed levels, and 'the last month the
composite was at its high and never regained it for k months'."""
exec(open("stage124_datemonth.py").read().split('def report(')[0])
import numpy as np, pandas as pd
def comp(names):
    fr={}
    for n in names:
        s=M[n].astype(float); fr[n]=np.log(s).diff() if (s>0).all() else s.diff()
    d=pd.DataFrame(fr).dropna(how="all"); z=(d-d.mean())/d.std()
    return z.mean(axis=1,skipna=True).dropna().cumsum()
FOUR=["payrolls","real income less transfers","industrial production","real manufacturing and trade sales"]
PANELS={"committee four":FOUR,
        "income and jobs":["payrolls","real income less transfers","household employment"],
        "jobs pair":["payrolls","household employment"],
        "income alone":["real income less transfers"],
        "jobs, income, hours":["payrolls","real income less transfers","average weekly hours"],
        "four + hours + capacity":FOUR+["average weekly hours","capacity use"]}
def last_high(w, k):
    """last month whose level is the running maximum and is not exceeded for the next k months"""
    v=w.values; n=len(v); best=None
    for i in range(n):
        if v[i]!=max(v[:i+1]): continue
        if i+1>=n: continue
        if max(v[i+1:min(n,i+1+k)])<=v[i]: best=i
    return w.index[best] if best is not None else w.index[int(np.argmax(v))]
def score(lab, s, back, fwd, sm, kind, k=None):
    x=s.rolling(sm,center=True).mean().dropna() if sm>1 else s
    ds=[]; mo=[]
    for i,a in enumerate(ALARM):
        w=x[(x.index>=a-pd.Timedelta(days=back))&(x.index<=a+pd.Timedelta(days=fwd))].dropna()
        if len(w)<6: return None
        d=last_high(w,k) if kind=="lasthigh" else w.idxmax()
        ds.append(((d.to_period("M")+1).to_timestamp()-FIRST[i]).days)
        mo.append((d.to_period("M")-pd.Period(PKM[i],"M")).n)
    return (float(np.mean(np.abs(ds))),sum(1 for x_ in ds if abs(x_)<=7),sum(1 for x_ in mo if x_==0),lab,[int(x_) for x_ in mo])
R=[]
for pn,names in PANELS.items():
    have=[n for n in names if n in M]
    if not have: continue
    c=comp(have) if len(have)>1 else np.log(M[have[0]].astype(float))
    for back,fwd in [(180,180),(270,180),(365,180),(180,270),(120,240)]:
        for sm in [1,3,5]:
            r=score(pn,c,back,fwd,sm,"max")
            if r: R.append(r+(back,fwd,sm,"argmax"))
            for k in [3,6,9,12]:
                r=score(pn,c,back,fwd,sm,"lasthigh",k)
                if r: R.append(r+(back,fwd,sm,"lasthigh k=%d"%k))
R.sort(key=lambda t:(-t[2],t[0]))
print("PEAK month, ranked by how often the exact NBER peak month is named")
print("%-24s %-9s %-6s %-6s %-7s %-6s %s"%("panel","rule","back","fwd","mean|d|","exact","months from the NBER peak"))
seen=set()
for a,c7,ex,lab,mo,back,fwd,sm,kind in R[:400]:
    key=(lab,tuple(mo))
    if key in seen: continue
    seen.add(key)
    print("%-24s %-9s %-6d %-6d %-7.1f %-6d %s"%(lab,kind.split()[0][:9],back,fwd,a,ex,mo))
    if len(seen)>=14: break
