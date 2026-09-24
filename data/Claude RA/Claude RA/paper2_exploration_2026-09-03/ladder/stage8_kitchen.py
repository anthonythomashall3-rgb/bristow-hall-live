exec(open("stage6_union.py").read().split("R=[]")[0])
A=ODD+"onset-detector-new-2026-08-23/27_realtime_vintages/alfred_all_vintages/"
df=pd.read_csv(A+"PAYEMS_all_vintages.csv", index_col=0, parse_dates=True); out={}
for c in df.columns:
    s=df[c].dropna(); m=s.index[-1]
    if m in out or len(s)<4: continue
    out[m]=dict(rel=pd.to_datetime(c[-8:]), d1=(s.iloc[-1]/s.iloc[-2]-1)*100, d2=(s.iloc[-1]/s.iloc[-3]-1)*100)
pay=pd.DataFrame(out).T.sort_index()
def pay_daily(cond):
    s=pd.Series(cond.values.astype(bool), index=pd.to_datetime(pay.rel.values)); return s.reindex(cal).ffill().fillna(False).astype(bool)
PAY1=pay_daily(pay.d1.astype(float)<=-0.1); PAY2=pay_daily(pay.d2.astype(float)<=-0.2)
R=[]
combos={
 "A: gate & (Sahm>=0.4 | IC>=30% | breadth)": G&(sahm_daily(0.4)|IC[0.30]|BR),
 "B: A | payroll 1-mo<=-0.1%": G&(sahm_daily(0.4)|IC[0.30]|BR|PAY1),
 "C: A | payroll 2-mo<=-0.2%": G&(sahm_daily(0.4)|IC[0.30]|BR|PAY2),
 "D: gate & (Sahm>=0.5 | IC>=30% | breadth | payroll 2-mo<=-0.2%)": G&(sahm_daily(0.5)|IC[0.30]|BR|PAY2),
 "E: gate & (Sahm>=0.45 | IC>=30% | breadth | payroll 1-mo<=-0.1%)": G&(sahm_daily(0.45)|IC[0.30]|BR|PAY1),
 "F: gate & (Sahm>=0.45 | IC>=30% | payroll 1-mo<=-0.1%)  [no breadth; 1962->]": G&(sahm_daily(0.45)|IC[0.30]|PAY1),
 "G: gate & (Sahm>=0.4 | IC>=30% | payroll 1-mo<=-0.1%)  [no breadth; 1962->]": G&(sahm_daily(0.4)|IC[0.30]|PAY1),
}
for nm,sig in combos.items():
    R.append(evalsig(sig, nm, "1968-06-01" if "1962" in nm else "1968-06-01"))
df2=pd.DataFrame(R); pd.set_option("display.width",340); pd.set_option("display.max_colwidth",160)
print(df2.drop(columns=["calls"]).to_string())
for r in R: print(r["rule"], r["calls"])
