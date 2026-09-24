from harness import *
R=[]
ic=load(ODD+"01_labor_unemployment/weekly/ICSA.csv"); cc=load(ODD+"01_labor_unemployment/weekly/CCSA.csv"); iur=load(ODD+"01_labor_unemployment/weekly/IURSA.csv"); nfci=load(ODD+"05_financial_conditions/weekly/NFCI.csv")
for nm,s in [("initial claims",ic),("continued claims",cc)]:
    for w in [4,8,13]:
        ma=s.rolling(w).mean()
        for L in [26,52]:
            r=ma/ma.shift(1).rolling(L).min()-1
            for p in [0.10,0.15,0.20,0.25,0.30]:
                for k in [1,3]:
                    sig=(r>=p).rolling(k).sum()==k; R.append(score(sig, f"{nm} {w}wk avg >= {int(p*100)}% above {L}wk min, {k}wk", gap_days=45))
for w in [13,26]:
    ma=iur.rolling(w).mean()
    for th in [0.10,0.15,0.20,0.30]:
        sig=(ma-ma.shift(1).rolling(52).min())>th; R.append(score(sig, f"SOS-type: IUR {w}wk mean > {th} above 52wk min", gap_days=45))
for th in [0.0,0.25,0.5,1.0]:
    R.append(score(nfci>th, f"NFCI > {th} (current vintage, revised series)", gap_days=45))
df=pd.DataFrame(R)
pd.set_option("display.width",320); pd.set_option("display.max_colwidth",100); pd.set_option("display.max_rows",500)
print("=== weekly rules: detect all covered episodes (no misses) and n_fa==0 ==="); print(df[(df.misses==0)&(df.n_fa==0)].drop(columns=["calls"]).to_string())
print("\n=== weekly rules with max_lag<=2 (regardless of misses/FA) ==="); print(df[df.max_lag<=2].drop(columns=["calls"]).to_string())
print("\n=== any rule detecting 2024? (last episode) ===")
for r in R:
    if r["calls"][-1] not in ("-","MISS") and r["calls"][-1] is not None: print(r["rule"], r["calls"][-1])
