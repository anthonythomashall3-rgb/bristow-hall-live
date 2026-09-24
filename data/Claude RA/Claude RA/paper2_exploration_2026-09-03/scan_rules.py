"""Exploratory scan: simpler onset/end rules on FIRST-PRINT unemployment data (ALFRED vintages, 1960->2026)."""
import pandas as pd, numpy as np, itertools, os
HOME=os.path.expanduser("~")
rt=pd.read_csv(HOME+"/mnt/Recession Papers/Paper 2/data/realtime_first_print_sahm_by_vintage.csv", parse_dates=["vintage","latest_month"])
first=rt.sort_values("vintage").drop_duplicates("latest_month", keep="first").set_index("latest_month").sort_index()
S=first.S_latest; V=first.vintage; U=first.u_latest
# first-print series of other statistics need the vintage; rebuild from the vintage file
df=pd.read_csv(HOME+"/mnt/Onset Detector Data/onset-detector-new-2026-08-23/27_realtime_vintages/alfred_all_vintages/UNRATE_all_vintages.csv", index_col=0, parse_dates=True)
cols=df.columns; vd=pd.to_datetime([c[-8:] for c in cols])
def fp_stat(fn):
    out={}
    for c,d in zip(cols,vd):
        u=df[c].dropna(); m=u.index[-1]
        if m in out: continue
        out[m]=fn(u)
    return pd.Series(out).sort_index()
def sahmL(u,L,k=3):
    m=u.rolling(k).mean(); return (m-m.shift(1).rolling(L).min()).iloc[-1]
stats={"S12":S}
for L in [6,9,12,24]:
    stats[f"S{L}"]=fp_stat(lambda u,L=L: sahmL(u,L))
stats["dS3"]=fp_stat(lambda u: (lambda m:(m-m.shift(1).rolling(12).min()))(u.rolling(3).mean()).diff(3).iloc[-1])
stats["du3"]=fp_stat(lambda u: u.rolling(3).mean().diff(3).iloc[-1])   # 3-mo change in 3-mo avg rate
stats["rise3"]=fp_stat(lambda u: int((u.rolling(3).mean().diff()>0).iloc[-3:].all()))
P=lambda s: pd.Period(s,"M")
nber=[("1960-04","1961-02"),("1969-12","1970-11"),("1973-11","1975-03"),("1980-01","1980-07"),("1981-07","1982-11"),("1990-07","1991-03"),("2001-03","2001-11"),("2007-12","2009-06"),("2020-02","2020-04")]
windows=[(P(a)-2,P(b)+12) for a,b in nber]+[(P("2024-03"),P("2025-09"))]   # 2024 = Paper 1's episode
def in_win(m): return any(a<=m<=b for a,b in windows)
def evaluate(sig):
    """sig: boolean Series indexed by month (first-print). Returns lags per recession (first True inside window), false-alarm months, episodes."""
    lags=[]; 
    for a,b in nber:
        w=sig[(sig.index.to_period("M")>=P(a)-2)&(sig.index.to_period("M")<=P(b)+12)]
        hit=w[w].index
        lags.append((hit[0].to_period("M")-P(a)).n if len(hit) else None)
    fa=[m for m in sig[sig].index if not in_win(m.to_period("M"))]
    # 2024
    w=sig[(sig.index.to_period("M")>=P("2024-03"))&(sig.index.to_period("M")<=P("2025-09"))]; h=w[w].index
    return lags, fa, (str(h[0].to_period("M")) if len(h) else None)
res=[]
for name,ser in stats.items():
    if name in ("rise3",): continue
    for th in [0.2,0.25,0.3,0.35,0.4,0.45,0.5,0.6]:
        for k in [1,2,3]:
            base=(ser>=th-1e-9)
            sig=base.rolling(k).sum()==k
            lags,fa,y24=evaluate(sig)
            if any(l is None for l in lags): continue
            res.append(dict(stat=name,th=th,k=k,lags=lags,med=np.median(lags),mx=max(lags),n_fa=len(fa),fa=[str(m.to_period("M")) for m in fa][:8],y2024=y24))
# combination rules: S12>=th AND rise3
for th in [0.2,0.25,0.3,0.35,0.4]:
    sig=(stats["S12"]>=th-1e-9)&(stats["rise3"]==1)
    lags,fa,y24=evaluate(sig)
    if all(l is not None for l in lags): res.append(dict(stat="S12&rise3",th=th,k=1,lags=lags,med=np.median(lags),mx=max(lags),n_fa=len(fa),fa=[str(m.to_period("M")) for m in fa][:8],y2024=y24))
# S12>=th AND dS3>=d
for th in [0.2,0.25,0.3,0.35,0.4]:
    for d in [0.1,0.15,0.2,0.25,0.3]:
        sig=(stats["S12"]>=th-1e-9)&(stats["dS3"]>=d-1e-9)
        lags,fa,y24=evaluate(sig)
        if all(l is not None for l in lags): res.append(dict(stat=f"S12&dS3>={d}",th=th,k=1,lags=lags,med=np.median(lags),mx=max(lags),n_fa=len(fa),fa=[str(m.to_period("M")) for m in fa][:8],y2024=y24))
R=pd.DataFrame(res)
pd.set_option("display.width",250); pd.set_option("display.max_colwidth",60); pd.set_option("display.max_rows",200)
print("=== rules with ZERO false alarms outside recession windows (+2024), ranked by median lag then max ===")
Z=R[R.n_fa==0].sort_values(["med","mx"]); print(Z.head(40).to_string())
print("\n=== baseline Sahm 0.50 k=1 ===")
print(R[(R.stat=="S12")&(R.th==0.5)&(R.k==1)].to_string())
print("\n=== best rules allowing <=2 false-alarm months ===")
print(R[R.n_fa<=2].sort_values(["med","mx"]).head(15).to_string())
pd.to_pickle(stats,"/tmp/explore/stats.pkl"); R.to_csv("/tmp/explore/onset_scan.csv",index=False)
