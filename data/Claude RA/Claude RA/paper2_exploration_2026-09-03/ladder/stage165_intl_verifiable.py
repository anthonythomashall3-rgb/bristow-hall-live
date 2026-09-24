"""Stage 165: score the foreign rule only where it can be checked.  Every one of the eight
foreign 'false alarms' falls before 1995, and for most of those countries the quarterly GDP
series begins in 1995 -- so there is no evidence either way about whether output fell.  Australia
1983, the one case that can be checked, turns out to sit inside a real recession (two negative
quarters, 1982Q2 to 1983Q2) and to have been counted false only because the scoring window closed
three months too early.  This stage restricts the whole exercise to each country's own
GDP-covered period and scores against two negative quarters, which is the definition that can
actually be verified."""
import os, numpy as np, pandas as pd, io, contextlib
BASE=os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03")
with contextlib.redirect_stdout(io.StringIO()):
    exec(open(os.path.join(BASE,"ladder","stage148_intl_record.py")).read().split("for delta,delta2 in")[0])
def run(iso,k,floor,delta=0.25,delta2=2.0,post=9):
    ch=channels(iso)
    if ch is None: return None
    idx,S,gate=ch
    g,sid=gdp(iso)
    if g is None or len(g)<40: return None
    lo=max(idx[0],pd.Timestamp(g.index.min())+pd.DateOffset(months=6))
    hi=min(idx[-1],pd.Timestamp(g.index.max()))
    eps=[(P,T) for P,T in technical(iso)[0] if P>=lo and T<=hi]
    idx2=idx[(idx>=lo)&(idx<=hi)]
    if len(idx2)<60: return None
    q=pd.Series(True,index=idx)
    for P,T in eps: q &= ~((idx>=P-pd.DateOffset(months=6))&(idx<=T+pd.DateOffset(months=post)))
    ufl=None
    for kk in ["unemployment rate","registered unemployment"]:
        if kk in S: ufl=(S[kk]>=floor) if ufl is None else (ufl|(S[kk]>=floor))
    ufl=pd.Series(True,index=idx) if ufl is None else ufl.reindex(idx).fillna(False).rolling(6,min_periods=1).max().fillna(0).astype(bool)
    cnt=pd.Series(0,index=idx)
    for kk,x in S.items():
        a=scale(x,q&gate)
        if a is not None:
            z,rec=a; cnt=cnt+((z>=rec+delta)&gate).reindex(idx).fillna(False).astype(int)
        b=scale(x,q&~gate)
        if b is not None:
            z,rec=b; cnt=cnt+((z>=rec+delta2)&~gate).reindex(idx).fillna(False).astype(int)
    trig=((cnt>=k)&ufl).reindex(idx).fillna(False)
    hits=[h for h in idx[trig.values] if lo<=h<=hi]
    det=0; miss=[]
    for P,T in eps:
        got=any(P-pd.DateOffset(months=6)<=h<=T+pd.DateOffset(months=post) for h in hits)
        det+=int(got)
        if not got: miss.append(str(P.date())[:7])
    runs=[]
    for h in hits:
        if runs and (h-runs[-1][1]).days<=200: runs[-1][1]=h
        else: runs.append([h,h])
    fa=[str(x.date())[:7] for x,y in runs if not any(P-pd.DateOffset(months=6)<=x<=T+pd.DateOffset(months=post) for P,T in eps)]
    qy=float(q[(idx>=lo)&(idx<=hi)].sum())/12.0
    return det,len(eps),miss,fa,qy,str(lo.date()),str(hi.date())
for k,floor in [(1,0.30),(1,0.20),(2,0.30)]:
    print("\n=== %d channel%s, floor %.2f, scored against two negative quarters inside each country's GDP record ==="%(k,"" if k==1 else "s",floor))
    print("%-4s %-16s %-11s %-9s %-24s %s"%("iso","country","covered","detected","missed","false alarms"))
    T=E=F=0; Y=0.0
    for iso in sorted(CC):
        r=run(iso,k,floor)
        if r is None: continue
        det,n,miss,fa,qy,lo,hi=r
        T+=det; E+=n; F+=len(fa); Y+=qy
        if n or fa: print("%-4s %-16s %-11s %-9s %-24s %s"%(iso,NAME.get(iso,iso),lo[:4]+"-"+hi[:4],"%d/%d"%(det,n),",".join(miss)[:23],",".join(fa)[:34]))
    print("TOTAL %d of %d (%.0f%%) | %d false in %.0f quiet country-years (%.4f/yr)"%(T,E,100*T/max(E,1),F,Y,F/max(Y,1)))
