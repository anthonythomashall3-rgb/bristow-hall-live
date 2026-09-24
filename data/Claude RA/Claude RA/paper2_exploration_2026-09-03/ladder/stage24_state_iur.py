"""Stage 24: state-level insured-unemployment-rate breadth from ETA 539 (weekly, 51 jurisdictions, 1986->). Per state:
IUR = continued weeks claimed (c8) / covered employment (c19); 4-week average minus its 52-week minimum; breadth = number of
states at or above a gap. Scored alone (gated) and added to v3. Also: Sahm quiet-period maximum under Anthony's 2023-26 chronology."""
exec(open("stage19b_iur.py").read().split("base=[SAHM[0.35]")[0])
d=pd.read_csv(ODD+"onset-detector-new-2026-08-23/26_ui_claims_admin/eta_ar539.csv", usecols=["st","c2","c19"], parse_dates=["c2"]); d=d[~d.st.isin(["PR","VI"])]
iur_st=d.pivot_table(index="c2", columns="st", values="c19", aggfunc="max").sort_index()   # c19 = state insured unemployment rate (NSA), as reported
# NSA per state -> use year-over-year gap instead of 52wk min? do both: (a) 4wk avg minus 52wk min (seasonal risk), (b) 4wk avg minus same 4 weeks a year earlier
m4=iur_st.rolling(4).mean(); gapA=m4-m4.shift(1).rolling(52).min(); gapB=m4-m4.shift(52)
print("states:", iur_st.shape[1], "weeks:", iur_st.shape[0], iur_st.index.min().date(), iur_st.index.max().date())
def breadth(gap, g): return (gap>=g-1e-12).sum(axis=1)
BR={}
for lab,gap in [("min52",gapA),("yoy",gapB)]:
    for g in [0.3,0.4,0.5,0.75,1.0]:
        b=breadth(gap,g)
        for K in [10,15,20,25,30]:
            for k in [1,2,4]:
                BR[f"{lab} gap>={g} states>={K} x{k}wk"]=wk((b>=K).rolling(k).sum()==k, 9)
rows=[]
for nm,a in BR.items():
    r=score(pd.Series(a&GATE[12], index=cal), nm, start="1987-06-01"); rows.append(r)
df=pd.DataFrame(rows); df["out1"]=df.lags.apply(lambda L: sum(abs(x)>1 for x in L))
pd.set_option("display.width",330); pd.set_option("display.max_colwidth",100); pd.set_option("display.max_rows",100)
print("\n=== state IUR breadth alone, gated, 1987-2026 (episodes covered: 1990, 2001, 2008, 2020, 2024) ===")
print(df.sort_values(["n_fa","misses","out1"]).drop(columns=["calls","fa"]).head(25).to_string())
print("\n=== v3 + best clean breadth channels ===")
V3=[SAHM[0.35], gapch(iur4,0.40), PAY, UM["um_d1_10"], persist2(h3,20)]
for nm in df[(df.n_fa==0)&(df.misses<=1)].sort_values(["misses","out1"]).rule.head(8):
    eps=replay3(V3+[BR[nm]], GATE[12], 120); res,false=score_eps(eps,T_P1); L=[r["lag"] for r in res]
    print(f"  +{nm}: false {len(false)} {false[:3]} lags {L} onsets {[r['onset'] for r in res][4:]}")
# breadth readings around 2023-24 and 2001 for the record
b=breadth(gapA,0.5); print("\nstates with 4wk IUR gap>=0.5 (min52), monthly max 2023-2024:", {str(k):int(v) for k,v in b.loc["2023-01":"2024-12"].resample("M").max().items()})
b2=breadth(gapB,0.5); print("states with IUR 4wk up>=0.5 yoy, monthly max 2023-2024:", {str(k):int(v) for k,v in b2.loc["2023-01":"2024-12"].resample("M").max().items()})
# Sahm quiet max under Anthony's chronology (Jul 2023 - Feb 2026)
allowedAH=np.zeros(N,bool)
for pk,tr in T_AH:
    lo=cal.searchsorted((P(pk)-2).to_timestamp()); hi=cal.searchsorted((P(tr)+12).to_timestamp(how="end")); allowedAH[lo:hi+1]=True
quietAH=(~allowedAH)&GATE[12]&(cal>=pd.Timestamp("1968-06-01")); Sd=Srel.reindex(cal).ffill().values
print("\nSahm first print: max gated quiet reading under Anthony's chronology =", np.nanmax(Sd[quietAH]).round(3), "on", str(cal[quietAH][np.nanargmax(Sd[quietAH])].date()))
