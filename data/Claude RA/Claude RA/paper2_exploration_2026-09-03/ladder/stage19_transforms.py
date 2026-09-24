"""Round 5, stage 19: ratio / percent / moving-level / normalized transforms as onset channels.
Question (Anthony, 3 Sep): 'try ratios and not pure levels, or moving levels, or percentages'. Every transform scored
(a) alone, gated by the 12-month curve gate, with the ladder harness (lags in months vs NBER peak; false-alarm runs), and
(b) inside the round-3 state machine, swapping the Sahm or claims channel. First prints where vintages exist (UNRATE, job losers)."""
exec(open("stage15_housing.py").read().split("base=[SAHM[0.35]")[0])
import sys
def persist2(s, x):
    c=(s<=-x/100); return D(c & c.shift(1).fillna(False))
HOU=persist2(h3,20)
# ---------- U-channel transforms from ALFRED UNRATE vintages (first print of each month, indexed by release date) ----------
U=pd.read_csv(A+"UNRATE_all_vintages.csv", index_col=0, parse_dates=True)
recs=[]
for c in U.columns:
    s=U[c].dropna(); m=s.index[-1]; rel=pd.to_datetime(c[-8:])
    if len(s)<16: continue
    u3=s.rolling(3).mean()
    cur=u3.iloc[-1]; prior=u3.iloc[-13:-1]              # prior 12 months of the 3-mo avg, same vintage
    ma12=u3.iloc[-13:-1].mean()
    recs.append(dict(month=m, rel=rel, u=s.iloc[-1], u3=cur, sahm_pp=cur-prior.min(), sahm_pct=cur/prior.min()-1,
                     u3_vs_ma12=cur/ma12-1, u1_pct=s.iloc[-1]/s.iloc[-13:-1].min()-1, u3_pp_ma12=cur-ma12,
                     sahm_pp_6=cur-u3.iloc[-7:-1].min(), sahm_pct_6=cur/u3.iloc[-7:-1].min()-1))
uv=pd.DataFrame(recs).drop_duplicates("month", keep="first").set_index("rel").sort_index()
def mrel(col, th): return D(uv[col]>=th-1e-9)
UCH={}
for th in [0.30,0.35,0.40,0.50]: UCH[f"sahm_pp>={th}"]=mrel("sahm_pp",th)
for th in [0.06,0.08,0.10,0.12,0.15]: UCH[f"sahm_pct>={th}"]=mrel("sahm_pct",th)
for th in [0.05,0.08,0.10,0.12]: UCH[f"u3_vs_ma12>={th}"]=mrel("u3_vs_ma12",th)
for th in [0.08,0.10,0.12,0.15,0.20]: UCH[f"u1_pct>={th}"]=mrel("u1_pct",th)
for th in [0.30,0.40,0.50]: UCH[f"u3_pp_ma12>={th}"]=mrel("u3_pp_ma12",th)
for th in [0.30,0.35,0.40]: UCH[f"sahm6_pp>={th}"]=mrel("sahm_pp_6",th)
for th in [0.08,0.10,0.12]: UCH[f"sahm6_pct>={th}"]=mrel("sahm_pct_6",th)
# ---------- job losers (first prints): LNS13023705 job losers level / CLF16OV ----------
try:
    JL=pd.read_csv(A+"LNS13023705_all_vintages.csv", index_col=0, parse_dates=True); LF=pd.read_csv(A+"CLF16OV_all_vintages.csv", index_col=0, parse_dates=True)
    recs=[]
    for c in JL.columns:
        s=JL[c].dropna(); m=s.index[-1]; rel=pd.to_datetime(c[-8:]); lc=[x for x in LF.columns if x[-8:]<=c[-8:]]
        if not lc or len(s)<16: continue
        lf=LF[lc[-1]].dropna().reindex(s.index).ffill()
        r=(s/lf*100).rolling(3).mean()
        recs.append(dict(month=m, rel=rel, jl_pp=r.iloc[-1]-r.iloc[-13:-1].min(), jl_pct=r.iloc[-1]/r.iloc[-13:-1].min()-1))
    jv=pd.DataFrame(recs).drop_duplicates("month", keep="first").set_index("rel").sort_index()
    print("job-losers first prints from", jv.index.min().date())
    for th in [0.20,0.25,0.30,0.40]: UCH[f"joblosers_pp>={th}"]=D(jv.jl_pp>=th-1e-9)
    for th in [0.10,0.15,0.20,0.25]: UCH[f"joblosers_pct>={th}"]=D(jv.jl_pct>=th-1e-9)
