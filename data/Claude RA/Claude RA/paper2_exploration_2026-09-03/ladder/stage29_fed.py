"""Stage 29: the Fed-reaction channel found by the daily scan — short rates collapsing (6-month bill, prime rate) — scored as an
onset channel (alone, gated/ungated) and added to v3. Economically: the Fed's own recession call, unrevised, daily."""
exec(open("stage19b_iur.py").read().split("base=[SAHM[0.35]")[0])
DF=HOME+"/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03/data_fetched/"
def loadfred(f):
    s=pd.read_csv(f); s=s[s.value!="."]; s.index=pd.to_datetime(s.date); return s.value.astype(float).sort_index()
tb6=loadfred(DF+"fred_daily/DTB6.csv"); pr=loadfred(DF+"fred_daily/DPRIME.csv"); tb3=loadfred(DF+"fred_daily/DTB3.csv"); ff=loadfred(DF+"fred_daily/DFF.csv")
def dch(s, w, lagd=1): x=(s-s.shift(w)); x.index=x.index+pd.Timedelta(days=lagd); return x
def dd(s, w=250, lagd=1): x=(s-s.rolling(w).max()); x.index=x.index+pd.Timedelta(days=lagd); return x
CH={}
for nm,s in [("TB6",tb6),("TB3",tb3),("PRIME",pr),("FF",ff)]:
    for w,tag in [(20,"20d"),(60,"60d")]:
        for th in [0.5,0.75,1.0,1.5]: CH[f"{nm} fall>={th} in {tag}"]=D(dch(s,w)<=-th)
    for th in [1.0,1.5,2.0,3.0]: CH[f"{nm} drawdown>={th} from 250d max"]=D(dd(s)<=-th)
rows=[]
for nm,a in CH.items():
    for g,tag in [(GATE[12],"gate"),(np.ones(N,bool),"nogate")]:
        r=score(pd.Series(a&g, index=cal), f"{nm} [{tag}]", start="1968-06-01"); r["out1"]=sum(abs(x)>1 for x in r["lags"]); rows.append(r)
df=pd.DataFrame(rows); pd.set_option("display.width",330); pd.set_option("display.max_colwidth",110); pd.set_option("display.max_rows",100)
print(df.sort_values(["n_fa","misses","out1"]).drop(columns=["calls"]).head(24).to_string())
print("\n=== added to v3 ===")
V3=[SAHM[0.35], gapch(iur4,0.40), PAY, UM["um_d1_10"], persist2(h3,20)]
for nm in df[(df.n_fa==0)].sort_values(["misses","out1"]).rule.str.replace(r" \[.*\]","",regex=True).drop_duplicates().head(6):
    eps=replay3(V3+[CH[nm]], GATE[12], 120); res,false=score_eps(eps,T_P1); L=[r["lag"] for r in res]
    print(f"  +{nm}: false {len(false)} {false[:3]} lags {L} onsets {[r['onset'] for r in res]}")
