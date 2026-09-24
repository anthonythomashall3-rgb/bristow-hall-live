"""Stage 135: a genuine out-of-sample test.  Everything in the instrument was chosen on
1968-2026.  Four American recessions sit before that window -- 1948, 1953, 1957 and 1960 --
and nothing in the rule has ever seen them.  The monthly channels that exist that far back
are replayed there, each scaled by its own pre-1968 quiet distribution, with the number of
robust standard deviations carried over unchanged from the modern sample."""
import os, numpy as np, pandas as pd
ODD=os.path.expanduser("~/mnt/Onset Detector Data/")
def load(p):
    d=pd.read_csv(p,parse_dates=[0]); d=d.set_index(d.columns[0]).iloc[:,0]
    return pd.to_numeric(d,errors="coerce").dropna()
u=load(ODD+"01_labor_unemployment/monthly/UNRATE.csv")
pay=load(ODD+"03_payroll_employment/monthly/PAYEMS.csv")
ip=load(ODD+"09_output_production/monthly/INDPRO.csv")
hou=load(ODD+"11_housing_construction/monthly/HOUST.csv")
tb=load(ODD+"06_interest_rates_yield_curve/monthly/TB3MS.csv")
g1=load(ODD+"06_interest_rates_yield_curve/monthly/GS1.csv")
g10=load(ODD+"06_interest_rates_yield_curve/monthly/GS10.csv")
EP_OLD=[("1948-11","1949-10"),("1953-07","1954-05"),("1957-08","1958-04"),("1960-04","1961-02")]
EP_NEW=[("1969-12","1970-11"),("1973-11","1975-03"),("1980-01","1980-07"),("1981-07","1982-11"),
        ("1990-07","1991-03"),("2001-03","2001-11"),("2007-12","2009-06"),("2020-02","2020-04"),("2024-04","2024-08")]
def build(idx):
    S={}
    uu=u.reindex(idx).interpolate(limit_area="inside")
    S["Sahm"]=uu.rolling(3).mean()-uu.rolling(12).min()
    p=pay.reindex(idx,method="ffill"); S["payrolls"]=-(p/p.shift(1)-1)*100
    i=ip.reindex(idx,method="ffill"); d=-(i/i.shift(1)-1)*100
    S["industrial production"]=pd.concat([d,d.shift(1)],axis=1).min(axis=1)
    h=hou.reindex(idx,method="ffill"); S["housing starts"]=-(h/h.shift(6)-1)*100
    t=tb.reindex(idx,method="ffill"); S["bill"]=-(t-t.shift(3))
    sp=g10.reindex(idx,method="ffill")-g1.reindex(idx,method="ffill")
    gate=(sp<0).rolling(12,min_periods=1).max().fillna(0).astype(bool)
    return S,gate
def quiet(idx,eps):
    q=pd.Series(True,index=idx)
    for a,b in eps:
        q &= ~((idx>=pd.Timestamp(a+"-01")-pd.DateOffset(months=6))&(idx<=pd.Timestamp(b+"-01")+pd.DateOffset(months=9)))
    return q
def zs(x,m):
    v=x[m].dropna()
    if len(v)<24: return None
    med=float(np.median(v)); mad=float(np.median(np.abs(v-med)))*1.4826
    return None if (not np.isfinite(mad) or mad<=0) else (x-med)/mad
def replay(idx,S,gate,q,c,c2):
    Zg=[];Zn=[]
    for k,x in S.items():
        a=zs(x,q&gate); b=zs(x,q&~gate)
        if a is not None: Zg.append(a)
        if b is not None: Zn.append(b)
    mg=pd.concat(Zg,axis=1).max(axis=1) if Zg else pd.Series(-99.0,index=idx)
    mn=pd.concat(Zn,axis=1).max(axis=1) if Zn else pd.Series(-99.0,index=idx)
    return (((mg>=c)&gate)|((mn>=c2)&~gate)).reindex(idx).fillna(False)
def score(idx,trig,eps):
    hits=list(idx[trig.values]); det=[];lags=[]
    for a,b in eps:
        P=pd.Timestamp(a+"-01"); T=pd.Timestamp(b+"-01")
        w=[h for h in hits if P-pd.DateOffset(months=6)<=h<=T+pd.DateOffset(months=3)]
        det.append(bool(w)); lags.append((w[0].to_period("M")-P.to_period("M")).n if w else None)
    runs=[]
    for h in hits:
        if runs and (h-runs[-1][1]).days<=200: runs[-1][1]=h
        else: runs.append([h,h])
    fa=[str(a.date()) for a,b in runs if not any(pd.Timestamp(p+"-01")-pd.DateOffset(months=6)<=a<=pd.Timestamp(t+"-01")+pd.DateOffset(months=3) for p,t in eps)]
    return det,lags,fa
print("channel start dates: unemployment %s, payrolls %s, production %s, housing %s, bill %s, 1-year %s, 10-year %s"%(
    u.index[0].date(),pay.index[0].date(),ip.index[0].date(),hou.index[0].date(),tb.index[0].date(),g1.index[0].date(),g10.index[0].date()))
for lab,lo,hi,eps in [("modern sample 1968-2026","1968-06-01","2026-08-01",EP_NEW),
                      ("pre-sample 1953-1968 (nothing fitted here)","1953-04-01","1968-12-01",EP_OLD[1:]),
                      ("pre-sample 1948-1968, no curve gate","1948-01-01","1968-12-01",EP_OLD)]:
    idx=pd.DatetimeIndex(pd.date_range(lo,hi,freq="MS"))
    S,gate=build(idx)
    if "no curve gate" in lab: gate=pd.Series(False,index=idx)
    q=quiet(idx,eps)
    print("\n%s"%lab)
    print("%-6s %-6s %-9s %-8s %s"%("c","c2","detected","false","lags in months from the peak"))
    for c,c2 in [(3.5,8.0),(4.25,8.0),(5.0,8.0),(4.25,6.0),(6.0,10.0)]:
        tr=replay(idx,S,gate,q,c,c2); det,lags,fa=score(idx,tr,eps)
        print("%-6.2f %-6.2f %-9s %-8d %s"%(c,c2,"%d/%d"%(sum(det),len(eps)),len(fa),lags))
        if fa and len(fa)<=6: print("        false: %s"%fa)
