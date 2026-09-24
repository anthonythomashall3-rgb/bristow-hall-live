"""Stage 21f: published rules on current-vintage data (CFNAI-MA3 < -0.70; CFNAI diffusion < -0.35; ADS daily lines; Philadelphia
leading index USSLIND < 0) and 'improved' thresholds/persistence, scored for +-1 month, zero false alarms. Current vintage only:
CFNAI (2001->) and ADS are revised, so these are upper bounds on real-time performance, not real-time records."""
from harness import *
import warnings; warnings.filterwarnings("ignore")
d10=load(ODD+"06_interest_rates_yield_curve/daily/DGS10.csv"); d1=load(ODD+"06_interest_rates_yield_curve/daily/DGS1.csv")
curve=(d10-d1.reindex(d10.index)).dropna(); gate=((curve<0).rolling(12*21).max()==1)
M=ODD+"09_output_production/monthly/"
cf=load(M+"CFNAIMA3.csv"); cd=load(M+"CFNAIDIFF.csv"); ld=load(M+"USSLIND.csv")
ads=pd.read_csv(ODD+"bristow-hall/projects-old/raw/ADS_INDEX.csv"); ads["d"]=pd.to_datetime(ads.Date.str.replace(":","-")); ads=ads.set_index("d").ADS_Index
def mo(sig, lagdays): s=sig.copy(); s.index=s.index+pd.DateOffset(months=1)+pd.Timedelta(days=lagdays); return s   # CFNAI released ~3rd week of next month
def scoreit(sig,nm,gated):
    s=sig.dropna().astype(bool)
    if gated: s=s & gate.reindex(s.index, method="ffill").fillna(False)
    r=score(s, nm+(" [gate]" if gated else ""), start="1968-06-01"); L=r["lags"]; r["out1"]=sum(abs(l)>1 for l in L)+r["misses"]; return r
rows=[]
for th in [-0.5,-0.6,-0.7,-0.8,-1.0]:
    for k in [1,2]:
        c=(cf<=th); c=c&c.shift(k-1) if k>1 else c
        for g in [False,True]: rows.append(scoreit(mo(c,21), f"CFNAI-MA3<={th} x{k}", g))
for th in [-0.25,-0.35,-0.45]:
    c=(cd<=th)
    for g in [False,True]: rows.append(scoreit(mo(c,21), f"CFNAI diffusion<={th}", g))
for th in [0,-0.5,-1.0]:
    c=(ld<=th)
    for g in [False,True]: rows.append(scoreit(mo(c,10), f"Philly leading index<={th}", g))
a=ads.copy(); a.index=a.index+pd.Timedelta(days=7)
for th in [-0.5,-0.8,-1.0,-1.5]:
    for k in [1,21]:
        c=(a<=th).rolling(k).sum()==k
        for g in [False,True]: rows.append(scoreit(c, f"ADS<={th} for {k}d (+7d)", g))
df=pd.DataFrame(rows); pd.set_option("display.width",330); pd.set_option("display.max_colwidth",110); pd.set_option("display.max_rows",200)
print(df.sort_values(["n_fa","out1","misses"]).drop(columns=["calls"]).head(40).to_string())
