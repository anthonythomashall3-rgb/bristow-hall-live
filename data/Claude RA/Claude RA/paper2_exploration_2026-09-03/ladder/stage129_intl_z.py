"""Stage 129: the international replay with a scale-free rule.  Round 19 carried American
numbers abroad and quiet did not survive; round 25 let each country set its own calm maximum
and detection fell.  Here the only thing carried abroad is a number of robust standard
deviations -- the same c for every country -- and every scale is the country's own."""
import os, numpy as np, pandas as pd
BASE=os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03")
exec(open(os.path.join(BASE,"ladder","stage51_intl_v2.py")).read().split("NBER = [(")[0])
NBER=[("1969-12","1970-11"),("1973-11","1975-03"),("1980-01","1980-07"),("1981-07","1982-11"),
      ("1990-07","1991-03"),("2001-03","2001-11"),("2007-12","2009-06"),("2020-02","2020-04"),("2024-04","2024-08")]
NBER=[(pd.Timestamp(a+"-01"),pd.Timestamp(b+"-01")) for a,b in NBER]
def country(iso):
    ur=first("LRHUTTTT%sM156S"%CC[iso],"LRUNTTTT%sM156S"%CC[iso],"LRHUTTTT%sM156N"%CC[iso])
    if ur is None: return None
    iu=first("LMUNRRTT%sM156S"%CC[iso],"LMUNRRTT%sM156N"%CC[iso])
    st=first("IR3TIB01%sM156N"%CC[iso],"IRSTCI01%sM156N"%CC[iso])
    lt=first("IRLTLT01%sM156N"%CC[iso]); ip=first("%sPROINDMISMEI"%iso)
    idx=pd.DatetimeIndex(pd.date_range(ur.index[0],ur.index[-1],freq="MS"))
    u=ur.reindex(idx).interpolate(limit_area="inside")
    S={"u":u.rolling(3).mean()-u.rolling(12).min()}
    if iu is not None:
        v=iu.reindex(idx).interpolate(limit_area="inside"); S["iu"]=v.rolling(3).mean()-v.rolling(12).min()
    if st is not None:
        s=st.reindex(idx,method="ffill"); S["r"]=-(s-s.shift(3))
    if ip is not None:
        p=ip.reindex(idx,method="ffill"); d=-(p/p.shift(1)-1)*100
        S["ip"]=pd.concat([d,d.shift(1)],axis=1).min(axis=1)
    gate=pd.Series(False,index=idx)
    if st is not None and lt is not None:
        sp=lt.reindex(idx,method="ffill")-st.reindex(idx,method="ffill")
        gate=(sp<0).rolling(12,min_periods=1).max().fillna(0).astype(bool)
    eps=(NBER if iso=="USA" else technical(iso)[0])
    eps=[(P,T) for P,T in eps if P>=idx[0] and T<=idx[-1]]
    q=pd.Series(True,index=idx)
    ug=S["u"]; q3=(ug<0.20).rolling(3).min().fillna(0).astype(bool)
    for P,T in eps:
        later=q3.index[(q3.index>T)&q3.values]; close=later[0] if len(later) else idx[-1]
        q &= ~((idx>=P-pd.DateOffset(months=6))&(idx<=close))
    return idx,S,gate,eps,q
def zscale(x, mask):
    v=x[mask].dropna()
    if len(v)<24: return None
    med=float(np.median(v)); mad=float(np.median(np.abs(v-med)))*1.4826
    if not np.isfinite(mad) or mad<=0: return None
    return (x-med)/mad
def replay_country(idx,S,gate,eps,q,c,c2,warm=0):
    Zg=[];Zn=[]
    for k,x in S.items():
        a=zscale(x,q&gate); b=zscale(x,q&~gate)
        if a is not None: Zg.append(a)
        if b is not None: Zn.append(b)
    if not Zg and not Zn: return None
    mg=pd.concat(Zg,axis=1).max(axis=1) if Zg else pd.Series(-99.0,index=idx)
    mn=pd.concat(Zn,axis=1).max(axis=1) if Zn else pd.Series(-99.0,index=idx)
    trig=((mg>=c)&gate)|((mn>=c2)&~gate)
    trig=trig.reindex(idx).fillna(False)
    hits=list(idx[trig.values])
    det=0; lags=[]; used=set()
    for P,T in eps:
        w=[h for h in hits if P-pd.DateOffset(months=6)<=h<=T+pd.DateOffset(months=3)]
        if w: det+=1; lags.append((w[0].to_period("M")-P.to_period("M")).n); used.add(w[0])
    runs=[]
    for h in hits:
        if runs and (h-runs[-1][1]).days<=200: runs[-1][1]=h
        else: runs.append([h,h])
    fa=[a for a,b in runs if not any(P-pd.DateOffset(months=6)<=a<=T+pd.DateOffset(months=3) for P,T in eps)]
    qy=float(q.sum())/12.0
    return det,len(eps),lags,len(fa),qy,[str(x.date()) for x in fa[:4]]
for c,c2 in [(3.5,8.0),(4.25,8.0),(5.0,8.0),(4.25,6.0),(4.25,12.0),(6.0,10.0)]:
    T=F=E=0; Y=0.0; LAG=[]
    print("\n=== c=%.2f  c2=%.2f ==="%(c,c2))
    print("%-4s %-16s %-8s %-7s %-6s %s"%("iso","country","detected","med lag","false","quiet years"))
    for iso in sorted(CC):
        r=country(iso)
        if r is None: continue
        out=replay_country(*r,c=c,c2=c2)
        if out is None: continue
        det,n,lags,nfa,qy,fad=out
        T+=det; E+=n; F+=nfa; Y+=qy; LAG+=lags
        if n: print("%-4s %-16s %-8s %-7s %-6d %.0f"%(iso,NAME.get(iso,iso),"%d/%d"%(det,n),
              ("%+d"%int(np.median(lags))) if lags else "-",nfa,qy))
    print("TOTAL detected %d of %d (%.0f%%) | false episodes %d in %.0f quiet country-years (%.2f/yr) | median lag %s months"%(
        T,E,100*T/max(E,1),F,Y,F/max(Y,1),("%+d"%int(np.median(LAG))) if LAG else "-"))
