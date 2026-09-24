"""Stage 161: why the foreign rule fires falsely and the American one does not.  At home two
things suppress a spurious call: the curve gate and the claims floor -- no episode may open
unless layoffs are already rising.  Abroad there is no weekly claims series and many countries
have no usable curve, so the machine fires on a single channel with nothing holding it back.
This stage adds a foreign analogue of the floor -- unemployment must already be above its own
twelve-month low -- and, separately, tries requiring two channels to agree."""
import os, numpy as np, pandas as pd, io, contextlib
BASE=os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03")
with contextlib.redirect_stdout(io.StringIO()):
    exec(open(os.path.join(BASE,"ladder","stage148_intl_record.py")).read().split("for delta,delta2 in")[0])
def overlaps(P,T,eps2,slack=6):
    for p,t in eps2:
        if p<=T+pd.DateOffset(months=slack) and t>=P-pd.DateOffset(months=slack): return True
    return False
def country_run(iso,delta,delta2,floor,kneed):
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
    # the floor: an unemployment-type channel above its own twelve-month low
    ufl=None
    for k in ["unemployment rate","registered unemployment"]:
        if k in S:
            ufl=(S[k]>=floor) if ufl is None else (ufl|(S[k]>=floor))
    if ufl is None: ufl=pd.Series(True,index=idx)
    ufl=ufl.reindex(idx).fillna(False)
    ufl=ufl.rolling(6,min_periods=1).max().fillna(0).astype(bool)
    cnt=pd.Series(0,index=idx)
    for k,x in S.items():
        a=scale(x,q&gate)
        if a is not None:
            z,rec=a; cnt=cnt+((z>=rec+delta)&gate).reindex(idx).fillna(False).astype(int)
        b=scale(x,q&~gate)
        if b is not None:
            z,rec=b; cnt=cnt+((z>=rec+delta2)&~gate).reindex(idx).fillna(False).astype(int)
    trig=(cnt>=kneed)&ufl
    hits=list(idx[trig.reindex(idx).fillna(False).values])
    a=b_=na=nb=0
    for P,T in eps:
        got=any(P-pd.DateOffset(months=6)<=h<=T+pd.DateOffset(months=3) for h in hits)
        if overlaps(P,T,tech): na+=1; a+=int(got)
        else: nb+=1; b_+=int(got)
    runs=[]
    for h in hits:
        if runs and (h-runs[-1][1]).days<=200: runs[-1][1]=h
        else: runs.append([h,h])
    fa=[x for x,y in runs if not any(P-pd.DateOffset(months=6)<=x<=T+pd.DateOffset(months=3) for P,T in eps)]
    return a,na,b_,nb,len(fa),float(q.sum())/12.0
print("%-7s %-7s %-7s %-6s %-22s %-20s %s"%("delta","delta2","floor","k","recessions detected","slowdowns","false alarms"))
for delta,delta2 in [(0.25,2.0),(0.5,2.0),(1.0,3.0)]:
  for floor in [0.0,0.1,0.2,0.3,0.5]:
    for k in [1,2]:
        TA=EA=TB=EB=F=0; Y=0.0
        for iso in sorted(CC):
            r=country_run(iso,delta,delta2,floor,k)
            if r is None: continue
            a,na,b_,nb,nf,qy=r
            TA+=a;EA+=na;TB+=b_;EB+=nb;F+=nf;Y+=qy
        print("%-7.2f %-7.2f %-7.2f %-6d %-22s %-20s %d in %.0f quiet country-years (%.3f/yr)"%(
            delta,delta2,floor,k,"%d of %d (%.0f%%)"%(TA,EA,100*TA/max(EA,1)),
            "%d of %d (%.0f%%)"%(TB,EB,100*TB/max(EB,1)),F,Y,F/max(Y,1)))
