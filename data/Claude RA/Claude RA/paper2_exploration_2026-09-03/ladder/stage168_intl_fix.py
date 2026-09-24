"""Stage 168: two defects in the foreign machine, and what fixing them costs.
(1) The floor asks whether unemployment is above its own twelve-month low.  Where the
    unemployment series has no data the comparison returns false and the floor blocks the call
    outright -- Denmark's pandemic quarter is missed for that reason alone.  A missing floor
    should not be a failed floor.
(2) The open lane's margin of two robust standard deviations was inherited from the American
    no-inversion clause, where it guards a single channel on days the curve is not inverted.
    Abroad, countries whose curve never arms run EVERYTHING through that lane, so the margin
    applies to their whole instrument.  Switzerland and Turkey are missed for that reason."""
import os, numpy as np, pandas as pd, io, contextlib
BASE=os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03")
with contextlib.redirect_stdout(io.StringIO()):
    exec(open(os.path.join(BASE,"ladder","stage165_intl_verifiable.py")).read().split("for k,floor in")[0])
def depth(iso,P,T):
    g,sid=gdp(iso)
    if g is None: return None
    w=g[(g.index>=P-pd.DateOffset(months=6))&(g.index<=T+pd.DateOffset(months=3))]
    return None if len(w)<3 else float((w.min()/w.max()-1)*100)
def run(iso,k,floor,delta,delta2,fix_floor,post=9):
    ch=channels(iso)
    if ch is None: return None
    idx,S,gate=ch
    g,sid=gdp(iso)
    if g is None or len(g)<40: return None
    lo=max(idx[0],pd.Timestamp(g.index.min())+pd.DateOffset(months=6)); hi=min(idx[-1],pd.Timestamp(g.index.max()))
    eps=[(P,T) for P,T in technical(iso)[0] if P>=lo and T<=hi]
    q=pd.Series(True,index=idx)
    for P,T in eps: q &= ~((idx>=P-pd.DateOffset(months=6))&(idx<=T+pd.DateOffset(months=post)))
    ufl=None; have=None
    for kk in ["unemployment rate","registered unemployment"]:
        if kk in S:
            u=S[kk]
            f=(u>=floor); h=u.notna()
            ufl=f if ufl is None else (ufl|f)
            have=h if have is None else (have|h)
    if ufl is None:
        ufl=pd.Series(True,index=idx)
    else:
        ufl=ufl.reindex(idx).fillna(False)
        if fix_floor:                                  # a missing floor is not a failed floor
            ufl=ufl | (~have.reindex(idx).fillna(False))
        ufl=ufl.rolling(6,min_periods=1).max().fillna(0).astype(bool)
    cnt=pd.Series(0,index=idx)
    for kk,x in S.items():
        a=scale(x,q&gate)
        if a is not None:
            z,rec=a; cnt=cnt+((z>=rec+delta)&gate).reindex(idx).fillna(False).astype(int)
        b=scale(x,q&~gate)
        if b is not None:
            z,rec=b; cnt=cnt+((z>=rec+delta2)&~gate).reindex(idx).fillna(False).astype(int)
    hits=[h for h in idx[((cnt>=k)&ufl).reindex(idx).fillna(False).values] if lo<=h<=hi]
    ro=[]
    for P,T in eps:
        got=any(P-pd.DateOffset(months=6)<=h<=T+pd.DateOffset(months=post) for h in hits)
        ro.append((iso,str(P.date())[:7],depth(iso,P,T),got))
    runs=[]
    for h in hits:
        if runs and (h-runs[-1][1]).days<=200: runs[-1][1]=h
        else: runs.append([h,h])
    fa=[str(x.date())[:7] for x,y in runs if not any(P-pd.DateOffset(months=6)<=x<=T+pd.DateOffset(months=post) for P,T in eps)]
    return ro,fa,float(q[(idx>=lo)&(idx<=hi)].sum())/12.0
print("%-6s %-7s %-7s %-24s %-17s %-16s %s"%("floorfix","gated","open","all episodes","deeper than 2pc","deeper than 4pc","false alarms"))
rows=[]
for fix in [False,True]:
  for delta,delta2 in [(0.25,2.0),(0.25,1.0),(0.25,0.5),(0.25,0.25),(0.0,0.25),(0.5,0.5)]:
    ALL=[];F=0;Y=0.0
    for iso in sorted(CC):
        r=run(iso,1,0.30,delta,delta2,fix)
        if r is None: continue
        ro,fa,qy=r; ALL+=ro; F+=len(fa); Y+=qy
    d=pd.DataFrame(ALL,columns=["iso","peak","depth","found"]).dropna()
    d2=d[d.depth<=-2.0]; d4=d[d.depth<=-4.0]
    rows.append((F,-d4.found.sum(),fix,delta,delta2,d,d2,d4,Y))
    print("%-6s %-7.2f %-7.2f %-24s %-17s %-16s %d in %.0f (%.4f/yr)"%(
        "yes" if fix else "no",delta,delta2,
        "%d of %d (%.0f%%)"%(d.found.sum(),len(d),100*d.found.mean()),
        "%d of %d (%.0f%%)"%(d2.found.sum(),len(d2),100*d2.found.mean()),
        "%d of %d (%.0f%%)"%(d4.found.sum(),len(d4),100*d4.found.mean()),F,Y,F/max(Y,1)))
