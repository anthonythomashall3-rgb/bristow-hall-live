"""Round 3: full state machine replay with multiple channels; grid over channel settings. Scores onset/end lags per episode,
false episodes, and dated-peak errors. Two 2023-24 targets scored: Paper 1 (Apr-Aug 2024) and Anthony's (Jul 2023-Feb 2026)."""
from harness import *
import warnings, itertools, json; warnings.filterwarnings("ignore")
cal=pd.date_range("1962-01-01","2026-08-31",freq="D"); N=len(cal)
def D(s): return s.reindex(cal).ffill().fillna(False).astype(bool).values
# ---- channels (all as daily boolean arrays, known on/after publication) ----
d10=load(ODD+"06_interest_rates_yield_curve/daily/DGS10.csv"); d1=load(ODD+"06_interest_rates_yield_curve/daily/DGS1.csv")
curve=(d10-d1.reindex(d10.index)).dropna()
GATE={m: D((curve<0).rolling(m*21).max()==1) for m in [12,18,24]}
rt=pd.read_csv(HOME+"/mnt/Recession Papers/Paper 2/data/realtime_first_print_sahm_by_vintage.csv", parse_dates=["vintage","latest_month"])
f=rt.sort_values("vintage").drop_duplicates("latest_month", keep="first").set_index("latest_month").sort_index(); S=f.S_latest; V=f.vintage
Srel=pd.Series(S.values, index=pd.to_datetime(V.values))            # first-print S indexed by release date
SAHM={th: D(Srel>=th-1e-9) for th in [0.30,0.35,0.40,0.45,0.50]}
SAHM_BELOW50=D(Srel<0.5-1e-9)
ic=load(ODD+"01_labor_unemployment/weekly/ICSA.csv"); ma4=ic.rolling(4).mean(); ma8=ic.rolling(8).mean()
r4=ma4/ma4.shift(1).rolling(52).min()-1; r8=ma8/ma8.shift(1).rolling(52).min()-1
def wk(sig, lag=5): s=sig.copy(); s.index=s.index+pd.Timedelta(days=lag); return D(s)
IC={}
for p in [0.20,0.25,0.30,0.35]:
    IC[f"ic4_{int(p*100)}_k1"]=wk(r4>=p); IC[f"ic4_{int(p*100)}_k2"]=wk((r4>=p)&(r4.shift(1)>=p)); IC[f"ic8_{int(p*100)}_k1"]=wk(r8>=p)
vel=ma4/ma4.shift(8)-1
for p in [0.15,0.20,0.25]: IC[f"icvel8_{int(p*100)}"]=wk((vel>=p)&(vel.shift(1)>=p))
d=pd.read_csv(ODD+"onset-detector-new-2026-08-23/26_ui_claims_admin/eta_ar539.csv", usecols=["st","c2","c3","c8","c19"], parse_dates=["c2"]); d=d[~d.st.isin(["PR","VI"])]
cw=d.pivot_table(index="c2", columns="st", values="c8", aggfunc="sum").sort_index(); s8=cw.rolling(8).sum(); g8=s8/s8.shift(52)-1
icst=d.pivot_table(index="c2", columns="st", values="c3", aggfunc="sum").sort_index(); si8=icst.rolling(8).sum(); gi8=si8/si8.shift(52)-1
BR={}
for p in [0.10,0.15]:
    b=(g8>=p).sum(axis=1)
    for K in [20,25,30]:
        for k in [2,4]: BR[f"cc_{int(p*100)}_{K}_{k}"]=wk((b>=K).rolling(k).sum()==k, 9)
    bi=(gi8>=p).sum(axis=1)
    for K in [25,30,35]: BR[f"ic_{int(p*100)}_{K}_4"]=wk((bi>=K).rolling(4).sum()==4, 9)
A=ODD+"onset-detector-new-2026-08-23/27_realtime_vintages/alfred_all_vintages/"
dfp=pd.read_csv(A+"PAYEMS_all_vintages.csv", index_col=0, parse_dates=True); out={}
for c in dfp.columns:
    s=dfp[c].dropna(); m=s.index[-1]
    if m in out or len(s)<4: continue
    out[m]=dict(rel=pd.to_datetime(c[-8:]), d1=(s.iloc[-1]/s.iloc[-2]-1)*100)
