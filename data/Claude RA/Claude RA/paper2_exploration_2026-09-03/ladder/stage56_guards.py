# Round 19e: two guards suggested by the foreign false alarms, tested on the panel.
#  G1 rate-channel labour confirmation: the rate channel may fire only if the
#     unemployment gap is at least +0.10 pp (the labour market is not improving).
#  G2 speed guard on the unemployment channels: the gap must be built inside
#     6 months, not 12 (kills slow structural drift).
import os, json, itertools
import pandas as pd, numpy as np
BASE = os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03")
src = open(os.path.join(BASE,"ladder","stage51_intl_v2.py")).read().split("NBER = [(")[0]
exec(src)
NBER = [("1948-11","1949-10"),("1953-07","1954-05"),("1957-08","1958-04"),
        ("1960-04","1961-02"),("1969-12","1970-11"),("1973-11","1975-03"),
        ("1980-01","1980-07"),("1981-07","1982-11"),("1990-07","1991-03"),
        ("2001-03","2001-11"),("2007-12","2009-06"),("2020-02","2020-04"),
        ("2024-04","2024-08")]
NBER = [(pd.Timestamp(a+"-01"), pd.Timestamp(b+"-01")) for a,b in NBER]
DROP = {"e_fast"}

def build2(iso, G1=False, G2=False, g1th=0.10):
    ur = first("LRHUTTTT%sM156S"%CC[iso],"LRUNTTTT%sM156S"%CC[iso],"LRHUTTTT%sM156N"%CC[iso])
    if ur is None: return None
    iu = first("LMUNRRTT%sM156S"%CC[iso],"LMUNRRTT%sM156N"%CC[iso])
    st = first("IR3TIB01%sM156N"%CC[iso],"IRSTCI01%sM156N"%CC[iso])
    lt = first("IRLTLT01%sM156N"%CC[iso]); ip = first("%sPROINDMISMEI"%iso)
    idx = pd.DatetimeIndex(pd.date_range(ur.index[0], ur.index[-1], freq="MS"))
    u = ur.reindex(idx).interpolate(limit_area="inside")
    W = 6 if G2 else 12
    ug  = u.rolling(3).mean() - u.rolling(W).min()
    ug12= u.rolling(3).mean() - u.rolling(12).min()
    gate = pd.Series(False, index=idx)
    if st is not None and lt is not None:
        sp = lt.reindex(idx, method="ffill") - st.reindex(idx, method="ffill")
        gate = (sp < 0).rolling(12, min_periods=1).max().fillna(0).astype(bool)
    lab = (ug12 >= g1th) if G1 else pd.Series(True, index=idx)
    f = {}
    f["u_fast"] = (ug >= TH["u_fast"]) & gate
    f["u_back"] = (ug >= TH["u_back"])
    if iu is not None:
        v = iu.reindex(idx).interpolate(limit_area="inside")
        g2 = v.rolling(3).mean() - v.rolling(W).min()
        f["iu_fast"] = (g2 >= TH["iu_fast"]) & gate
        f["iu_back"] = (g2 >= TH["iu_back"])
    if st is not None:
        s = st.reindex(idx, method="ffill"); d = s - s.shift(3)
        f["r_fast"] = (d <= -TH["r_fast"]) & gate & lab
        f["r_back"] = (d <= -TH["r_back"]) & lab
    if ip is not None:
        p = ip.reindex(idx, method="ffill"); d = (p/p.shift(1)-1)*100
        f["ip_back"] = (d <= TH["ip_back"]) & (d.shift(1) <= TH["ip_back"])
    f = {k: v.fillna(False).astype(bool) for k,v in f.items() if k not in DROP}
    return dict(idx=idx, f=f, ug=ug12)

def episodes_of(b):
    idx, ug = b["idx"], b["ug"]
    ev = sorted(((pd.Timestamp(d)+pd.DateOffset(months=LAG[k])).replace(day=1), k)
                for k,v in b["f"].items() for d in idx[v.values])
    q3 = (ug < 0.20).rolling(3).min().fillna(0).astype(bool)
    eps, until = [], None
    for cm,k in ev:
        if until is not None and cm <= until: continue
        later = q3.index[(q3.index > cm) & q3.values]
        until = later[0] if len(later) else idx[-1]
        eps.append((cm, until, k))
    return eps

def run(G1, G2):
    cov=tot=fas=0; yrs=0.0; lags=[]; usmiss=[]
    for iso in sorted(CC):
        b = build2(iso, G1, G2)
        if b is None: continue
        mach = episodes_of(b); lo,hi = b["idx"][0], b["idx"][-1]
        tech,_ = technical(iso); tech=[(P,T) for P,T in tech if P>=lo and T<=hi]
        oec = [(P,T) for P,T in oecd(iso) if P>=lo and T<=hi]
        ref = [(P,T) for P,T in NBER if P>=lo and T<=hi] if iso=="USA" else []
        allw = tech+oec+ref
        if len(tech) < 2: continue
        yrs += (hi-lo).days/365.25
        used=set()
        for P,T in tech:
            c=[m for m in mach if m[0]<=T and m[1]>=P]
            tot+=1
            if c:
                cov+=1; used.add(c[0]); lags.append((c[0][0].year-P.year)*12+(c[0][0].month-P.month))
            elif iso!="USA": usmiss.append((iso,str(P.date())[:7]))
        fas += sum(1 for m in mach if m not in used and
                   not any(m[0]<=T and m[1]>=P for P,T in allw))
    return cov, tot, fas, yrs, lags

print("%-28s %-8s %-8s %-22s %s" % ("variant","covered","FA","1 per N yrs","median lag"))
for G1,G2,lab in [(False,False,"v7 structure as frozen"),
                  (True,False,"+ G1 rate labour guard"),
                  (False,True,"+ G2 six-month speed guard"),
                  (True,True,"+ G1 and G2")]:
    c,t,f,y,L = run(G1,G2)
    print("%-28s %2d/%-5d %-8d %-22s %.1f" % (lab, c, t, f, "1 per %.1f"%(y/max(f,1)), np.median(L)))
