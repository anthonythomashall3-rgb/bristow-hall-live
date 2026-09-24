"""Stage 32: closing the blind spot. (A) UNGATED backstop channels — thresholds set by the maximum-margin rule on the ungated
record (so a recession with no prior curve inversion is still called); (B) an activity backstop on first prints (IP, payrolls,
real disposable income) for a recession that spares the labor market's claims data; (C) v5 = v4 (gated fast channels) OR the
backstops, scored for zero false episodes and lags; coverage matrix: which channel sees which recession."""
exec(open("stage31_v4.py").read().split("V3=[SAHM[0.35]")[0])
NOGATE=np.ones(N,bool)
def quiet_max(arr_series, lagd, gated):
    v=arr_series.reindex(cal).ffill().values if lagd is None else pd.Series(arr_series.values, index=arr_series.index+pd.Timedelta(days=lagd)).reindex(cal).ffill().values
    allowed=np.zeros(N,bool)
    for pk,tr in T_P1:
        lo=cal.searchsorted((P(pk)-2).to_timestamp()); hi=cal.searchsorted((P(tr)+12).to_timestamp(how="end")); allowed[lo:hi+1]=True
    q=(~allowed)&(cal>=pd.Timestamp("1968-06-01"))&(GATE[12] if gated else NOGATE)
    return np.nanmax(v[q]), str(cal[q][np.nanargmax(v[q])].date())
# --- A. ungated quiet maxima for each channel statistic (larger = worse) ---
s4=iur4-iur4.shift(1).rolling(52).min()
print("UNGATED quiet maxima (1968-2026, outside [peak-2, trough+12]):")
print("  Sahm first print:", quiet_max(Srel, 0, False)); print("  IUR 4wk gap:", quiet_max(s4, 12, False)); print("  claims 8wk ratio:", quiet_max(r8, 5, False))
print("  bill 60d fall:", quiet_max(-(tb6-tb6.shift(60)), 1, False)); print("  sentiment 1m fall:", quiet_max(-(um-um.shift(1)), 0, False)); print("  housing 3m first-print fall:", quiet_max(-h3, 0, False))
print("  payroll first print 1m fall:", quiet_max(pd.Series(-pay.d1.astype(float).values, index=pd.to_datetime(pay.rel.values)), 0, False))
# backstop channels (ungated)
BS={}
for th in [0.50,0.55,0.60]:
    for k in [1,2]:
        c=(Srel>=th-1e-9); 
        for j in range(1,k): c=c&(Srel.shift(j)>=th-1e-9)
        BS[f"Sahm>={th} x{k} [nogate]"]=D(pd.Series(c.values, index=Srel.index))
for g in [0.45,0.50,0.60,0.75]: BS[f"IUR gap>={g} [nogate]"]=gapch(iur4,g)
for p in [0.35,0.40,0.50]: BS[f"claims 8wk>={int(p*100)}% [nogate]"]=wk(r8>=p)
for th in [2.5,3.0]: BS[f"bill fall>={th}/60d [nogate]"]=fall(tb6,60,th)
for x in [12,15,20]: BS[f"sentiment -{x} [nogate]"]=D((um-um.shift(1))<=-x)
for x in [25,30]: BS[f"housing -{x}% x2 [nogate]"]=persist2(h3,x)
for x in [0.2,0.3]: BS[f"payrolls -{x}% [nogate]"]=D(pd.Series((pay.d1.astype(float)<=-x).values, index=pd.to_datetime(pay.rel.values)))
# --- B. activity backstop on first prints: IP, payrolls, real disposable income (1979->), 3-month changes ---
def fpch3(fn):
    df=pd.read_csv(A+fn, index_col=0, parse_dates=True); out={}
    for c in df.columns:
        s=df[c].dropna(); m=s.index[-1]
        if m in out or len(s)<4: continue
        out[m]=(pd.to_datetime(c[-8:]), s.iloc[-1]/s.iloc[-4]-1)
    return pd.Series([v[1] for v in out.values()], index=pd.to_datetime([v[0] for v in out.values()])).sort_index()
