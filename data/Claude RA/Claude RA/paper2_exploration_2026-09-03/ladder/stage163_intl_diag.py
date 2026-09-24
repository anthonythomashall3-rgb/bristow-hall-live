"""Stage 163: where, exactly, does the foreign rule go wrong?  The aggregate figures hide the
answer.  This stage reports, country by country, how many channels exist, whether a curve gate
exists at all, how many recessions are found and how many false alarms are raised -- so that the
question 'is this the rule or the data' can be answered per country."""
import os, numpy as np, pandas as pd, io, contextlib
BASE=os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03")
with contextlib.redirect_stdout(io.StringIO()):
    exec(open(os.path.join(BASE,"ladder","stage148_intl_record.py")).read().split("for delta,delta2 in")[0])
def overlaps(P,T,eps2,slack=6):
    return any(p<=T+pd.DateOffset(months=slack) and t>=P-pd.DateOffset(months=slack) for p,t in eps2)
DELTA,DELTA2,FLOOR=0.25,2.0,0.30
def run(iso,k):
    ch=channels(iso)
    if ch is None: return None
    idx,S,gate=ch
    eps,src=oecd(iso)
    if eps is None: eps=technical(iso)[0]; src="gdp"
    eps=[(P,T) for P,T in eps if P>=idx[0] and T<=idx[-1]]
    if not eps: return None
    tech=technical(iso)[0]
    q=pd.Series(True,index=idx)
    for P,T in eps: q &= ~((idx>=P-pd.DateOffset(months=6))&(idx<=T+pd.DateOffset(months=9)))
    ufl=None
    for kk in ["unemployment rate","registered unemployment"]:
        if kk in S: ufl=(S[kk]>=FLOOR) if ufl is None else (ufl|(S[kk]>=FLOOR))
    hasU=ufl is not None
    ufl=pd.Series(True,index=idx) if ufl is None else ufl.reindex(idx).fillna(False).rolling(6,min_periods=1).max().fillna(0).astype(bool)
    cnt=pd.Series(0,index=idx); nch=0
    for kk,x in S.items():
        used=False
        a=scale(x,q&gate)
        if a is not None:
            z,rec=a; cnt=cnt+((z>=rec+DELTA)&gate).reindex(idx).fillna(False).astype(int); used=True
        b=scale(x,q&~gate)
        if b is not None:
            z,rec=b; cnt=cnt+((z>=rec+DELTA2)&~gate).reindex(idx).fillna(False).astype(int); used=True
        nch+=int(used)
    trig=(cnt>=k)&ufl
    hits=list(idx[trig.reindex(idx).fillna(False).values])
    a=na=0; miss=[]
    for P,T in eps:
        if not overlaps(P,T,tech): continue
        na+=1
        got=any(P-pd.DateOffset(months=6)<=h<=T+pd.DateOffset(months=3) for h in hits)
        a+=int(got)
        if not got: miss.append(str(P.date())[:7])
    runs=[]
    for h in hits:
        if runs and (h-runs[-1][1]).days<=200: runs[-1][1]=h
        else: runs.append([h,h])
    fa=[str(x.date())[:7] for x,y in runs if not any(P-pd.DateOffset(months=6)<=x<=T+pd.DateOffset(months=3) for P,T in eps)]
    return dict(nch=nch,gate=bool(gate.any()),hasU=hasU,det=a,n=na,miss=miss,fa=fa,qy=float(q.sum())/12.0)
for k in [1,2]:
    print("\n=== requiring %d channel%s, floor %.2f ==="%(k,"" if k==1 else "s",FLOOR))
    print("%-4s %-16s %-6s %-6s %-6s %-9s %-26s %s"%("iso","country","chans","gate","jobs","detected","recessions missed","false alarms"))
    T=E=F=0; Y=0.0
    for iso in sorted(CC):
        r=run(iso,k)
        if r is None: continue
        T+=r["det"]; E+=r["n"]; F+=len(r["fa"]); Y+=r["qy"]
        if r["n"]==0 and not r["fa"]: continue
        print("%-4s %-16s %-6d %-6s %-6s %-9s %-26s %s"%(iso,NAME.get(iso,iso),r["nch"],
              "yes" if r["gate"] else "no","yes" if r["hasU"] else "no",
              "%d/%d"%(r["det"],r["n"]),",".join(r["miss"])[:25],",".join(r["fa"])[:40]))
    print("TOTAL %d of %d recessions | %d false in %.0f quiet country-years"%(T,E,F,Y))
