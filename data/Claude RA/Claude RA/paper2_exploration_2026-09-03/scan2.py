import pandas as pd, numpy as np, os
HOME=os.path.expanduser("~")
stats=pd.read_pickle("/tmp/explore/stats.pkl")
P=lambda s: pd.Period(s,"M")
nber=[("1960-04","1961-02"),("1969-12","1970-11"),("1973-11","1975-03"),("1980-01","1980-07"),("1981-07","1982-11"),("1990-07","1991-03"),("2001-03","2001-11"),("2007-12","2009-06"),("2020-02","2020-04")]
windows=[(P(a)-2,P(b)+12) for a,b in nber]+[(P("2024-03"),P("2025-09"))]
def in_win(m): return any(a<=m<=b for a,b in windows)
def runs(sig):
    idx=list(sig[sig].index); out=[]
    for m in idx:
        if out and (m.to_period("M")-out[-1][1].to_period("M")).n==1: out[-1][1]=m
        else: out.append([m,m])
    return out
def evaluate(sig):
    lags=[]
    for a,b in nber:
        w=sig[(sig.index.to_period("M")>=P(a)-2)&(sig.index.to_period("M")<=P(b)+12)]; hit=w[w].index
        lags.append((hit[0].to_period("M")-P(a)).n if len(hit) else None)
    fa=[(str(r[0].to_period("M")),str(r[1].to_period("M"))) for r in runs(sig) if not in_win(r[0].to_period("M"))]
    w=sig[(sig.index.to_period("M")>=P("2024-03"))&(sig.index.to_period("M")<=P("2025-09"))]; h=w[w].index
    return lags, fa, (str(h[0].to_period("M")) if len(h) else None)
res=[]
for name,ser in stats.items():
    if name=="rise3": continue
    for th in [0.2,0.25,0.3,0.35,0.4,0.45,0.5]:
        for k in [1,2,3]:
            sig=((ser>=th-1e-9).rolling(k).sum()==k)
            lags,fa,y24=evaluate(sig)
            if any(l is None for l in lags): continue
            res.append(dict(stat=name,th=th,k=k,lags=lags,med=np.median(lags),mean=round(np.mean(lags),2),mx=max(lags),n_fa=len(fa),fa=fa[:6],y2024=y24))
for th in [0.2,0.25,0.3,0.35,0.4,0.45]:
    for d in [0.1,0.15,0.2,0.25,0.3]:
        sig=(stats["S12"]>=th-1e-9)&(stats["dS3"]>=d-1e-9); lags,fa,y24=evaluate(sig)
        if all(l is not None for l in lags): res.append(dict(stat=f"S12&dS3>={d}",th=th,k=1,lags=lags,med=np.median(lags),mean=round(np.mean(lags),2),mx=max(lags),n_fa=len(fa),fa=fa[:6],y2024=y24))
    sig=(stats["S12"]>=th-1e-9)&(stats["rise3"]==1); lags,fa,y24=evaluate(sig)
    if all(l is not None for l in lags): res.append(dict(stat="S12&rise3",th=th,k=1,lags=lags,med=np.median(lags),mean=round(np.mean(lags),2),mx=max(lags),n_fa=len(fa),fa=fa[:6],y2024=y24))
R=pd.DataFrame(res); pd.set_option("display.width",260); pd.set_option("display.max_colwidth",70); pd.set_option("display.max_rows",300)
print("=== ZERO false-alarm runs (outside recession windows and 2024), sorted by mean lag ==="); print(R[R.n_fa==0].sort_values(["mean","mx"]).head(25).to_string())
print("\n=== baseline ==="); print(R[(R.stat=="S12")&(R.th==0.5)&(R.k==1)].to_string())
print("\n=== rules faster than Sahm on mean (<3.2) regardless of false alarms ==="); print(R[R["mean"]<3.2].sort_values(["n_fa","mean"]).head(25).to_string())
R.to_csv("/tmp/explore/onset_scan2.csv",index=False)
