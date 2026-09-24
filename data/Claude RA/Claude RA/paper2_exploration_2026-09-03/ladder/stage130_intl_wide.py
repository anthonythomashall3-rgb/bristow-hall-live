"""Stage 130: widen the international test.  The harmonised unemployment rate exists on FRED
for twelve countries only, which is why earlier rounds covered so few.  Business and consumer
confidence, industrial production and the two interest rates cover twice as many, so the
instrument is rebuilt out of those, scored against the OECD's own peak-to-trough chronology
where it exists and against two negative quarters of GDP where it does not."""
import os, numpy as np, pandas as pd
BASE=os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03")
ROOT=os.path.expanduser("~/mnt/Onset Detector Data")
exec(open(os.path.join(BASE,"ladder","stage51_intl_v2.py")).read().split("NBER = [(")[0])
CHR=os.path.join(ROOT,"22_recession_chronologies/monthly/recession_probabilities")
def oecd(iso):
    for sid in ["%sRECM"%CC[iso],"%sRECDM"%CC[iso],"%sRECM"%iso,"%sRECDM"%iso]:
        p=os.path.join(CHR,sid+".csv")
        if os.path.exists(p):
            x=pd.read_csv(p); x.columns=["date","v"]; x["date"]=pd.to_datetime(x["date"])
            s=pd.Series(pd.to_numeric(x["v"],errors="coerce").values,index=pd.DatetimeIndex(x["date"]))
            s=(s.dropna()>0.5)
            eps=[];i=0;d=list(s.index);v=s.values
            while i<len(v):
                if v[i]:
                    j=i
                    while j+1<len(v) and v[j+1]: j+=1
                    if j-i+1>=3: eps.append((d[i],d[j]))
                    i=j+1
                else: i+=1
            if eps: return eps,sid
    return None,None
def channels(iso):
    ip=first("%sPROINDMISMEI"%iso)
    bc=first("BSCICP02%sM460S"%CC[iso]); csc=first("CSCICP02%sM460S"%CC[iso])
    ru=first("LMUNRRTT%sM156S"%CC[iso],"LMUNRRTT%sM156N"%CC[iso])
    hu=first("LRHUTTTT%sM156S"%CC[iso],"LRUNTTTT%sM156S"%CC[iso])
    st=first("IR3TIB01%sM156N"%CC[iso],"IRSTCI01%sM156N"%CC[iso]); lt=first("IRLTLT01%sM156N"%CC[iso])
    sp=first("SPASTT01%sM661N"%CC[iso],"SPASTT01%sM657N"%CC[iso])
    xp=first("XTEXVA01%sM667S"%CC[iso],"XTEXVA01%sM664N"%CC[iso])
    bc3=first("BSCICP03%sM665S"%CC[iso]); cs3=first("CSCICP03%sM665S"%CC[iso])
    hu2=first("LRHU24TT%sM156S"%CC[iso])
    base=[x for x in [ip,bc,csc,ru,hu,st,sp,xp,bc3,cs3,hu2] if x is not None]
    if not base: return None
    lo=min(x.index[0] for x in base); hi=max(x.index[-1] for x in base)
    idx=pd.DatetimeIndex(pd.date_range(lo,hi,freq="MS"))
    S={}
    if ip is not None:
        p=ip.reindex(idx,method="ffill"); d=-(p/p.shift(1)-1)*100
        S["industrial production"]=pd.concat([d,d.shift(1)],axis=1).min(axis=1)
        S["industrial production 3m"]=-(p/p.shift(3)-1)*100
    if bc is not None:
        b=bc.reindex(idx,method="ffill"); S["business confidence"]=-(b-b.shift(3)); S["business confidence level"]=b.rolling(12).max()-b
    if csc is not None:
        cq=csc.reindex(idx,method="ffill"); S["consumer confidence"]=-(cq-cq.shift(3))
    for nm,u in [("registered unemployment",ru),("unemployment rate",hu)]:
        if u is not None:
            v=u.reindex(idx).interpolate(limit_area="inside"); S[nm]=v.rolling(3).mean()-v.rolling(12).min()
    if st is not None:
        s=st.reindex(idx,method="ffill"); S["short rate fall"]=-(s-s.shift(3))
    if sp is not None:
        v=sp.reindex(idx,method="ffill"); S["share prices"]=-(v/v.shift(6)-1)*100
    if xp is not None:
        v=xp.reindex(idx,method="ffill"); S["exports"]=-(v/v.shift(6)-1)*100
    if bc3 is not None:
        v=bc3.reindex(idx,method="ffill"); S["business confidence, normalised"]=-(v-v.shift(3))
    if cs3 is not None:
        v=cs3.reindex(idx,method="ffill"); S["consumer confidence, normalised"]=-(v-v.shift(3))
    if hu2 is not None:
        v=hu2.reindex(idx).interpolate(limit_area="inside"); S["youth unemployment"]=v.rolling(3).mean()-v.rolling(12).min()
    gate=pd.Series(False,index=idx)
    if st is not None and lt is not None:
        sp=lt.reindex(idx,method="ffill")-st.reindex(idx,method="ffill")
        gate=(sp<0).rolling(12,min_periods=1).max().fillna(0).astype(bool)
    return idx,S,gate
