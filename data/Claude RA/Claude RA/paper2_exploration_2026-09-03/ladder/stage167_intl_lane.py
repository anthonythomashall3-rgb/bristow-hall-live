"""Stage 167: a foreign lane.  Seven of the twenty-four deep foreign episodes the rule misses are
the same one -- the pandemic quarter of 2020, which at home was caught by the volatility lane and
abroad by nothing.  Share prices are the one daily-to-monthly object available for most
countries, so a share-price collapse is tried as the foreign analogue of that lane, and the cost
in false alarms is measured."""
import os, numpy as np, pandas as pd, io, contextlib
BASE=os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03")
with contextlib.redirect_stdout(io.StringIO()):
    exec(open(os.path.join(BASE,"ladder","stage165_intl_verifiable.py")).read().split("for k,floor in")[0])
def depth(iso,P,T):
    g,sid=gdp(iso)
    if g is None: return None
    w=g[(g.index>=P-pd.DateOffset(months=6))&(g.index<=T+pd.DateOffset(months=3))]
    return None if len(w)<3 else float((w.min()/w.max()-1)*100)
def run(iso,k,floor,lane_th,lane_on,delta=0.25,delta2=2.0,post=9):
    ch=channels(iso)
    if ch is None: return None
    idx,S,gate=ch
    g,sid=gdp(iso)
    if g is None or len(g)<40: return None
    lo=max(idx[0],pd.Timestamp(g.index.min())+pd.DateOffset(months=6)); hi=min(idx[-1],pd.Timestamp(g.index.max()))
    eps=[(P,T) for P,T in technical(iso)[0] if P>=lo and T<=hi]
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
    lane=pd.Series(False,index=idx)
    if lane_on and "share prices" in S:
        sp=S["share prices"]                       # already the 6-month fall, positive = falling
        a=scale(sp,q)
        if a is not None:
            z,rec=a; lane=(z>=rec+lane_th).reindex(idx).fillna(False)
    trig=trig|lane
    hits=[h for h in idx[trig.values] if lo<=h<=hi]
    rec_out=[]
    for P,T in eps:
        got=any(P-pd.DateOffset(months=6)<=h<=T+pd.DateOffset(months=post) for h in hits)
        rec_out.append((iso,str(P.date())[:7],depth(iso,P,T),got))
    runs=[]
    for h in hits:
        if runs and (h-runs[-1][1]).days<=200: runs[-1][1]=h
        else: runs.append([h,h])
    fa=[str(x.date())[:7] for x,y in runs if not any(P-pd.DateOffset(months=6)<=x<=T+pd.DateOffset(months=post) for P,T in eps)]
    return rec_out,fa,float(q[(idx>=lo)&(idx<=hi)].sum())/12.0
print("%-6s %-9s %-24s %-16s %-14s %s"%("lane","margin","all episodes","deeper than 2pc","deeper than 4pc","false alarms"))
for lane_on,th in [(False,None),(True,0.0),(True,0.25),(True,0.5),(True,1.0),(True,2.0)]:
    ALL=[];F=0;Y=0.0;FA=[]
    for iso in sorted(CC):
        r=run(iso,1,0.30,th if th is not None else 99,lane_on)
        if r is None: continue
        ro,fa,qy=r; ALL+=ro; F+=len(fa); Y+=qy; FA+=[(iso,x) for x in fa]
    d=pd.DataFrame(ALL,columns=["iso","peak","depth","found"]).dropna()
    deep2=d[d.depth<=-2.0]; deep4=d[d.depth<=-4.0]
    print("%-6s %-9s %-24s %-16s %-14s %d in %.0f (%.4f/yr)%s"%(
        "yes" if lane_on else "no",("%.2f"%th) if th is not None else "-",
        "%d of %d (%.0f%%)"%(d.found.sum(),len(d),100*d.found.mean()),
        "%d of %d (%.0f%%)"%(deep2.found.sum(),len(deep2),100*deep2.found.mean()),
        "%d of %d (%.0f%%)"%(deep4.found.sum(),len(deep4),100*deep4.found.mean()),
        F,Y,F/max(Y,1),("  "+", ".join("%s %s"%x for x in FA[:5])) if 0<F<=5 else ""))
