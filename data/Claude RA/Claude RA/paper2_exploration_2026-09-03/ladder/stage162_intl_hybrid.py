"""Stage 162: abroad, agreement works.  Two channels agreeing removes every false alarm in 718
quiet country-years but costs half the detections, because a single very loud channel is then
ignored and because several countries have only one usable channel at all.  The repair is a
hybrid: fire on ONE channel if it is loud enough, or on TWO if they are merely above their own
records -- and never demand two channels of a country that has only one."""
import os, numpy as np, pandas as pd, io, contextlib
BASE=os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03")
with contextlib.redirect_stdout(io.StringIO()):
    exec(open(os.path.join(BASE,"ladder","stage148_intl_record.py")).read().split("for delta,delta2 in")[0])
def overlaps(P,T,eps2,slack=6):
    return any(p<=T+pd.DateOffset(months=slack) and t>=P-pd.DateOffset(months=slack) for p,t in eps2)
def run(iso,dlo,dhi,dlo2,dhi2,floor,adaptive=True):
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
    for k in ["unemployment rate","registered unemployment"]:
        if k in S: ufl=(S[k]>=floor) if ufl is None else (ufl|(S[k]>=floor))
    ufl=pd.Series(True,index=idx) if ufl is None else ufl.reindex(idx).fillna(False).rolling(6,min_periods=1).max().fillna(0).astype(bool)
    lo=pd.Series(0,index=idx); hi=pd.Series(False,index=idx); nch=0
    for k,x in S.items():
        used=False
        a=scale(x,q&gate)
        if a is not None:
            z,rec=a
            lo=lo+((z>=rec+dlo)&gate).reindex(idx).fillna(False).astype(int)
            hi=hi|((z>=rec+dhi)&gate).reindex(idx).fillna(False)
            used=True
        b=scale(x,q&~gate)
        if b is not None:
            z,rec=b
            lo=lo+((z>=rec+dlo2)&~gate).reindex(idx).fillna(False).astype(int)
            hi=hi|((z>=rec+dhi2)&~gate).reindex(idx).fillna(False)
            used=True
        nch+=int(used)
    need=2 if (nch>=2 or not adaptive) else 1
    trig=(hi|(lo>=need))&ufl
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
    return a,na,b_,nb,len(fa),float(q.sum())/12.0,nch
print("%-6s %-6s %-7s %-24s %-20s %s"%("2-ch","1-ch","floor","recessions detected","slowdowns","false alarms"))
best=[]
for dlo in [0.0,0.25,0.5]:
  for dhi in [1.5,2.0,2.5,3.0,4.0,6.0]:
    for floor in [0.2,0.3,0.4]:
        TA=EA=TB=EB=F=0; Y=0.0
        for iso in sorted(CC):
            r=run(iso,dlo,dhi,dlo+2.0,dhi+2.0,floor)
            if r is None: continue
            a,na,b_,nb,nf,qy,nch=r
            TA+=a;EA+=na;TB+=b_;EB+=nb;F+=nf;Y+=qy
        best.append((F,-TA,dlo,dhi,floor,TA,EA,TB,EB,Y))
        print("%-6.2f %-6.2f %-7.2f %-24s %-20s %d in %.0f (%.4f/yr)"%(dlo,dhi,floor,
            "%d of %d (%.0f%%)"%(TA,EA,100*TA/max(EA,1)),"%d of %d (%.0f%%)"%(TB,EB,100*TB/max(EB,1)),F,Y,F/max(Y,1)))
best.sort()
print("\nzero-false settings, ranked by detection:")
for F,negT,dlo,dhi,floor,TA,EA,TB,EB,Y in [b for b in best if b[0]==0][:6]:
    print("  two channels at record+%.2f or one at record+%.2f, floor %.2f -> %d of %d recessions (%.0f%%), %d of %d slowdowns"%(
        dlo,dhi,floor,TA,EA,100*TA/max(EA,1),TB,EB))