pay=pd.DataFrame(out).T.sort_index(); PAY=D(pd.Series((pay.d1.astype(float)<=-0.1).values, index=pd.to_datetime(pay.rel.values)))
# end channel: claims 8wk avg peak / 3% confirm (weekly, known +5d)
ma8v=ma8.copy(); ma8v.index=ma8v.index+pd.Timedelta(days=5); ma8d=ma8v.reindex(cal).ffill().values
# ---- targets ----
NBER=[("1969-12","1970-11"),("1973-11","1975-03"),("1980-01","1980-07"),("1981-07","1982-11"),("1990-07","1991-03"),("2001-03","2001-11"),("2007-12","2009-06"),("2020-02","2020-04")]
T_P1=NBER+[("2024-04","2024-08")]; T_AH=NBER+[("2023-07","2026-02")]
def replay(onset, close_extra=None):
    """State machine over daily calendar. onset: bool array. Episode opens at first True while closed; end called by claims peak/3%;
    episode closes when end has been called AND Sahm first print < 0.50 (and onset signal off). Returns list of episodes."""
    eps=[]; open_=False; i=0
    while i<N:
        if not open_:
            if onset[i]:
                open_=True; start=i; runmax=-1; pk=None; endcall=None; i+=1; continue
            i+=1; continue
        v=ma8d[i]
        if not np.isnan(v):
            if v>runmax: runmax=v; pk=i
            elif endcall is None and v<=runmax*0.97: endcall=i
        if endcall is not None and SAHM_BELOW50[i] and not onset[i] and (i-endcall)>=0:
            eps.append(dict(onset=cal[start], trough_week=cal[pk], end_call=cal[endcall], close=cal[i])); open_=False
        i+=1
    if open_: eps.append(dict(onset=cal[start], trough_week=cal[pk] if pk else None, end_call=cal[endcall] if endcall else None, close=None))
    return eps
def score_eps(eps, targets):
    res=[]; used=set()
    for pk,tr in targets:
        pkm=P(pk); trm=P(tr)
        m=[e for e in eps if (pkm-2).to_timestamp()<=e["onset"]<=(trm+6).to_timestamp(how="end")]
        if not m: res.append(dict(peak=pk, onset=None, lag=None, end_lag=None, tr_err=None)); continue
        e=m[0]; used.add(e["onset"])
        lag=(e["onset"].to_period("M")-pkm).n
        el=(e["end_call"].to_period("M")-trm).n if e["end_call"] is not None else None
        te=(e["trough_week"].to_period("M")-trm).n if e["trough_week"] is not None else None
        res.append(dict(peak=pk, onset=str(e["onset"].date()), lag=lag, end_lag=el, tr_err=te))
    false=[str(e["onset"].date()) for e in eps if e["onset"] not in used and e["onset"]>=pd.Timestamp("1968-06-01")]
    return res, false
configs=[]
for gm in [12,18,24]:
    for th in [0.35,0.40,0.45]:
        for icn in ["ic4_30_k1","ic4_30_k2","ic8_30_k1","ic4_25_k2","ic4_35_k1","icvel8_20","icvel8_25",None]:
            for brn in ["cc_10_25_4","cc_10_20_4","cc_10_30_4","cc_15_25_4","cc_10_25_2","ic_10_30_4",None]:
                for payon in [False,True]:
                    configs.append((gm,th,icn,brn,payon))
rows=[]
for gm,th,icn,brn,payon in configs:
    sig=SAHM[th].copy()
    if icn: sig=sig|IC[icn]
    if brn: sig=sig|BR[brn]
    if payon: sig=sig|PAY
    sig=sig&GATE[gm]
    sig[cal<pd.Timestamp("1968-06-01")]=False
    eps=replay(sig)
    for tname,T in [("P1",T_P1),("AH",T_AH)]:
        res,false=score_eps(eps,T)
        lags=[r["lag"] for r in res]; miss=sum(l is None for l in lags); L=[l for l in lags if l is not None]
        rows.append(dict(gate=gm, sahm=th, ic=icn, br=brn, pay=payon, target=tname, misses=miss, n_false=len(false), false=false[:5],
                         lags=L, max_abs=max(abs(x) for x in L) if L else None, n_out2=sum(abs(x)>2 for x in L), mean_abs=round(np.mean([abs(x) for x in L]),2) if L else None,
                         end_lags=[r["end_lag"] for r in res], tr_errs=[r["tr_err"] for r in res], onsets=[r["onset"] for r in res]))
df=pd.DataFrame(rows); df.to_csv("stage9_grid.csv", index=False)
pd.set_option("display.width",340); pd.set_option("display.max_colwidth",120); pd.set_option("display.max_rows",80)
for t in ["P1","AH"]:
    d0=df[(df.target==t)&(df.misses==0)]
    print(f"\n=== target {t}: zero false episodes, sorted by n_out2 then mean_abs ===")
    print(d0[d0.n_false==0].sort_values(["n_out2","mean_abs"]).drop(columns=["end_lags","tr_errs","onsets","false"]).head(12).to_string())
    print(f"\n=== target {t}: frontier n_false -> best n_out2 ===")
    print(d0.groupby("n_false").n_out2.min().head(6).to_string())
best=df[(df.target=="P1")&(df.misses==0)&(df.n_false==0)].sort_values(["n_out2","mean_abs"]).head(3)
for _,r in best.iterrows(): print("\nBEST P1:", dict(r[["gate","sahm","ic","br","pay"]]), "onsets", r.onsets, "lags", r.lags, "end_lags", r.end_lags, "tr_errs", r.tr_errs)
best=df[(df.target=="AH")&(df.misses==0)&(df.n_false==0)].sort_values(["n_out2","mean_abs"]).head(3)
for _,r in best.iterrows(): print("\nBEST AH:", dict(r[["gate","sahm","ic","br","pay"]]), "onsets", r.onsets, "lags", r.lags, "end_lags", r.end_lags, "tr_errs", r.tr_errs)
