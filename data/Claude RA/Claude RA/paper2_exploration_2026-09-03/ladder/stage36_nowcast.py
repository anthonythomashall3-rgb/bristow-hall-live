"""Stage 36: a single-call nowcast channel. The Sahm print for month M arrives ~5 days after M ends; the insured-unemployment
rate for the CPS reference week (the week containing the 12th) arrives ~T-8 days before M ends. Build a mixed-frequency Sahm
indicator: S~(M) = mean(U[M-2], U[M-1], U^[M]) - min over the prior 12 months, with U^[M] = U[M-1] + b * (IURref[M] - IURref[M-1]),
b estimated on an expanding window of PAST months only (no look-ahead). The channel fires once, when S~ crosses a threshold set
by the maximum-margin rule; it is never revised or superseded — one call. Test: quiet maxima, first crossings, and what it adds to v5."""
exec(open("stage32_backstops.py").read().split("rows=[]")[0])
# monthly first-print unemployment rate by month (from the Sahm vintage file: u_latest is the first print of latest_month)
rt=pd.read_csv(HOME+"/mnt/Recession Papers/Paper 2/data/realtime_first_print_sahm_by_vintage.csv", parse_dates=["vintage","latest_month"])
fpu=rt.sort_values("vintage").drop_duplicates("latest_month", keep="first").set_index("latest_month").u_latest.sort_index()
# reference-week IUR: the week containing the 12th; published the Thursday 12 days after the week ends (continued claims lag)
iurw=iur.copy()   # index = week ending Saturday
ref={}; pub={}
for m in pd.period_range("1971-02","2026-08",freq="M"):
    d12=pd.Timestamp(m.year,m.month,12); wk_end=d12+pd.Timedelta(days=(5-d12.weekday())%7)   # Saturday on/after the 12th
    if wk_end in iurw.index: ref[m.to_timestamp()]=iurw[wk_end]; pub[m.to_timestamp()]=wk_end+pd.Timedelta(days=12)
ref=pd.Series(ref).sort_index(); pub=pd.Series(pub).sort_index()
# expanding-window bridge: dU[M] = b * dIURref[M], b from months before M (both first-print U changes and ref-week IUR changes)
dU=fpu.diff(); dR=ref.diff(); common=dU.index.intersection(dR.index)
bs={}
for i,m in enumerate(common):
    past=common[:i]; past=past[past<m]
    if len(past)<36: continue
    x=dR[past].values; y=dU[past].values; ok=~(np.isnan(x)|np.isnan(y))
    bs[m]=float((x[ok]*y[ok]).sum()/(x[ok]**2).sum())
bs=pd.Series(bs)
# nowcast Sahm for month M on the reference-week publication day
rows=[]
for m in bs.index:
    if m not in fpu.index or m not in ref.index: continue
    hist=fpu[fpu.index<m]
    if len(hist)<14: continue
    uhat=hist.iloc[-1]+bs[m]*(ref[m]-ref[ref.index<m].iloc[-1])
    seq=list(hist.iloc[-2:].values)+[uhat]; u3=np.mean(seq)
    prior=[np.mean(hist.iloc[j-2:j+1].values) for j in range(len(hist)-12, len(hist))]
    rows.append(dict(month=m, pubday=pub[m], S_now=u3-min(prior), S_actual=Srel.get(rt[rt.latest_month==m].sort_values("vintage").vintage.iloc[0], np.nan) if (rt.latest_month==m).any() else np.nan))
nc=pd.DataFrame(rows).set_index("pubday").sort_index()
print("nowcast months:", len(nc), nc.index.min().date(), nc.index.max().date(), "| corr(S_now, S_actual) =", round(nc[["S_now","S_actual"]].dropna().corr().iloc[0,1],3), "| mean lead vs the jobs report (days):", int((pd.Series([ (rt[rt.latest_month==m].sort_values('vintage').vintage.iloc[0]-p).days for p,m in zip(nc.index, nc.month) if (rt.latest_month==m).any()])).mean()))
Sn=nc.S_now
allowed=np.zeros(N,bool)
for pk,tr in T_P1:
    lo=cal.searchsorted((P(pk)-2).to_timestamp()); hi=cal.searchsorted((P(tr)+12).to_timestamp(how="end")); allowed[lo:hi+1]=True
v=Sn.reindex(cal).ffill().values
for gated,tag in [(True,"gated"),(False,"ungated")]:
    q=(~allowed)&(cal>=pd.Timestamp("1974-06-01"))&(GATE[12] if gated else True)
    print(f"  nowcast Sahm quiet max ({tag}) = {np.nanmax(v[q]):.3f} on {cal[q][np.nanargmax(v[q])].date()}")
for pk,tr in T_P1[2:]:
    lo=cal.searchsorted((P(pk)-1).to_timestamp()); hi=cal.searchsorted((P(pk)+2).to_timestamp(how="end")); w=v[lo:hi+1]
    print(f"  {pk}: nowcast max in [peak-1, peak+2] = {np.nanmax(w):.3f}")
V5g=[SAHM[0.35], gapch(iur4,0.40), PAY, UM["um_d1_10"], persist2(h3,20), fall(tb6,60,1.43)]
for th in [0.35,0.40,0.45,0.50]:
    NC=D(Sn>=th-1e-9)
    eps=replay3(V5g+[NC], GATE[12], 120); res,false=score_eps(eps,T_P1)
    alone=score(pd.Series(NC&GATE[12], index=cal), "x", start="1974-06-01")
    print(f"  v5 + nowcast Sahm>={th}: false {false[:3]} lags {[r['lag'] for r in res]} onsets {[r['onset'] for r in res][2:]} | alone gated: fa {alone['n_fa']} lags {alone['lags']}")
