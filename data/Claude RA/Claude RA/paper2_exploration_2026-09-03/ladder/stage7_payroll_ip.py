from harness import *
import warnings; warnings.filterwarnings("ignore")
A=ODD+"onset-detector-new-2026-08-23/27_realtime_vintages/alfred_all_vintages/"
def firstprint_changes(fn, horizons=(1,2,3), pct=True):
    df=pd.read_csv(A+fn, index_col=0, parse_dates=True); out={}
    for c in df.columns:
        s=df[c].dropna(); m=s.index[-1]; vd=pd.to_datetime(c[-8:])
        if m in out: continue
        rec={"release":vd}
        for h in horizons:
            if len(s)>h: rec[f"d{h}"]=(s.iloc[-1]/s.iloc[-1-h]-1)*100 if pct else s.iloc[-1]-s.iloc[-1-h]
        out[m]=rec
    return pd.DataFrame(out).T.sort_index()
pay=firstprint_changes("PAYEMS_all_vintages.csv"); ip=firstprint_changes("INDPRO_all_vintages.csv")
print("PAYEMS vintages from", pay.release.min().date(), "| INDPRO from", ip.release.min().date())
d10=load(ODD+"06_interest_rates_yield_curve/daily/DGS10.csv"); d1=load(ODD+"06_interest_rates_yield_curve/daily/DGS1.csv")
curve=(d10-d1.reindex(d10.index)).dropna(); gate=((curve<0).rolling(18*21).max()==1)
def gated(sig_months, rel):
    s=pd.Series(False, index=pd.to_datetime(rel.values))
    for m,on in sig_months.items():
        if on:
            dte=rel.loc[m]; g=gate[gate.index<=dte]
            if len(g) and g.iloc[-1]: s.loc[dte]=True
    return s.sort_index()
R=[]
for nm,tab in [("payrolls",pay),("industrial production",ip)]:
    for h in [1,2,3]:
        for x in ([-0.1,-0.2,-0.3,-0.5] if nm=="payrolls" else [-0.5,-1.0,-1.5,-2.0,-3.0]):
            cond=(tab[f"d{h}"].astype(float)<=x)
            R.append(score(pd.Series(cond.values, index=pd.to_datetime(tab.release.values)).sort_index(), f"{nm} first-print {h}-mo change <= {x}%", gap_days=45))
            R.append(score(gated(cond, tab.release), f"GATE18 & {nm} first-print {h}-mo change <= {x}%", gap_days=45))
df=pd.DataFrame(R); pd.set_option("display.width",330); pd.set_option("display.max_colwidth",120); pd.set_option("display.max_rows",200)
print(df[df.misses<=1].sort_values(["n_fa","max_lag"]).drop(columns=["calls"]).head(30).to_string())
for r in R:
    if r["n_fa"]<=1 and r["misses"]<=1: print(r["rule"], r["calls"])
df.to_csv("stage7_payroll_ip.csv", index=False)
