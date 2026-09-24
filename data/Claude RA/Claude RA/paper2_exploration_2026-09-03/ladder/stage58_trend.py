# Round 19f: a baseline-stability guard on the unemployment channels.
# The 12-month minimum that the gap is measured against must itself be stable:
# min_12(t) - min_12(t-24) <= X pp.  Structural drift is blocked; a cyclical
# break is not.  Tested on the panel first.
import os, json
import pandas as pd, numpy as np
BASE = os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03")
src = open(os.path.join(BASE,"ladder","stage51_intl_v2.py")).read().split("NBER = [(")[0]
exec(src)
NBER=[("1948-11","1949-10"),("1953-07","1954-05"),("1957-08","1958-04"),("1960-04","1961-02"),
      ("1969-12","1970-11"),("1973-11","1975-03"),("1980-01","1980-07"),("1981-07","1982-11"),
      ("1990-07","1991-03"),("2001-03","2001-11"),("2007-12","2009-06"),("2020-02","2020-04"),
      ("2024-04","2024-08")]
NBER=[(pd.Timestamp(a+"-01"),pd.Timestamp(b+"-01")) for a,b in NBER]

def build3(iso, X=None):
    ur = first("LRHUTTTT%sM156S"%CC[iso],"LRUNTTTT%sM156S"%CC[iso],"LRHUTTTT%sM156N"%CC[iso])
    if ur is None: return None
    iu = first("LMUNRRTT%sM156S"%CC[iso],"LMUNRRTT%sM156N"%CC[iso])
    st = first("IR3TIB01%sM156N"%CC[iso],"IRSTCI01%sM156N"%CC[iso])
    lt = first("IRLTLT01%sM156N"%CC[iso]); ip = first("%sPROINDMISMEI"%iso)
    idx = pd.DatetimeIndex(pd.date_range(ur.index[0], ur.index[-1], freq="MS"))
    u = ur.reindex(idx).interpolate(limit_area="inside")
    m12 = u.rolling(12).min(); ug = u.rolling(3).mean() - m12
    stable = pd.Series(True, index=idx) if X is None else ((m12 - m12.shift(24)) <= X)
    gate = pd.Series(False, index=idx)
    if st is not None and lt is not None:
        sp = lt.reindex(idx, method="ffill") - st.reindex(idx, method="ffill")
        gate = (sp<0).rolling(12,min_periods=1).max().fillna(0).astype(bool)
    f = {}
    f["u_fast"] = (ug>=TH["u_fast"]) & gate & stable
    f["u_back"] = (ug>=TH["u_back"]) & stable
    if iu is not None:
        v = iu.reindex(idx).interpolate(limit_area="inside")
        n12 = v.rolling(12).min(); g2 = v.rolling(3).mean()-n12
        st2 = pd.Series(True,index=idx) if X is None else ((n12-n12.shift(24))<=X)
        f["iu_fast"]=(g2>=TH["iu_fast"])&gate&st2; f["iu_back"]=(g2>=TH["iu_back"])&st2
    if st is not None:
        s = st.reindex(idx,method="ffill"); d = s-s.shift(3)
        f["r_fast"]=(d<=-TH["r_fast"])&gate; f["r_back"]=(d<=-TH["r_back"])
    if ip is not None:
        p = ip.reindex(idx,method="ffill"); d=(p/p.shift(1)-1)*100
        f["ip_back"]=(d<=TH["ip_back"])&(d.shift(1)<=TH["ip_back"])
    return dict(idx=idx, f={k:v.fillna(False).astype(bool) for k,v in f.items()}, ug=ug)

def eps_of(b):
    idx, ug = b["idx"], b["ug"]
    ev = sorted(((pd.Timestamp(d)+pd.DateOffset(months=LAG[k])).replace(day=1),k)
                for k,v in b["f"].items() for d in idx[v.values])
    q3 = (ug<0.20).rolling(3).min().fillna(0).astype(bool)
    out, until = [], None
    for cm,k in ev:
        if until is not None and cm<=until: continue
        later = q3.index[(q3.index>cm)&q3.values]
        until = later[0] if len(later) else idx[-1]
        out.append((cm,until,k))
    return out

print("%-30s %-9s %-6s %-13s %s" % ("baseline-stability guard","covered","FA","1 per N yrs","median lag"))
for X in [None, 2.0, 1.5, 1.0, 0.75, 0.5, 0.25]:
    cov=tot=fas=0; yrs=0.0; L=[]
    for iso in sorted(CC):
        b = build3(iso, X)
        if b is None: continue
        mach = eps_of(b); lo,hi = b["idx"][0], b["idx"][-1]
        tech,_ = technical(iso); tech=[(P,T) for P,T in tech if P>=lo and T<=hi]
        if len(tech)<2: continue
        oec=[(P,T) for P,T in oecd(iso) if P>=lo and T<=hi]
        ref=[(P,T) for P,T in NBER if P>=lo and T<=hi] if iso=="USA" else []
        allw=tech+oec+ref; yrs+=(hi-lo).days/365.25; used=set()
        for P,T in tech:
            c=[m for m in mach if m[0]<=T and m[1]>=P]; tot+=1
            if c: cov+=1; used.add(c[0]); L.append((c[0][0].year-P.year)*12+(c[0][0].month-P.month))
        fas += sum(1 for m in mach if m not in used and not any(m[0]<=T and m[1]>=P for P,T in allw))
    lab = "none (v7 as frozen)" if X is None else "12-month min drift <= %.2f pp/2y" % X
    print("%-30s %2d/%-6d %-6d 1 per %-6.1f %.1f" % (lab, cov, tot, fas, yrs/max(fas,1), np.median(L)))
