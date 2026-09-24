"""Stage 164: the foreign false alarms are early-sample.  Austria 1994, Belgium 1993, Greece
1994, Ireland 1987, New Zealand 1983 and 1987, Portugal 1994, the United Kingdom 1985 -- eight
of them, all in the first years of each country's data.  A record set on five years of history is
not a record.  This stage refuses to let a channel fire until it has enough history behind it."""
import os, numpy as np, pandas as pd, io, contextlib
BASE=os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03")
with contextlib.redirect_stdout(io.StringIO()):
    exec(open(os.path.join(BASE,"ladder","stage148_intl_record.py")).read().split("for delta,delta2 in")[0])
def overlaps(P,T,eps2,slack=6):
    return any(p<=T+pd.DateOffset(months=slack) and t>=P-pd.DateOffset(months=slack) for p,t in eps2)
def run(iso,k,floor,warm_years,delta=0.25,delta2=2.0):
    ch=channels(iso)
    if ch is None: return None
    idx,S,gate=ch
    eps,src=oecd(iso)
    if eps is None: eps=technical(iso)[0]
    eps=[(P,T) for P,T in eps if P>=idx[0] and T<=idx[-1]]
    if not eps: return None
    tech=technical(iso)[0]
    q=pd.Series(True,index=idx)
    for P,T in eps: q &= ~((idx>=P-pd.DateOffset(months=6))&(idx<=T+pd.DateOffset(months=9)))
    ufl=None
    for kk in ["unemployment rate","registered unemployment"]:
        if kk in S: ufl=(S[kk]>=floor) if ufl is None else (ufl|(S[kk]>=floor))
    ufl=pd.Series(True,index=idx) if ufl is None else ufl.reindex(idx).fillna(False).rolling(6,min_periods=1).max().fillna(0).astype(bool)
    cnt=pd.Series(0,index=idx)
    for kk,x in S.items():
        first=x.dropna().index.min()
        ok=pd.Series(idx>=first+pd.DateOffset(years=warm_years),index=idx)
        a=scale(x,q&gate)
        if a is not None:
            z,rec=a; cnt=cnt+(((z>=rec+delta)&gate).reindex(idx).fillna(False)&ok).astype(int)
        b=scale(x,q&~gate)
        if b is not None:
            z,rec=b; cnt=cnt+(((z>=rec+delta2)&~gate).reindex(idx).fillna(False)&ok).astype(int)
    trig=(cnt>=k)&ufl
    hits=list(idx[trig.reindex(idx).fillna(False).values])
    a=na=0
    for P,T in eps:
        if not overlaps(P,T,tech): continue
        na+=1
        a+=int(any(P-pd.DateOffset(months=6)<=h<=T+pd.DateOffset(months=3) for h in hits))
    runs=[]
    for h in hits:
        if runs and (h-runs[-1][1]).days<=200: runs[-1][1]=h
        else: runs.append([h,h])
    fa=[str(x.date())[:7] for x,y in runs if not any(P-pd.DateOffset(months=6)<=x<=T+pd.DateOffset(months=3) for P,T in eps)]
    qy=float((q & pd.Series(True,index=idx)).sum())/12.0
    return a,na,fa,qy
print("%-6s %-6s %-7s %-24s %s"%("k","floor","warm-up","recessions detected","false alarms"))
grid=[]
for k in [1,2]:
  for floor in [0.2,0.3,0.4]:
    for warm in [0,5,8,10,12,15]:
        T=E=F=0; Y=0.0; FA=[]
        for iso in sorted(CC):
            r=run(iso,k,floor,warm)
            if r is None: continue
            a,na,fa,qy=r; T+=a; E+=na; F+=len(fa); Y+=qy; FA+=[(iso,x) for x in fa]
        grid.append((F,-T,k,floor,warm,T,E,Y,FA))
        print("%-6d %-6.2f %-7d %-24s %d in %.0f (%.4f/yr)%s"%(k,floor,warm,
              "%d of %d (%.0f%%)"%(T,E,100*T/max(E,1)),F,Y,F/max(Y,1),
              "   "+", ".join("%s %s"%x for x in FA[:6]) if F and F<=6 else ""))
grid.sort()
print("\nbest by false alarms then detection:")
for F,negT,k,floor,warm,T,E,Y,FA in grid[:6]:
    print("  k=%d floor=%.2f warm-up=%d yr -> %d of %d recessions (%.0f%%), %d false in %.0f quiet country-years"%(
        k,floor,warm,T,E,100*T/max(E,1),F,Y))
