from harness import *
import warnings; warnings.filterwarnings("ignore")
d=pd.read_csv(ODD+"onset-detector-new-2026-08-23/26_ui_claims_admin/eta_ar539.csv", usecols=["st","c2","c3","c8","c19"], parse_dates=["c2"])
d=d[d.st.isin([s for s in d.st.unique() if s not in ("PR","VI")])]   # 50 states + DC
ic=d.pivot_table(index="c2", columns="st", values="c3", aggfunc="sum").sort_index()
cw=d.pivot_table(index="c2", columns="st", values="c8", aggfunc="sum").sort_index()
print("states:", ic.shape[1], "weeks:", ic.index.min().date(), ic.index.max().date())
R=[]
def breadth(panel, w, p, lookback="yoy"):
    s=panel.rolling(w).sum()
    if lookback=="yoy": g=s/s.shift(52)-1
    else: g=s/s.shift(1).rolling(52).min()-1
    return (g>=p).sum(axis=1)
for nm,panel in [("state initial claims",ic),("state continued claims",cw)]:
    for w in [4,8]:
        for lb in ["yoy","min52"]:
            for p in [0.10,0.20,0.30,0.50]:
                b=breadth(panel,w,p,lb)
                for K in [20,25,30,35,40]:
                    for k in [1,4]:
                        sig=(b>=K).rolling(k).sum()==k
                        R.append(score(sig[sig.index>="1987-06-01"], f"{nm} {w}wk {lb} >= {int(p*100)}% in >= {K} states, {k}wk", gap_days=45))
df=pd.DataFrame(R); pd.set_option("display.width",320); pd.set_option("display.max_colwidth",100); pd.set_option("display.max_rows",500)
print("=== zero misses (5 episodes: 1990, 2001, 2008, 2020, 2024) & zero FA ==="); print(df[(df.misses==0)&(df.n_fa==0)].sort_values("max_lag").drop(columns=["calls"]).head(30).to_string())
print("\n=== max_lag<=2, by FA ==="); print(df[(df.misses==0)&(df.max_lag<=2)].sort_values("n_fa").drop(columns=["calls"]).head(20).to_string())
print("\nfrontier:"); print(df[df.misses==0].groupby("max_lag").n_fa.min().to_string())
df.to_csv("stage5_breadth.csv", index=False)
