"""Stage 38: v6 = v5 + the live lane's advancing channels. Lane rule: a lane channel may open an episode only if a frozen (v5)
channel fires within the next 120 days; otherwise the lane opening is void and logged as a lane false alarm. Scored on the record."""
exec(open("stage37_lane.py").read().split("res=[r for r in res if r]")[0])
sel=['Sahm>=0.55 x1 [nogate]','IUR gap>=0.5 [nogate]','claims 8wk>=40% [nogate]','bill fall>=2.5/60d [nogate]','sentiment -15 [nogate]','housing -25% x2 [nogate]','IP 3m first print <=-2.0% x2 [nogate]']
FAST=[SAHM[0.35], gapch(iur4,0.40), PAY, UM["um_d1_10"], persist2(h3,20), fall(tb6,60,1.43)]
frozen=np.zeros(N,bool)
for c in FAST: frozen|=fresh(c,120)&GATE[12]
for nm in sel: frozen|=fresh(BS[nm],120)
def lane_arr(series, lagd, thr): x=dl(series,lagd); return D(x>=thr)&GATE[12]
LANE={"VIX 20d change>=17.4 (1990->)":lane_arr(vix-vix.shift(20),1,17.425),
      "Baa-10y rise from 250d min>=1.5 (1987->)":lane_arr(baa-baa.rolling(250).min(),1,1.5),
      "OFR funding stress>=2.36 (2000->, backfilled pre-2017)":lane_arr(of["Funding"],1,2.358),
      "OFR FSI>=5.64 (2000->, backfilled)":lane_arr(of["OFR FSI"],1,5.639),
      "OFR equity valuation>=1.20 (2000->, backfilled)":lane_arr(of["Equity valuation"],1,1.198),
      "NFCI level>=3.0 (1971->, backfilled)":lane_arr(nfci,6,3.0),
      "news sentiment 20d change down>=0.289 (1980->)":lane_arr(-(ns.rolling(20).mean()-ns.rolling(20).mean().shift(20)),1,0.289)}
def run(lane_names):
    lane=np.zeros(N,bool)
    for nm in lane_names: lane|=fresh(LANE[nm],120)
    # a lane opening is valid only if a frozen trigger occurs within 120 days after it
    valid=lane.copy(); lane_fa=[]
    starts=np.flatnonzero(np.diff(lane.astype(np.int8))==1)+1
    for i in starts:
        if not frozen[i:i+121].any():
            j=i
            while j<N and lane[j]: valid[j]=False; j+=1
            if cal[i]>=pd.Timestamp("1968-06-01"): lane_fa.append(str(cal[i].date()))
    trig=frozen|valid
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
    return eps, lane_fa
T={pk:(P(pk)+1).to_timestamp() for pk,tr in T_P1}
for nm_set,label in [(["VIX 20d change>=17.4 (1990->)","Baa-10y rise from 250d min>=1.5 (1987->)"],"real-time lane only (VIX, Baa)"),
                     (list(LANE),"full lane (incl. backfilled OFR, NFCI)")]:
    eps,lfa=run(nm_set); res,false=score_eps(eps,T_P1)
    print(f"\nv6 [{label}]: false episodes {false} | lane openings voided (no frozen follow-up) {lfa}")
    for r in res:
        d=(pd.Timestamp(r['onset'])-T[r['peak']]).days
        print(f"  {r['peak']}: call {r['onset']} lag {r['lag']:+d} | days from recession's first day {d:+d} | end lag {r['end_lag']:+d}")
# which lane channel fired first in the advanced calls
for nm,a in LANE.items():
    for pk in ["1981-07","2007-12","2020-02"]:
        lo=cal.searchsorted((P(pk)-2).to_timestamp()); hi=cal.searchsorted((P(pk)+1).to_timestamp(how="end")); seg=(fresh(a,120))[lo:hi+1]
        if seg.any(): print(f"  {nm} first on in {pk} window: {cal[lo+int(np.argmax(seg))].date()}")
