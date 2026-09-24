"""Simple initial-claims onset rules on the current-vintage weekly file (1967->), with a first-print check 2002-> from DOL releases."""
import pandas as pd, numpy as np, os
HOME=os.path.expanduser("~"); ODD=HOME+"/mnt/Onset Detector Data/"
ic=pd.read_csv(ODD+"01_labor_unemployment/weekly/ICSA.csv", parse_dates=[0]); ic=ic.set_index(ic.columns[0]).iloc[:,0].astype(float)
print("ICSA current vintage:", ic.index.min().date(), ic.index.max().date(), len(ic))
P=lambda s: pd.Period(s,"M")
nber=[("1969-12","1970-11"),("1973-11","1975-03"),("1980-01","1980-07"),("1981-07","1982-11"),("1990-07","1991-03"),("2001-03","2001-11"),("2007-12","2009-06"),("2020-02","2020-04")]
windows=[(P(a)-2,P(b)+12) for a,b in nber]+[(P("2023-01"),P("2025-09"))]
def in_win(m): return any(a<=m<=b for a,b in windows)
def runs(sig):
    idx=list(sig[sig].index); out=[]
    for m in idx:
        if out and (m-out[-1][1]).days<=14: out[-1][1]=m
        else: out.append([m,m])
    return out
def evaluate(sig):
    lags=[]; dates=[]
    for a,b in nber:
        w=sig[(sig.index.to_period("M")>=P(a)-2)&(sig.index.to_period("M")<=P(b)+12)]; hit=w[w].index
        lags.append((hit[0].to_period("M")-P(a)).n if len(hit) else None); dates.append(str(hit[0].date()) if len(hit) else None)
    fa=[(str(r[0].date()),str(r[1].date())) for r in runs(sig) if not in_win(r[0].to_period("M"))]
    return lags,dates,fa
res=[]
for w in [4,8,13]:
    ma=ic.rolling(w).mean()
    for L in [26,52]:
        ratio=ma/ma.shift(1).rolling(L).min()-1
        for p in [0.10,0.15,0.20,0.25,0.30,0.40]:
            for k in [1,2,4]:
                sig=((ratio>=p-1e-12).rolling(k).sum()==k)
                lags,dates,fa=evaluate(sig)
                if any(l is None for l in lags): continue
                res.append(dict(ma_weeks=w,lookback=L,pct=p,k=k,lags=lags,mean=round(np.mean(lags),2),mx=max(lags),n_fa=len(fa),fa=fa[:5]))
R=pd.DataFrame(res); pd.set_option("display.width",280); pd.set_option("display.max_colwidth",90)
print("=== zero false-alarm runs (outside recession windows and 2023-25), by mean lag ==="); print(R[R.n_fa==0].sort_values(["mean","mx"]).head(15).to_string())
print("\n=== fastest overall (<=2 false alarm runs) ==="); print(R[R.n_fa<=2].sort_values(["mean","mx"]).head(15).to_string())
R.to_csv("/tmp/explore/claims_scan.csv",index=False)