ip3=fpch3("INDPRO_all_vintages.csv"); pay3=fpch3("PAYEMS_all_vintages.csv"); inc3=fpch3("DSPIC96_all_vintages.csv")
for x in [1.5,2.0,3.0]:
    for k in [1,2]:
        c=(ip3<=-x/100); 
        for j in range(1,k): c=c&(ip3.shift(j)<=-x/100)
        BS[f"IP 3m first print <=-{x}% x{k} [nogate]"]=D(c)
    BS[f"IP 3m<=-{x}% & payrolls 3m<=-0.3% [nogate]"]=D(ip3<=-x/100)&D(pay3<=-0.003)
    BS[f"IP 3m<=-{x}% & real income 3m<=-0.5% [nogate]"]=D(ip3<=-x/100)&D(inc3<=-0.005)
rows=[]
for nm,a in BS.items():
    r=score(pd.Series(a, index=cal), nm, start="1968-06-01"); r["out1"]=sum(abs(x)>1 for x in r["lags"]); rows.append(r)
df=pd.DataFrame(rows); pd.set_option("display.width",330); pd.set_option("display.max_colwidth",110); pd.set_option("display.max_rows",100)
print("\n=== backstop channels, UNGATED, alone ===")
print(df.sort_values(["n_fa","misses","out1"]).drop(columns=["calls"]).to_string())
# --- C. v5 = v4 OR clean backstops ---
V4=[SAHM[0.35], gapch(iur4,0.40), PAY, UM["um_d1_10"], persist2(h3,20), fall(tb6,60,1.43)]
clean=[nm for nm in df[df.n_fa==0].rule]
print("\nclean ungated backstops:", clean)
def replay_mixed(gated_chs, ungated_chs):
    trig=np.zeros(N,bool)
    for c in gated_chs: trig|=fresh(c,120)&GATE[12]
    for c in ungated_chs: trig|=fresh(c,120)
    eps=[]; open_=False; i=0
    while i<N:
        if not open_:
            if trig[i] and cal[i]>=pd.Timestamp("1968-06-01"): open_=True; start=i; runmax=-1; pk=None; endcall=None
            i+=1; continue
        v=ma8d[i]
        if not np.isnan(v):
            if v>runmax: runmax=v; pk=i; endcall=None
            elif endcall is None and v<=runmax*0.97: endcall=i
        if endcall is not None and B3[i] and CALM[i]:
            eps.append(dict(onset=cal[start], trough_week=cal[pk], end_call=cal[endcall], close=cal[i])); open_=False
        i+=1
    if open_: eps.append(dict(onset=cal[start], trough_week=cal[pk] if pk else None, end_call=cal[endcall] if endcall else None, close=None))
    return eps
sel=[nm for nm in clean if any(s in nm for s in ["Sahm>=0.5 x2","IUR gap>=0.5 ","claims 8wk>=40","bill fall>=2.5","sentiment -15","housing -25","payrolls -0.2","IP 3m first print <=-2.0% x2","IP 3m<=-2.0% & payrolls"])]
print("selected backstops:", sel)
eps=replay_mixed(V4,[BS[n] for n in sel]); res,false=score_eps(eps,T_P1)
print("v5 (v4 gated OR backstops ungated): false", false, "lags", [r["lag"] for r in res], "onsets", [r["onset"] for r in res])
# coverage matrix: for each recession, which channels (gated fast / ungated backstop) are on inside [peak-1, peak+1] and first date
names=["Sahm.35g","IUR.40g","pay.1g","sent10g","hou20g","bill1.43g"]+sel
arrs=[fresh(c,120)&GATE[12] for c in V4]+[fresh(BS[n],120) for n in sel]
print("\nCOVERAGE (first day on inside [peak-2, peak+2]):")
for pk,tr in T_P1:
    lo=cal.searchsorted((P(pk)-2).to_timestamp()); hi=cal.searchsorted((P(pk)+2).to_timestamp(how="end"))
    hits=[(nm, str(cal[lo+int(np.argmax(a[lo:hi+1]))].date())) for nm,a in zip(names,arrs) if a[lo:hi+1].any()]
    print(f"  {pk}: {hits}")
# blind-spot simulation: gate OFF everywhere (a recession with no inversion) — what would the ungated backstops alone have called?
eps0=replay_mixed([],[BS[n] for n in sel]); res0,false0=score_eps(eps0,T_P1)
print("\nBACKSTOPS ALONE (no gate anywhere): false", false0, "lags", [r["lag"] for r in res0], "onsets", [r["onset"] for r in res0])
