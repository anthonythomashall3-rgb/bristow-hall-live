"""Stage 19b (publication lag corrected to 12 days, 3 Sep evening): the insured-unemployment-rate gap (a ratio: continued claims / covered employment) as an onset channel."""
exec(open("stage19_transforms.py").read().split("# ---------- (a) single-channel scoring")[0])
iur4=iur.rolling(4).mean(); iur8=iur.rolling(8).mean()
def gapch(ma, g, k=1):
    s=ma-ma.shift(1).rolling(52).min(); c=(s>=g-1e-12)
    for j in range(1,k): c=c&(s.shift(j)>=g-1e-12)
    return wk(c, 12)   # continued claims / IUR are published 12 days after the reference week (one week behind initial claims)
base=[SAHM[0.35], IC["ic8_30_k1"], PAY, UM["um_d1_10"], HOU]
rows=[]
for nm,ch in [("v1 (no IUR)",None)]+[(f"IUR{w} gap>={g} k{k}", gapch(m,g,k)) for w,m in [(4,iur4),(8,iur8)] for g in [0.20,0.25,0.30,0.35,0.40] for k in [1,2]]:
    eps=replay3(base+([ch] if ch is not None else []), GATE[12], 120); res,false=score_eps(eps,T_P1)
    rows.append(dict(rule=nm, n_false=len(false), false=false[:4], lags=[r["lag"] for r in res], end=[r["end_lag"] for r in res], tr=[r["tr_err"] for r in res], onsets=[r["onset"] for r in res]))
d=pd.DataFrame(rows); print(d.drop(columns=["onsets"]).to_string())
for _,r in d.iterrows():
    if r.n_false==0 and all(abs(x)<=2 for x in r.lags if x is not None): print(r.rule, r.onsets)
print("\n=== IUR gap replacing claims AND Sahm (two-channel labor rule: IUR gap + sentiment + housing) ===")
for g in [0.25,0.30,0.35]:
    for extra_nm, extra in [("+sent+hou",[UM["um_d1_10"],HOU]),("+sent+hou+pay",[UM["um_d1_10"],HOU,PAY]),("+Sahm+sent+hou",[SAHM[0.35],UM["um_d1_10"],HOU])]:
        eps=replay3([gapch(iur4,g)]+extra, GATE[12], 120); res,false=score_eps(eps,T_P1)
        print(f"IUR4 gap>={g} {extra_nm}: false {len(false)} {false[:3]} lags {[r['lag'] for r in res]} onsets {[r['onset'] for r in res]}")
print("\nIUR4 gap values around 1979-80 and 1973-74 (weekly, week-ending):")
s4=iur4-iur4.shift(1).rolling(52).min()
print({str(k.date()):round(v,3) for k,v in s4.loc["1979-10":"1980-02"].items()})
print({str(k.date()):round(v,3) for k,v in s4.loc["1973-10":"1974-02"].items()})
print("max IUR4 gap in quiet years:", {y: round(s4.loc[str(y)].max(),3) for y in [1976,1977,1978,1979,1984,1985,1986,1989,1995,1998,2003,2016,2019,2022,2023,2024,2025]})
