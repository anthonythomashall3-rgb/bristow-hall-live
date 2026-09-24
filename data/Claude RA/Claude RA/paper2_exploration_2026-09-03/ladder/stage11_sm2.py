"""State machine v2: onset on a channel EDGE (off->on) while closed; end = claims 8wk peak, 3% confirm, revisable while open;
close when end called and Sahm first print < 0.50. Grid over channels; both 2023-24 targets."""
exec(open("stage9_statemachine.py").read().split("# ---- targets ----")[0])
for p in [0.15,0.20]:
    IC[f"ic4_{int(p*100)}_k2"]=wk((r4>=p)&(r4.shift(1)>=p)); IC[f"ic4_{int(p*100)}_k3"]=wk((r4>=p)&(r4.shift(1)>=p)&(r4.shift(2)>=p))
NBER=[("1969-12","1970-11"),("1973-11","1975-03"),("1980-01","1980-07"),("1981-07","1982-11"),("1990-07","1991-03"),("2001-03","2001-11"),("2007-12","2009-06"),("2020-02","2020-04")]
T_P1=NBER+[("2024-04","2024-08")]; T_AH=NBER+[("2023-07","2026-02")]
def edges(chs):
    e=np.zeros(N,bool)
    for c in chs: e|= c & ~np.roll(c,1)
    return e
def replay2(chs, gate):
    on=np.zeros(N,bool)
    for c in chs: on|=c
    edge=edges(chs)&gate
    eps=[]; open_=False; i=0
    while i<N:
        if not open_:
            if edge[i] and cal[i]>=pd.Timestamp("1968-06-01"):
                open_=True; start=i; runmax=-1; pk=None; endcall=None
            i+=1; continue
        v=ma8d[i]
        if not np.isnan(v):
            if v>runmax: runmax=v; pk=i; endcall=None
            elif endcall is None and v<=runmax*0.97: endcall=i
        if endcall is not None and SAHM_BELOW50[i]:
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
        res.append(dict(peak=pk, onset=str(e["onset"].date()), lag=(e["onset"].to_period("M")-pkm).n,
                        end_lag=(e["end_call"].to_period("M")-trm).n if e["end_call"] is not None else None,
                        tr_err=(e["trough_week"].to_period("M")-trm).n if e["trough_week"] is not None else None))
    false=[str(e["onset"].date()) for e in eps if e["onset"] not in used]
    return res,false
rows=[]
for gm in [12,18]:
    for th in [0.35,0.40,0.45,0.50]:
        for icn in ["ic8_30_k1","ic4_35_k1","ic4_30_k2","ic4_25_k2","ic4_20_k2","ic4_20_k3","ic4_15_k3",None]:
            for brn in ["cc_10_25_4","cc_10_20_4","cc_10_25_2",None]:
                for payon in [False,True]:
                    chs=[SAHM[th]]
                    if icn: chs.append(IC[icn])
                    if brn: chs.append(BR[brn])
                    if payon: chs.append(PAY)
                    eps=replay2(chs, GATE[gm])
                    for tname,T in [("P1",T_P1),("AH",T_AH)]:
                        res,false=score_eps(eps,T); L=[r["lag"] for r in res]; miss=sum(l is None for l in L); L2=[l for l in L if l is not None]
                        rows.append(dict(gate=gm,sahm=th,ic=icn,br=brn,pay=payon,target=tname,misses=miss,n_false=len(false),false=false[:4],lags=L2,
                                         n_out2=sum(abs(x)>2 for x in L2), max_abs=max(abs(x) for x in L2) if L2 else None, mean_abs=round(np.mean([abs(x) for x in L2]),2) if L2 else None,
                                         end_lags=[r["end_lag"] for r in res], tr_errs=[r["tr_err"] for r in res], onsets=[r["onset"] for r in res]))
df=pd.DataFrame(rows); df.to_csv("stage11_grid.csv", index=False)
pd.set_option("display.width",340); pd.set_option("display.max_colwidth",120); pd.set_option("display.max_rows",60)
for t in ["P1","AH"]:
    d0=df[(df.target==t)&(df.misses==0)]
    print(f"\n=== {t}: zero false episodes ==="); print(d0[d0.n_false==0].sort_values(["n_out2","mean_abs"]).drop(columns=["end_lags","tr_errs","onsets","false"]).head(10).to_string())
    print(f"--- {t}: frontier"); print(d0.groupby("n_false").n_out2.min().head(4).to_string())
    b=d0[d0.n_false==0].sort_values(["n_out2","mean_abs"]).head(2)
    for _,r in b.iterrows(): print("BEST",t, dict(r[["gate","sahm","ic","br","pay"]]), "\n onsets", r.onsets, "\n lags", r.lags, "end", r.end_lags, "tr_err", r.tr_errs)
