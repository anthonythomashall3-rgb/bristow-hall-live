from harness import *
import itertools, warnings; warnings.filterwarnings("ignore")
rt=pd.read_csv(HOME+"/mnt/Recession Papers/Paper 2/data/realtime_first_print_sahm_by_vintage.csv", parse_dates=["vintage","latest_month"])
f=rt.sort_values("vintage").drop_duplicates("latest_month", keep="first").set_index("latest_month").sort_index()
S=f.S_latest; V=f.vintage
stats=pd.read_pickle("/tmp/explore/stats.pkl")
ic=load(ODD+"01_labor_unemployment/weekly/ICSA.csv"); cc=load(ODD+"01_labor_unemployment/weekly/CCSA.csv"); iur=load(ODD+"01_labor_unemployment/weekly/IURSA.csv"); nfci=load(ODD+"05_financial_conditions/weekly/NFCI.csv")
def ratio(s,w,L): ma=s.rolling(w).mean(); return ma/ma.shift(1).rolling(L).min()-1
wk={}
for w in [4,8]:
    for p in [0.0,0.05,0.10,0.15,0.20]:
        wk[f"IC{w}wk>={int(p*100)}%"]=ratio(ic,w,52)>=p; wk[f"CC{w}wk>={int(p*100)}%"]=ratio(cc,w,52)>=p
ma=iur.rolling(13).mean()
for th in [0.0,0.05,0.10]: wk[f"IUR13wk>+{th}"]=(ma-ma.shift(1).rolling(52).min())>th
for th in [-0.5,0.0]: wk[f"NFCI>{th}"]=nfci>th
def asof(cond, date):   # weekly condition as known on the CPS release date (week ending <= date-5 days)
    c=cond[cond.index<=date-pd.Timedelta(days=5)]; return bool(c.iloc[-1]) if len(c) else False
R=[]
mstats={"S12":S,"S6":stats["S6"],"du3":stats["du3"],"dS3":stats["dS3"]}
for mname,ms in mstats.items():
    for th in [0.20,0.25,0.30,0.35,0.40,0.45,0.50]:
        for wname,wc in wk.items():
            months=ms.index[ms>=th-1e-9]
            sig=pd.Series(False,index=V.values.astype("datetime64[ns]"))
            sig.index=pd.to_datetime(sig.index)
            for m in months:
                if m in V.index:
                    d=V.loc[m]
                    if asof(wc,d): sig.loc[d]=True
            sig=sig.sort_index()
            R.append(score(sig[sig.index>="1968-01-01"], f"{mname}>={th} AND {wname}", gap_days=45))
df=pd.DataFrame(R); pd.set_option("display.width",320); pd.set_option("display.max_colwidth",110); pd.set_option("display.max_rows",500)
print("=== zero misses, zero FA ==="); print(df[(df.misses==0)&(df.n_fa==0)].sort_values("max_lag").drop(columns=["calls"]).head(25).to_string())
print("\n=== max_lag<=2, sorted by n_fa ==="); print(df[(df.misses==0)&(df.max_lag<=2)].sort_values("n_fa").drop(columns=["calls"]).head(20).to_string())
print("\n=== max_lag<=3, n_fa<=1 ==="); print(df[(df.misses==0)&(df.max_lag<=3)&(df.n_fa<=1)].sort_values(["n_fa","max_lag"]).drop(columns=["calls"]).head(20).to_string())
df.to_csv("stage3_scan.csv",index=False)