except Exception as e: print("job losers skipped:", e)
# ---------- claims transforms (weekly, current vintage 1967->; known +5 days) ----------
cc=load(ODD+"01_labor_unemployment/weekly/CCSA.csv"); icn=load(ODD+"01_labor_unemployment/weekly/ICNSA.csv"); ccn=load(ODD+"01_labor_unemployment/weekly/CCNSA.csv"); iur=load(ODD+"01_labor_unemployment/weekly/IURSA.csv")
ma26=ic.rolling(26).mean(); ma52=ic.rolling(52).mean(); ma13=ic.rolling(13).mean()
CCH={}
for p in [0.10,0.15,0.20,0.25]: CCH[f"ma4/ma26>={p}"]=wk(ma4/ma26-1>=p); CCH[f"ma8/ma52>={p}"]=wk(ma8/ma52-1>=p); CCH[f"ma4/ma13>={p}"]=wk(ma4/ma13-1>=p)
lg=np.log(ma4); z52=(lg-lg.shift(1).rolling(52).mean())/lg.shift(1).rolling(52).std()
for z in [2.0,2.5,3.0,3.5]: CCH[f"z52(log ma4)>={z}"]=wk(z52>=z); CCH[f"z52 2wk>={z}"]=wk((z52>=z)&(z52.shift(1)>=z))
# expanding percentile of r8 against its own history up to 52 weeks earlier (label-free, self-normalizing)
r8h=r8.dropna(); pr=pd.Series(index=r8h.index, dtype=float); vals=r8h.values
for i in range(len(vals)):
    hist=vals[:max(0,i-52)]
    pr.iloc[i]=(hist<vals[i]).mean() if len(hist)>260 else np.nan
for q in [0.95,0.975,0.99]: CCH[f"r8 expanding pct>={q}"]=wk(pr>=q)
# yoy log conjunct on NSA claims (v8 leg 1 form): min(log(ma4 IC_t/IC_t-52), log(ma4 CC_{t-1}/CC_{t-53}))
i4=icn.rolling(4).mean(); c4=ccn.rolling(4).mean().shift(1)
conj=pd.concat([np.log(i4/i4.shift(52)), np.log(c4/c4.shift(52))],axis=1).min(axis=1)
for t in [0.10,0.15,0.20,0.26]: CCH[f"nsa yoy conjunct>={t}"]=wk(conj>=t)
for t in [0.15,0.20,0.25,0.30]: CCH[f"nsa IC yoy>={t}"]=wk(np.log(i4/i4.shift(52))>=t)
# continued claims ratio vs 52wk min; IUR gap (SOS form)
cma4=cc.rolling(4).mean(); cr=cma4/cma4.shift(1).rolling(52).min()-1
for p in [0.10,0.15,0.20,0.25]: CCH[f"cc ma4 vs 52wk min>={p}"]=wk(cr>=p)
i26=iur.rolling(26).mean(); gap=i26-i26.shift(1).rolling(52).min()
for g in [0.10,0.15,0.20]: CCH[f"IUR 26wk gap>={g}"]=wk(gap>=g)
for g in [0.10,0.15,0.20,0.30]: CCH[f"IUR 4wk gap>={g}"]=wk(iur.rolling(4).mean()-iur.rolling(4).mean().shift(1).rolling(52).min()>=g)
# velocity of the ratio
for v in [0.10,0.15,0.20]: CCH[f"r4 velocity 4wk>={v}"]=wk(r4-r4.shift(4)>=v); CCH[f"r8 velocity 8wk>={v}"]=wk(r8-r8.shift(8)>=v)
# ---------- Beveridge u/v (current vintage JOLTS, 2001->) ----------
try:
    jor=load(ODD+"01_labor_unemployment/monthly/UNRATE.csv"); v=load(ODD+"02_labor_demand_vacancies/monthly/JTSJOR.csv") if os.path.exists(ODD+"02_labor_demand_vacancies/monthly/JTSJOR.csv") else None
    if v is None:
        import glob; cand=glob.glob(ODD+"**/JTSJOR.csv", recursive=True); v=load(cand[0]) if cand else None
    if v is not None:
        uu=jor.reindex(v.index); ratio=uu/v; rel=ratio.copy(); rel.index=rel.index+pd.DateOffset(months=2, days=5)  # JOLTS ~5 weeks after month end
        for t in [1.0,1.1,1.2]: CCH[f"u/v>={t} (JOLTS, current vintage)"]=D(rel>=t)
        m3=ratio.rolling(3).mean(); rr=m3/m3.shift(1).rolling(12).min()-1; rr.index=rr.index+pd.DateOffset(months=2, days=5)
        for t in [0.20,0.30,0.40]: CCH[f"u/v 3mo vs 12mo min>={t}"]=D(rr>=t)
        print("JOLTS u/v from", v.index.min().date())
