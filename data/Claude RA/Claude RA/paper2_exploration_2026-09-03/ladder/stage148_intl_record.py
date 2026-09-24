"""Stage 148: the international replay with v14's own derivation.  Nothing is carried abroad
except the margin: every line is a country's own quiet record plus delta robust standard
deviations of that country's own quiet distribution.  The instrument is therefore identical in
form to the American one and contains no American number at all."""
import os, numpy as np, pandas as pd
BASE=os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03")
ROOT=os.path.expanduser("~/mnt/Onset Detector Data")
exec(open(os.path.join(BASE,"ladder","stage130_intl_wide.py")).read().split("def zs(")[0])

_gdp_orig=gdp
def gdp(iso):
    g,sid=_gdp_orig(iso)
    if g is not None: return g,sid
    for sid2 in ["NGDPRSAXDC%sQ"%CC[iso],"NAEXKP01%sQ652S"%CC[iso],"JPNRGDPEXP" if iso=="JPN" else None]:
        if sid2 is None: continue
        r=load(sid2)
        if r is not None and len(r)>=40: return r,sid2
    return None,None
def scale(x,mask):
    v=x[mask].dropna()
    if len(v)<36: return None
    med=float(np.median(v)); mad=float(np.median(np.abs(v-med)))*1.4826
    if not np.isfinite(mad) or mad<=0: return None
    z=(x-med)/mad
    rec=float(z[mask].dropna().max())
    return z,rec
def run(iso,delta,delta2):
    ch=channels(iso)
    if ch is None: return None
    idx,S,gate=ch
    eps,src=oecd(iso)
    if eps is None: eps=technical(iso)[0]; src="two negative quarters"
    eps=[(P,T) for P,T in eps if P>=idx[0] and T<=idx[-1]]
    if not eps: return None
    q=pd.Series(True,index=idx)
    for P,T in eps: q &= ~((idx>=P-pd.DateOffset(months=6))&(idx<=T+pd.DateOffset(months=9)))
    hit=pd.Series(False,index=idx); nch=0
    for k,x in S.items():
        a=scale(x,q&gate)
        if a is not None:
            z,rec=a; hit=hit|((z>=rec+delta)&gate); nch+=1
        b=scale(x,q&~gate)
        if b is not None:
            z,rec=b; hit=hit|((z>=rec+delta2)&~gate)
    hits=list(idx[hit.reindex(idx).fillna(False).values])
    det=0;lags=[]
    for P,T in eps:
        w=[h for h in hits if P-pd.DateOffset(months=6)<=h<=T+pd.DateOffset(months=3)]
        if w: det+=1; lags.append((w[0].to_period("M")-P.to_period("M")).n)
    runs=[]
    for h in hits:
        if runs and (h-runs[-1][1]).days<=200: runs[-1][1]=h
        else: runs.append([h,h])
    fa=[a for a,b in runs if not any(P-pd.DateOffset(months=6)<=a<=T+pd.DateOffset(months=3) for P,T in eps)]
    return det,len(eps),lags,len(fa),float(q.sum())/12.0,src,nch
for delta,delta2 in [(0.0,1.0),(0.25,2.0),(0.5,2.0),(1.0,3.0),(2.0,4.0)]:
    T=E=F=0; Y=0.0; L=[]; rowsUS=None
    lines=[]
    for iso in sorted(CC):
        r=run(iso,delta,delta2)
        if r is None: continue
        det,n,lags,nfa,qy,src,nch=r
        T+=det;E+=n;F+=nfa;Y+=qy;L+=lags
        lines.append("%-4s %-16s %-6d %-8s %-8s %-6d %-6.0f %s"%(iso,NAME.get(iso,iso),nch,"%d/%d"%(det,n),
            ("%+d"%int(np.median(lags))) if lags else "-",nfa,qy,src))
        if iso=="USA": rowsUS=lines[-1]
    print("\n=== delta=%.2f (gated) delta2=%.2f (open) ==="%(delta,delta2))
    print("%-4s %-16s %-6s %-8s %-8s %-6s %-6s %s"%("iso","country","chans","detected","med lag","false","quiet","chronology"))
    for l in lines: print(l)
    print("TOTAL %d of %d (%.0f%%) | %d false in %.0f quiet country-years (%.3f/yr) | median lag %s"%(
        T,E,100*T/max(E,1),F,Y,F/max(Y,1),("%+d"%int(np.median(L))) if L else "-"))
