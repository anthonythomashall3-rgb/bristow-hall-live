"""Stage 166: detection by depth.  'Two consecutive negative quarters' counts a fall of a tenth
of a per cent twice as a recession; Finland has ten of them since 1990 and Norway eight.  If the
instrument finds the deep ones and misses the shallow ones, that is the behaviour wanted, not a
failure.  This stage sorts every foreign episode by how far output actually fell and reports
detection in each band."""
import os, numpy as np, pandas as pd, io, contextlib
BASE=os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03")
with contextlib.redirect_stdout(io.StringIO()):
    exec(open(os.path.join(BASE,"ladder","stage165_intl_verifiable.py")).read().split("for k,floor in")[0])
def depth(iso,P,T):
    g,sid=gdp(iso)
    if g is None: return None
    w=g[(g.index>=P-pd.DateOffset(months=6))&(g.index<=T+pd.DateOffset(months=3))]
    if len(w)<3: return None
    return float((w.min()/w.max()-1)*100)
def run2(iso,k=1,floor=0.30,delta=0.25,delta2=2.0,post=9):
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
    hits=[h for h in idx[((cnt>=k)&ufl).reindex(idx).fillna(False).values] if lo<=h<=hi]
    out=[]
    for P,T in eps:
        got=any(P-pd.DateOffset(months=6)<=h<=T+pd.DateOffset(months=post) for h in hits)
        out.append((iso,str(P.date())[:7],depth(iso,P,T),got))
    return out
ALL=[]
for iso in sorted(CC):
    r=run2(iso)
    if r: ALL+=r
d=pd.DataFrame(ALL,columns=["iso","peak","depth","found"]).dropna()
print("foreign episodes with two negative quarters, by how far output fell peak to trough")
print("%-24s %-8s %-10s %s"%("depth of the fall","episodes","detected","share"))
bands=[(-1e9,-4.0,"deeper than 4 per cent"),(-4.0,-2.0,"2 to 4 per cent"),(-2.0,-1.0,"1 to 2 per cent"),
       (-1.0,-0.5,"half a point to 1"),(-0.5,1e9,"shallower than half a point")]
for lo,hi,lab in bands:
    s=d[(d.depth>lo)&(d.depth<=hi)]
    if not len(s): continue
    print("%-24s %-8d %-10d %.0f%%"%(lab,len(s),s.found.sum(),100*s.found.mean()))
print("%-24s %-8d %-10d %.0f%%"%("all",len(d),d.found.sum(),100*d.found.mean()))
print("\ndeep episodes (worse than 2 per cent) that were missed:")
m=d[(d.depth<=-2.0)&(~d.found)]
for _,r in m.iterrows(): print("  %-4s %s  output fell %.1f per cent"%(r.iso,r.peak,r.depth))
print("\nthe United States, for comparison")
print(d[d.iso=="USA"].to_string(index=False))
