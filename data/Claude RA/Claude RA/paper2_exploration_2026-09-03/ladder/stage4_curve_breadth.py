from harness import *
import warnings; warnings.filterwarnings("ignore")
R=[]
d10=load(ODD+"06_interest_rates_yield_curve/daily/DGS10.csv"); d1=load(ODD+"06_interest_rates_yield_curve/daily/DGS1.csv"); tb3=load(ODD+"06_interest_rates_yield_curve/daily/DTB3.csv")
curves={"10y-1y":(d10-d1.reindex(d10.index)).dropna(), "10y-3m":(d10-tb3.reindex(d10.index)).dropna()}
# A. curve reversion variants
for nm,s in curves.items():
    inv=(s<0)
    for N in [20,60]:
        was=inv.rolling(N).sum()>=N*0.8          # mostly inverted over last N days
        cross=(s>0)&(s.shift(1)<=0)&was.shift(1).fillna(False)
        R.append(score(cross, f"{nm} crosses back above 0 after >={N}d inverted (event)", gap_days=45))
    for lb in [250,375]:
        for x in [0.5,1.0,1.5]:
            wasneg=inv.rolling(lb).max()==1
            R.append(score(wasneg&(s>=x), f"{nm} >= +{x} after inversion within prior {lb} trading days", gap_days=45))
    for x in [1.0,1.5]:
        R.append(score((s-s.rolling(90).min())>=x, f"{nm} steepens >= {x}pp within 90 trading days", gap_days=45))
# B. curve gate + fast labor rules (monthly S first prints; weekly IC)
rt=pd.read_csv(HOME+"/mnt/Recession Papers/Paper 2/data/realtime_first_print_sahm_by_vintage.csv", parse_dates=["vintage","latest_month"])
f=rt.sort_values("vintage").drop_duplicates("latest_month", keep="first").set_index("latest_month").sort_index(); S=f.S_latest; V=f.vintage
ic=load(ODD+"01_labor_unemployment/weekly/ICSA.csv"); icr=ic.rolling(4).mean()/ic.rolling(4).mean().shift(1).rolling(52).min()-1
s=curves["10y-1y"]; inv=(s<0)
for lbm in [12,18,24]:
    gate=inv.rolling(lbm*21).max()==1   # inverted at some point in prior lbm months
    def g(date): 
        w=gate[gate.index<=date]; return bool(w.iloc[-1]) if len(w) else False
    for th in [0.25,0.30,0.35,0.40,0.45,0.50]:
        sig=pd.Series(False,index=pd.to_datetime(V.values))
        for m in S.index[S>=th-1e-9]:
            d=V.loc[m]
            if g(d): sig.loc[d]=True
        R.append(score(sig[sig.index>="1963-01-01"].sort_index(), f"GATE curve inverted in prior {lbm}m AND Sahm>={th}", gap_days=45))
    for p in [0.10,0.15,0.20]:
        sig=(icr>=p)&gate.reindex(icr.index, method="ffill").fillna(False)
        R.append(score(sig[sig.index>="1968-01-01"], f"GATE curve inverted in prior {lbm}m AND IC4wk>={int(p*100)}%", gap_days=45))
show(R)
pd.DataFrame(R).to_csv("stage4_curve.csv", index=False)
