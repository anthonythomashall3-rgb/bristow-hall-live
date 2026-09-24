"""Stage 115: the international test, rebuilt.  Round 19 ported US THRESHOLDS abroad and
found detection transferred but quiet did not.  The a-priori rule ports no numbers at all --
each country sets every line from its OWN calm-period maximum times 1.05 -- so it is the
right instrument for the question 'does the method generalise, or only the American fit?'"""
import os
import pandas as pd, numpy as np
BASE=os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03")
exec(open(os.path.join(BASE,"ladder","stage51_intl_v2.py")).read().split("NBER = [(")[0])
NBER=[("1969-12","1970-11"),("1973-11","1975-03"),("1980-01","1980-07"),("1981-07","1982-11"),
      ("1990-07","1991-03"),("2001-03","2001-11"),("2007-12","2009-06"),("2020-02","2020-04"),("2024-04","2024-08")]
NBER=[(pd.Timestamp(a+"-01"),pd.Timestamp(b+"-01")) for a,b in NBER]
C=1.05
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
    eps=([(P,T) for P,T in NBER] if iso=="USA" else [(P,T) for P,T in technical(iso)[0]])
    eps=[(P,T) for P,T in eps if P>=idx[0] and T<=idx[-1]]
    q=pd.Series(True,index=idx)
    ug=S["u"]; q3=(ug<0.20).rolling(3).min().fillna(0).astype(bool)
    for P,T in eps:
        later=q3.index[(q3.index>T)&q3.values]; close=later[0] if len(later) else idx[-1]
        q &= ~((idx>=P-pd.DateOffset(months=6))&(idx<=close))
    return idx,S,gate,eps,q
print("%-4s %-15s %-7s %-7s %-9s %-6s %s" % ("iso","country","det","<=+-3m","med lag","FA","own thresholds (calm max x1.05)"))
tot=cov=fa=0; yrs=0.0; LAGS=[]
for iso in sorted(CC):
    r=country(iso)
    if r is None: continue
    idx,S,gate,eps,q=r
    if len(eps)<2: continue
    on=pd.Series(False,index=idx); th={}
    for k,s in S.items():
        m=q&(gate if k in("u","iu","r") else pd.Series(True,index=idx))
        x=s[m & s.notna()]
        if len(x)<60: continue
        t=float(x.max())*C; th[k]=round(t,3)
        f=(s>=t)
        if k in ("u","iu","r"): f=f&gate
        on |= f.fillna(False)
    if not th: continue
    runs=[]; prev=False
    for d0,v in on.items():
        if v and not prev: runs.append(d0)
        prev=v
    yrs+=(idx[-1]-idx[0]).days/365.25
    used=set()
    for P,T in eps:
        tot+=1
        hit=[x for x in runs if P-pd.DateOffset(months=6)<=x<=T]
        if hit:
            cov+=1; used.add(hit[0]); LAGS.append((hit[0].year-P.year)*12+(hit[0].month-P.month))
    fa+=sum(1 for x in runs if x not in used and not any(P-pd.DateOffset(months=6)<=x<=T+pd.DateOffset(months=3) for P,T in eps))
    myl=[(x.year-P.year)*12+(x.month-P.month) for P,T in eps for x in runs if P-pd.DateOffset(months=6)<=x<=T][:9]
    print("%-4s %-15s %2d/%-4d %-7d %-9s %-6d %s" % (iso,NAME[iso],
          sum(1 for P,T in eps if any(P-pd.DateOffset(months=6)<=x<=T for x in runs)),len(eps),
          sum(1 for l in myl if abs(l)<=3), ("%.1f"%np.median(myl)) if myl else "-",
          sum(1 for x in runs if x not in used and not any(P-pd.DateOffset(months=6)<=x<=T+pd.DateOffset(months=3) for P,T in eps)), th))
print("-"*118)
print("TOTAL detected %d/%d = %.0f%% | within +-3 months %d/%d | false episodes %d in %.0f country-years = %.1f%%/yr (1 per %.1f yr)"
      % (cov,tot,100*cov/max(tot,1),sum(1 for l in LAGS if abs(l)<=3),len(LAGS),fa,yrs,100*fa/yrs,yrs/max(fa,1)))
print("round 19 for comparison: US thresholds ported -> 89%% detection, 9.2%%/yr false (1 per 11 years)")
