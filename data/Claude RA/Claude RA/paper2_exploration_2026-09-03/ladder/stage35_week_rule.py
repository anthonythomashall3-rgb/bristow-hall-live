"""Stage 35: (1) assemble the in-week onset rule from the economically meaningful admissible channels of stage 34, score it
(false alarms, days from T, and the margin each threshold has); (2) the END frontier in days: fastest claims confirmation vs
withdrawn (false) end calls; (3) ends with a second condition that could block the 1970/1974 pauses."""
exec(open("stage31_v4.py").read().split("V3=[SAHM[0.35]")[0])
DF=HOME+"/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03/data_fetched/"
def loadfred(f):
    s=pd.read_csv(f); s=s[s.value!="."]; s.index=pd.to_datetime(s.date); return s.value.astype(float).sort_index()
def dl(s, lagd): x=s.dropna().copy(); x.index=x.index+pd.Timedelta(days=lagd); return x
T={pk:(P(pk)+1).to_timestamp() for pk,tr in T_P1}
# --- (1) in-week channels, thresholds at the gated quiet maximum + epsilon (as in stage 34) ---
ccsa=load(ODD+"01_labor_unemployment/weekly/CCSA.csv"); cc26=np.log(ccsa/ccsa.shift(26))
t6ff=loadfred(DF+"fred_daily/T6MFF.csv") if os.path.exists(DF+"fred_daily/T6MFF.csv") else None
dtb6=loadfred(DF+"fred_daily/DTB6.csv"); brent=loadfred(DF+"extra/DCOILBRENTEU.csv")
u6=pd.read_csv(A+"U6RATE_all_vintages.csv", index_col=0, parse_dates=True); out={}
for c in u6.columns:
    s=u6[c].dropna(); m=s.index[-1]
    if m in out or len(s)<14: continue
    out[m]=(pd.to_datetime(c[-8:]), s.iloc[-1]-s.iloc[-13:].min())
u6up=pd.Series([v[1] for v in out.values()], index=pd.to_datetime([v[0] for v in out.values()])).sort_index()
iur8=iur.rolling(8).mean(); g8=iur8-iur8.shift(1).rolling(52).min()
def qmax(series, lagd, gated=True):
    v=dl(series,lagd).reindex(cal).ffill().values
    allowed=np.zeros(N,bool)
    for pk,tr in T_P1:
        lo=cal.searchsorted((P(pk)-2).to_timestamp()); hi=cal.searchsorted((P(tr)+12).to_timestamp(how="end")); allowed[lo:hi+1]=True
    q=(~allowed)&(cal>=pd.Timestamp("1968-06-01"))&(GATE[12] if gated else True)
    return float(np.nanmax(v[q]))
W={}
Q=qmax(cc26,12); W[f"continued claims 26wk log change > {Q:.3f} [gate]"]=(D(dl(cc26,12)>Q+1e-9), True)
Q=qmax(g8,12,False); W[f"IUR 8wk gap > {Q:.3f} [nogate]"]=(D(dl(g8,12)>Q+1e-9), False)
if t6ff is not None:
    x=t6ff-t6ff.shift(20); Q=qmax(x,1); W[f"6mo bill minus funds, 20d rise > {Q:.2f} [gate]"]=(D(dl(x,1)>Q+1e-9), True)
x=-(dtb6-dtb6.rolling(250).max()); Q=qmax(x,1); W[f"6mo bill drawdown from 250d max > {Q:.2f} [gate]"]=(D(dl(x,1)>Q+1e-9), True)
x=np.log(brent/brent.shift(20)); Q=qmax(x,1); W[f"Brent 20d log rise > {Q:.3f} [gate]"]=(D(dl(x,1)>Q+1e-9), True)
Q=qmax(u6up,0); W[f"U-6 first print over 12m min > {Q:.2f} [gate]"]=(D(dl(u6up,0)>Q+1e-9), True)
trig=np.zeros(N,bool)
for nm,(a,g) in W.items(): trig|=fresh(a,120)&(GATE[12] if g else True)
def replay_trig(trig):
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
eps=replay_trig(trig); res,false=score_eps(eps,T_P1)
print("IN-WEEK RULE (thresholds at quiet max + epsilon):", list(W))
print("  false episodes:", false)
for r in res:
    d=(pd.Timestamp(r['onset'])-T[r['peak']]).days if r['onset'] else None
    print(f"  {r['peak']}: call {r['onset']} | days from recession's first day {d} | end lag {r['end_lag']}")
# --- (2) END frontier in days from the expansion's first day (first day after trough month), v5 episodes ---
V5eps=replay3([SAHM[0.35], gapch(iur4,0.40), PAY, UM["um_d1_10"], persist2(h3,20), fall(tb6,60,1.43)], GATE[12], 120)
TR=[t for p,t in T_P1]; TE={t:(P(t)+1).to_timestamp() for t in TR}
def series_daily(s, lag): x=s.copy(); x.index=x.index+pd.Timedelta(days=lag); return x.reindex(cal).ffill().values
ma={n: series_daily(ic.rolling(n).mean(),5) for n in [2,3,4,6,8]}
def end_calls(vals, i0, i1, pct, minage=0):
    runmax=-np.inf; pk=None; calls=[]; called=False
    for i in range(i0,i1+1):
        v=vals[i]
        if np.isnan(v): continue
        if v>runmax:
            if called: calls[-1][2]=True; called=False
            runmax=v; pk=i
        elif not called and pk is not None and (i-pk)>=minage and v<=runmax*(1-pct): calls.append([i,pk,False]); called=True
    return calls
print("\nEND FRONTIER (days from the expansion's first day; withdrawn = provisional end calls overturned by a new claims high):")
for n in [2,3,4,6,8]:
    for pct in [0.01,0.02,0.03,0.05]:
        days=[]; wd=0
        for e,tr in zip(V5eps,TR):
            i0=int(np.where(cal==e["onset"])[0][0]); i1=int(np.where(cal==e["close"])[0][0]) if e["close"] is not None else N-1
            calls=end_calls(ma[n],i0,i1,pct)
            wd+=sum(1 for c in calls if c[2]); fin=[c for c in calls if not c[2]]; c=fin[-1] if fin else (calls[-1] if calls else None)
            days.append((cal[c[0]]-TE[tr]).days if c else None)
        print(f"  claims ma{n} down {int(pct*100)}%: days {days} | within 7d: {sum(1 for d in days if d is not None and abs(d)<=7)} | withdrawn {wd}")
