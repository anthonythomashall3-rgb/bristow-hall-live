"""Stage 74: why were Germany 2012Q3, Italy 2001Q1 and Italy 2002Q4 missed?
For each, every channel's peak reading in the window, against its US threshold and
against that country's own quiet maximum."""
import os, json
import pandas as pd, numpy as np
BASE=os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03")
src=open(os.path.join(BASE,"ladder","stage51_intl_v2.py")).read().split("NBER = [(")[0]
exec(src)
MISS=[("DEU","2012-09-01","2013-03-01"),("ITA","2001-03-01","2001-12-01"),("ITA","2002-12-01","2003-09-01")]
ALLW={}
def stats_of(iso):
    ur=first("LRHUTTTT%sM156S"%CC[iso],"LRUNTTTT%sM156S"%CC[iso],"LRHUTTTT%sM156N"%CC[iso])
    iu=first("LMUNRRTT%sM156S"%CC[iso],"LMUNRRTT%sM156N"%CC[iso])
    st=first("IR3TIB01%sM156N"%CC[iso],"IRSTCI01%sM156N"%CC[iso])
    lt=first("IRLTLT01%sM156N"%CC[iso]); ip=first("%sPROINDMISMEI"%iso)
    idx=pd.DatetimeIndex(pd.date_range(ur.index[0],ur.index[-1],freq="MS"))
    u=ur.reindex(idx).interpolate(limit_area="inside")
    S={"u_gap": u.rolling(3).mean()-u.rolling(12).min()}
    if iu is not None:
        v=iu.reindex(idx).interpolate(limit_area="inside")
        S["iu_gap"]=v.rolling(3).mean()-v.rolling(12).min()
    if st is not None:
        s=st.reindex(idx,method="ffill"); S["rate_fall"]=-(s-s.shift(3))
    if ip is not None:
        p=ip.reindex(idx,method="ffill"); d=-(p/p.shift(1)-1)*100
        S["ip_2x"]=pd.concat([d,d.shift(1)],axis=1).min(axis=1)
    gate=pd.Series(False,index=idx)
    if st is not None and lt is not None:
        sp=lt.reindex(idx,method="ffill")-st.reindex(idx,method="ffill")
        gate=(sp<0).rolling(12,min_periods=1).max().fillna(0).astype(bool)
    return idx,S,gate,u
TH={"u_gap":(0.36,0.55),"iu_gap":(0.40,0.50),"rate_fall":(1.45,None),"ip_2x":(2.0,None)}
for iso,P,T in MISS:
    idx,S,gate,u=stats_of(iso)
    P=pd.Timestamp(P); T=pd.Timestamp(T)
    w=(idx>=P-pd.DateOffset(months=6))&(idx<=T)
    eps,_=technical(iso); q=pd.Series(True,index=idx)
    for a,b in eps: q &= ~((idx>=a-pd.DateOffset(months=6))&(idx<=b+pd.DateOffset(months=12)))
    print("\n=== %s  %s .. %s ===  gate armed in window: %s" % (iso,str(P.date())[:7],str(T.date())[:7],bool(gate[w].any())))
    print("  %-9s %8s %8s %8s %8s  %s" % ("channel","peak","fast","clause","quietmax","verdict"))
    for k,s in S.items():
        pk=float(s[w].max()) if s[w].notna().any() else float("nan")
        qm=float(s[q & s.notna()].max())
        f,c=TH[k]
        v=("FIRES(fast)" if (pk>=f and (k in("ip_2x",) or gate[w].any())) else
           ("fires only ungated" if pk>=f else
            ("above own quiet max" if pk>qm else "below own quiet max by %.2f"%(qm-pk))))
        print("  %-9s %8.3f %8s %8s %8.3f  %s" % (k,pk,f,c if c else "-",qm,v))
    print("  unemployment rate over the window: %.2f -> %.2f (rise %.2f pp)" %
          (float(u[w].iloc[0]),float(u[w].max()),float(u[w].max()-u[w].min())))
