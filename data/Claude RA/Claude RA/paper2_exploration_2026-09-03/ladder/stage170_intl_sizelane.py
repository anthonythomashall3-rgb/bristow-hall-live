"""Stage 170: a lane that fires on the SIZE of a move rather than on beating a record.  Four of
the deep foreign episodes still missed are the pandemic in Switzerland, Finland, Norway and
Korea, where the country's own records were set in the crises of the 1990s and 2020 -- violent as
it was -- did not beat them.  A record is a hard yardstick when a country has already lived
through something worse.  This lane asks instead how large the move is in that country's own
robust standard deviations, with the same number carried to every country."""
import os, numpy as np, pandas as pd, io, contextlib
BASE=os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03")
with contextlib.redirect_stdout(io.StringIO()):
    exec(open(os.path.join(BASE,"ladder","stage168_intl_fix.py")).read().split('print("%-6s %-7s')[0])
def depth(iso,P,T):
    g,sid=gdp(iso)
    if g is None: return None
    w=g[(g.index>=P-pd.DateOffset(months=6))&(g.index<=T+pd.DateOffset(months=3))]
    return None if len(w)<3 else float((w.min()/w.max()-1)*100)
def run2(iso,C,floor=0.30,delta=0.25,delta2=0.25,post=9,need_floor=True):
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
            u=S[kk]; f=(u>=floor); h=u.notna()
            ufl=f if ufl is None else (ufl|f); have=h if have is None else (have|h)
    if ufl is None: ufl=pd.Series(True,index=idx)
    else:
        ufl=ufl.reindex(idx).fillna(False)|(~have.reindex(idx).fillna(False))
        ufl=ufl.rolling(6,min_periods=1).max().fillna(0).astype(bool)
    cnt=pd.Series(0,index=idx); lane=pd.Series(False,index=idx)
    for kk,x in S.items():
        a=scale(x,q&gate)
        if a is not None:
            z,rec=a
            cnt=cnt+((z>=rec+delta)&gate).reindex(idx).fillna(False).astype(int)
            lane=lane|(z>=C).reindex(idx).fillna(False)
        b=scale(x,q&~gate)
        if b is not None:
            z,rec=b
            cnt=cnt+((z>=rec+delta2)&~gate).reindex(idx).fillna(False).astype(int)
            lane=lane|(z>=C).reindex(idx).fillna(False)
    trig=((cnt>=1)&ufl)|(lane&(ufl if need_floor else True))
    hits=[h for h in idx[trig.reindex(idx).fillna(False).values] if lo<=h<=hi]
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
print("%-8s %-7s %-24s %-17s %-16s %s"%("lane z","floor?","all episodes","deeper than 2pc","deeper than 4pc","false alarms"))
for need_floor in [True,False]:
  for C in [99,20,15,12,10,8,6,5]:
    ALL=[];F=0;Y=0.0;FA=[]
    for iso in sorted(CC):
        r=run2(iso,C,need_floor=need_floor)
        if r is None: continue
        ro,fa,qy=r; ALL+=ro; F+=len(fa); Y+=qy; FA+=[(iso,x) for x in fa]
    d=pd.DataFrame(ALL,columns=["iso","peak","depth","found"]).dropna()
    d2=d[d.depth<=-2.0]; d4=d[d.depth<=-4.0]
    print("%-8s %-7s %-24s %-17s %-16s %d in %.0f (%.4f/yr)%s"%(
        ("off" if C==99 else "%.0f"%C),"yes" if need_floor else "no",
        "%d of %d (%.0f%%)"%(d.found.sum(),len(d),100*d.found.mean()),
        "%d of %d (%.0f%%)"%(d2.found.sum(),len(d2),100*d2.found.mean()),
        "%d of %d (%.0f%%)"%(d4.found.sum(),len(d4),100*d4.found.mean()),F,Y,F/max(Y,1),
        ("  "+", ".join("%s %s"%x for x in FA[:5])) if 0<F<=5 else ""))
