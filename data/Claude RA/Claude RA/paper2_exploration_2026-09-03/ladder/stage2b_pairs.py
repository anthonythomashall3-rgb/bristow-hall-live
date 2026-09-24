from harness import *
import itertools
ic=load(ODD+"01_labor_unemployment/weekly/ICSA.csv"); cc=load(ODD+"01_labor_unemployment/weekly/CCSA.csv"); iur=load(ODD+"01_labor_unemployment/weekly/IURSA.csv"); nfci=load(ODD+"05_financial_conditions/weekly/NFCI.csv")
def ratio(s,w,L): ma=s.rolling(w).mean(); return ma/ma.shift(1).rolling(L).min()-1
conds={}
for w in [4,8]:
    for p in [0.05,0.10,0.15,0.20,0.25]:
        conds[f"IC{w}wk>={int(p*100)}%/52"]=ratio(ic,w,52)>=p
        conds[f"CC{w}wk>={int(p*100)}%/52"]=ratio(cc,w,52)>=p
for th in [0.05,0.10,0.15,0.20]:
    ma=iur.rolling(13).mean(); conds[f"IUR13wk>+{th}"]=(ma-ma.shift(1).rolling(52).min())>th
for th in [-0.5,-0.25,0.0]:
    conds[f"NFCI>{th}"]=nfci>th
names=list(conds); R=[]
for a,b in itertools.combinations(names,2):
    if a[:2]==b[:2] and a[:2] in ("IC","CC"): continue
    idx=conds[a].index.union(conds[b].index)
    sig=(conds[a].reindex(idx).ffill().fillna(False) & conds[b].reindex(idx).ffill().fillna(False))
    sig=sig[sig.index>=max(conds[a].index.min(),conds[b].index.min())]
    R.append(score(sig, f"{a} AND {b}", gap_days=45))
df=pd.DataFrame(R)
pd.set_option("display.width",320); pd.set_option("display.max_colwidth",100); pd.set_option("display.max_rows",500)
ok=df[(df.misses==0)&(df.n_fa==0)]
print("=== pairs with zero misses and zero false alarms ==="); print(ok.sort_values("max_lag").drop(columns=["calls"]).head(30).to_string())
print("\n=== pairs with max_lag<=2 and n_fa<=2 ==="); print(df[(df.max_lag<=2)&(df.n_fa<=2)&(df.misses==0)].drop(columns=["calls"]).head(30).to_string())
print("\n=== best overall (min fa then max_lag) ==="); print(df[df.misses==0].sort_values(["n_fa","max_lag"]).drop(columns=["calls"]).head(20).to_string())