except Exception as e: print("u/v skipped:", e)
# ---------- (a) single-channel scoring, gated ----------
def gated(arr): return pd.Series(arr&GATE[12], index=cal)
rows=[]
for nm,a in list(UCH.items())+list(CCH.items()):
    r=score(gated(a), nm, start="1968-06-01"); rows.append(r)
df=pd.DataFrame(rows); pd.set_option("display.width",330); pd.set_option("display.max_colwidth",120); pd.set_option("display.max_rows",300)
df["n_out2"]=df.lags.apply(lambda L: sum(abs(x)>2 for x in L)); df["mean_lag"]=df.lags.apply(lambda L: round(np.mean(L),2) if L else None)
print("\n=== SINGLE CHANNELS, gated (12-mo curve), 1968-2026; false alarm = run starting outside [peak-2, trough+12] ===")
print(df.sort_values(["n_fa","misses","n_out2","mean_lag"]).drop(columns=["calls","fa"]).to_string())
df.to_csv("stage19_single.csv", index=False)
# ---------- (b) inside the state machine: swap Sahm 0.35 -> U transform; swap claims 30% -> claims transform ----------
print("\n=== STATE MACHINE: replace Sahm>=0.35 by each U transform (other channels unchanged) ===")
rows=[]
for nm,a in UCH.items():
    eps=replay3([a, IC["ic8_30_k1"], PAY, UM["um_d1_10"], HOU], GATE[12], 120); res,false=score_eps(eps,T_P1)
    rows.append(dict(swap=nm, misses=sum(r["lag"] is None for r in res), n_false=len(false), false=false[:4], lags=[r["lag"] for r in res], onsets=[r["onset"] for r in res]))
d1=pd.DataFrame(rows); print(d1.drop(columns=["onsets"]).to_string()); d1.to_csv("stage19_swapU.csv", index=False)
print("\n=== STATE MACHINE: replace claims 8wk>=30% by each claims transform (other channels unchanged) ===")
rows=[]
for nm,a in CCH.items():
    eps=replay3([SAHM[0.35], a, PAY, UM["um_d1_10"], HOU], GATE[12], 120); res,false=score_eps(eps,T_P1)
    rows.append(dict(swap=nm, misses=sum(r["lag"] is None for r in res), n_false=len(false), false=false[:4], lags=[r["lag"] for r in res], onsets=[r["onset"] for r in res]))
d2=pd.DataFrame(rows); print(d2.drop(columns=["onsets"]).to_string()); d2.to_csv("stage19_swapC.csv", index=False)
print("\n=== STATE MACHINE: ADD each claims transform to the full v1 rule ===")
rows=[]
for nm,a in CCH.items():
    eps=replay3([SAHM[0.35], IC["ic8_30_k1"], a, PAY, UM["um_d1_10"], HOU], GATE[12], 120); res,false=score_eps(eps,T_P1)
    rows.append(dict(add=nm, misses=sum(r["lag"] is None for r in res), n_false=len(false), false=false[:4], lags=[r["lag"] for r in res], onsets=[r["onset"] for r in res]))
d3=pd.DataFrame(rows); print(d3.drop(columns=["onsets"]).to_string()); d3.to_csv("stage19_addC.csv", index=False)
