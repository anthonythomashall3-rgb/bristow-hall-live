from harness import *
R=[]
d10=load(ODD+"06_interest_rates_yield_curve/daily/DGS10.csv"); tb3=load(ODD+"06_interest_rates_yield_curve/daily/DTB3.csv"); d1=load(ODD+"06_interest_rates_yield_curve/daily/DGS1.csv")
sp=(d10-tb3.reindex(d10.index)).dropna(); sp1=(d10-d1.reindex(d10.index)).dropna()
for nm,s in [("10y-3m",sp),("10y-1y",sp1)]:
    for k in [1,10,20,60]:
        sig=(s<0).rolling(k).sum()==k; R.append(score(sig, f"yield curve {nm} inverted {k} trading days", gap_days=45))
    # steepening after inversion (classic 'recession begins when curve re-steepens'): spread rises >= X within 60 days after having been negative in prior 250 days
    for x in [0.5,1.0]:
        was_neg=(s<0).rolling(250).max()==1
        sig=was_neg & (s-s.rolling(60).min()>=x) & (s>0)
        R.append(score(sig, f"{nm}: re-steepen >= {x}pp within 60d after inversion in prior year"))
baa=load(ODD+"06_interest_rates_yield_curve/daily/BAA10Y.csv"); aaa=load(ODD+"06_interest_rates_yield_curve/daily/AAA10Y.csv")
for nm,s in [("BAA-10y",baa),("BAA-AAA",(baa-aaa.reindex(baa.index)).dropna())]:
    for x in [0.5,0.75,1.0,1.5]:
        sig=(s-s.rolling(250).min())>=x; R.append(score(sig, f"credit spread {nm} rises >= {x}pp above 250-day min"))
for f,nm in [("DJIA.csv","DJIA"),("NASDAQCOM.csv","NASDAQ")]:
    try:
        s=load(ODD+"20_market_equity/daily/"+f)
        for x in [0.15,0.20,0.30]:
            sig=(s/s.rolling(250).max()-1)<=-x; R.append(score(sig, f"{nm} drawdown >= {int(x*100)}% from 250-day high"))
    except Exception as e: print(nm, "skip", e)
dff=load(ODD+"06_interest_rates_yield_curve/daily/DFF.csv")
for x in [0.5,1.0]:
    sig=(dff.rolling(60).max()-dff)>=x; R.append(score(sig, f"fed funds falls >= {x}pp within 60 days"))
show(R)