def zs(x,mask):
    v=x[mask].dropna()
    if len(v)<36: return None
    med=float(np.median(v)); mad=float(np.median(np.abs(v-med)))*1.4826
    if not np.isfinite(mad) or mad<=0: return None
    return (x-med)/mad
def run(iso,c,c2):
    ch=channels(iso)
    if ch is None: return None
    idx,S,gate=ch
    eps,src=oecd(iso)
    if eps is None:
        eps=technical(iso)[0]; src="two negative quarters"
    eps=[(P,T) for P,T in eps if P>=idx[0] and T<=idx[-1]]
    if not eps: return None
    q=pd.Series(True,index=idx)
    for P,T in eps: q &= ~((idx>=P-pd.DateOffset(months=6))&(idx<=T+pd.DateOffset(months=9)))
    Zg=[];Zn=[]
    for k,x in S.items():
        a=zs(x,q&gate); b=zs(x,q&~gate)
        if a is not None: Zg.append(a)
        if b is not None: Zn.append(b)
    mg=pd.concat(Zg,axis=1).max(axis=1) if Zg else pd.Series(-99.0,index=idx)
    mn=pd.concat(Zn,axis=1).max(axis=1) if Zn else pd.Series(-99.0,index=idx)
    trig=(((mg>=c)&gate)|((mn>=c2)&~gate)).reindex(idx).fillna(False)
    hits=list(idx[trig.values])
    det=0;lags=[]
    for P,T in eps:
        w=[h for h in hits if P-pd.DateOffset(months=6)<=h<=T+pd.DateOffset(months=3)]
        if w: det+=1; lags.append((w[0].to_period("M")-P.to_period("M")).n)
    runs=[]
    for h in hits:
        if runs and (h-runs[-1][1]).days<=200: runs[-1][1]=h
        else: runs.append([h,h])
    fa=[a for a,b in runs if not any(P-pd.DateOffset(months=6)<=a<=T+pd.DateOffset(months=3) for P,T in eps)]
    return det,len(eps),lags,len(fa),float(q.sum())/12.0,src,len(S)
for c,c2 in [(3.5,8.0),(4.25,8.0),(5.0,10.0),(6.0,12.0),(7.0,14.0)]:
    print("\n=== c=%.2f c2=%.2f ==="%(c,c2))
    print("%-4s %-16s %-6s %-8s %-8s %-6s %-8s %s"%("iso","country","chans","detected","med lag","false","quiet yr","chronology"))
    T=E=F=0; Y=0.0; L=[]
    for iso in sorted(CC):
        r=run(iso,c,c2)
        if r is None: continue
        det,n,lags,nfa,qy,src,nch=r
        T+=det;E+=n;F+=nfa;Y+=qy;L+=lags
        print("%-4s %-16s %-6d %-8s %-8s %-6d %-8.0f %s"%(iso,NAME.get(iso,iso),nch,"%d/%d"%(det,n),
              ("%+d"%int(np.median(lags))) if lags else "-",nfa,qy,src))
    print("TOTAL %d of %d (%.0f%%) | %d false in %.0f quiet country-years (%.3f/yr) | median lag %s"%(
        T,E,100*T/max(E,1),F,Y,F/max(Y,1),("%+d"%int(np.median(L))) if L else "-"))
