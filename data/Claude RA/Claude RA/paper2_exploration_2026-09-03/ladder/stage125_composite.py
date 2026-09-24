"""Stage 125: a coincident composite for dating.  The dating committee reads four monthly
series together; a single one of them is noisy, so this stage builds the standard composite
(equal-weight standardised monthly growth, cumulated to a level) and dates the peak and the
trough from the composite's own turning point inside a window anchored on the machine's call."""
exec(open("stage124_datemonth.py").read().split('def report(')[0])
import numpy as np, pandas as pd, itertools
def comp(names, lo=None):
    fr={}
    for n in names:
        s=M[n].astype(float)
        g=np.log(s).diff() if (s>0).all() else s.diff()
        fr[n]=g
    d=pd.DataFrame(fr).dropna(how="all")
    z=(d-d.mean())/d.std()
    a=z.mean(axis=1,skipna=True).dropna()
    return a.cumsum()
FOUR=["payrolls","real income less transfers","industrial production","real manufacturing and trade sales"]
PANELS={"committee four":FOUR,
        "four + hours":FOUR+["average weekly hours"],
        "four + capacity use":FOUR+["capacity use"],
        "employment pair":["payrolls","household employment"],
        "output pair":["industrial production","capacity use"],
        "four + ADS":FOUR+["ADS (monthly mean)"],
        "everything":[k for k in M if k!="ADS (monthly mean)"]}
def turn(s, a, back, fwd, kind):
    w=s[(s.index>=a-pd.Timedelta(days=back))&(s.index<=a+pd.Timedelta(days=fwd))].dropna()
    if len(w)<6: return None
    return w.idxmax() if kind=="max" else w.idxmin()
def line(lab, s, anchors, targets, refm, kind, back, fwd):
    ds=[];mo=[]
    for i,a in enumerate(anchors):
        d=turn(s,a,back,fwd,kind)
        if d is None: ds.append(np.nan); mo.append(np.nan); continue
        ds.append(((d.to_period("M")+1).to_timestamp()-targets[i]).days)
        mo.append((d.to_period("M")-pd.Period(refm[i],"M")).n)
    v=[x for x in ds if x==x]
    return (float(np.mean(np.abs(v))) if len(v)==9 else np.inf, sum(1 for x in v if abs(x)<=7), lab,
            [int(x) for x in mo] if len(v)==9 else None)
print("PEAK, composite level turning point")
print("%-24s %-6s %-8s %-7s %-6s %s"%("panel","back","forward","mean|d|","exact","months from the NBER peak"))
R=[]
for pn,names in PANELS.items():
    have=[n for n in names if n in M]
    if len(have)<2: continue
    c=comp(have)
    for back,fwd in [(365,90),(180,180),(270,120),(540,120)]:
        a,cnt,lab,mo=line(pn,c,ALARM,FIRST,PKM,"max",back,fwd)
        if mo is None: continue
        R.append((a,cnt,pn,back,fwd,mo))
R.sort()
for a,cnt,pn,back,fwd,mo in R[:12]:
    print("%-24s %-6d %-8d %-7.1f %-6d %s"%(pn,back,fwd,a,sum(1 for x in mo if x==0),mo))
print("\nTROUGH, composite level turning point")
print("%-24s %-6s %-8s %-7s %-6s %s"%("panel","back","forward","mean|d|","exact","months from the NBER trough"))
R2=[]
for pn,names in PANELS.items():
    have=[n for n in names if n in M]
    if len(have)<2: continue
    c=comp(have)
    for back,fwd in [(365,180),(270,120),(540,240),(180,240)]:
        a,cnt,lab,mo=line(pn,c,ENDC,LAST,TRM,"min",back,fwd)
        if mo is None: continue
        R2.append((a,cnt,pn,back,fwd,mo))
R2.sort()
for a,cnt,pn,back,fwd,mo in R2[:12]:
    print("%-24s %-6d %-8d %-7.1f %-6d %s"%(pn,back,fwd,a,sum(1 for x in mo if x==0),mo))
print("\nsingle best objects for reference:")
for nm in ["capacity use","industrial production","real income less transfers","payrolls"]:
    if nm in M:
        a,c,_,mo=line(nm,M[nm],ALARM,FIRST,PKM,"max",180,180); print("  peak   %-34s mean|d| %5.1f  exact %d  %s"%(nm,a,sum(1 for x in mo if x==0),mo))
for nm in ["capacity use","industrial production","real manufacturing and trade sales","payrolls"]:
    if nm in M:
        a,c,_,mo=line(nm,M[nm],ENDC,LAST,TRM,"min",365,180); print("  trough %-34s mean|d| %5.1f  exact %d  %s"%(nm,a,sum(1 for x in mo if x==0),mo))
