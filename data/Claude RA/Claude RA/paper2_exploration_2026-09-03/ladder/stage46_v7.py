"""Stage 46: v7 = v6 minus the sentiment channel (both the fast −10 and the backstop −15), which round 17 showed carries a third
of the false-alarm risk and changes no call. Then: (a) confirm the record, (b) the end-condition test with the fuller channel set,
(c) a +-1-tick perturbation map of every threshold, (d) leave-one-out and recursive re-selection on the v7 menu."""
exec(open("stage38_v6.py").read().split("T={pk:(P(pk)+1)")[0])
import warnings, itertools; warnings.filterwarnings("ignore")
LANE2=["VIX 20d change>=17.4 (1990->)","Baa-10y rise from 250d min>=1.5 (1987->)"]
FASTn=["Sahm 0.35","IUR 0.40","payrolls 0.1","sentiment 10","housing 20","bill 1.43"]
BSn=['Sahm>=0.55 x1 [nogate]','IUR gap>=0.5 [nogate]','claims 8wk>=40% [nogate]','bill fall>=2.5/60d [nogate]','sentiment -15 [nogate]','housing -25% x2 [nogate]','IP 3m first print <=-2.0% x2 [nogate]']
def build(fast, bsl, lane=LANE2):
    frozen=np.zeros(N,bool)
    for c in fast: frozen|=fresh(c,120)&GATE[12]
    for nm in bsl: frozen|=fresh(BS[nm],120)
    lanearr=np.zeros(N,bool)
    for nm in lane: lanearr|=fresh(LANE[nm],120)
    valid=lanearr.copy(); lfa=[]
    for i in np.flatnonzero(np.diff(lanearr.astype(np.int8))==1)+1:
        if not frozen[i:i+121].any():
            j=i
            while j<N and lanearr[j]: valid[j]=False; j+=1
            if cal[i]>=pd.Timestamp("1968-06-01"): lfa.append(str(cal[i].date()))
    return frozen|valid, lfa
def replay(trig, endpct=0.03, conf=None):
    eps=[]; open_=False; i=0
    while i<N:
        if not open_:
            if trig[i] and cal[i]>=pd.Timestamp("1968-06-01"): open_=True; start=i; runmax=-1; pk=None; endcall=None; cmax=-np.inf
            i+=1; continue
        v=ma8d[i]
        if not np.isnan(v):
            if v>runmax: runmax=v; pk=i; endcall=None
        if conf is not None and not np.isnan(conf[i]): cmax=max(cmax,conf[i])
        ok=(not np.isnan(v)) and pk is not None and v<=runmax*(1-endpct)
        if conf is not None: ok=ok and (not np.isnan(conf[i])) and conf[i]<cmax-1e-12
        if ok and endcall is None: endcall=i
        if endcall is not None and B3[i] and CALM[i]:
            eps.append(dict(onset=cal[start],trough_week=cal[pk],end_call=cal[endcall],close=cal[i])); open_=False
        i+=1
    if open_: eps.append(dict(onset=cal[start],trough_week=cal[pk] if pk else None,end_call=cal[endcall] if endcall else None,close=None))
    return eps
FASTa=[SAHM[0.35], gapch(iur4,0.40), PAY, UM["um_d1_10"], persist2(h3,20), fall(tb6,60,1.43)]
V7fast=[FASTa[i] for i in [0,1,2,4,5]]; V7bs=[BSn[i] for i in [0,1,2,3,5,6]]
t6,l6=build(FASTa,BSn); t7,l7=build(V7fast,V7bs)
for nm,t,l in [("v6",t6,l6),("v7 (no sentiment)",t7,l7)]:
    eps=replay(t); res,false=score_eps(eps,T_P1)
    print(f"{nm}: false {false} | lane voided {l} | onsets {[r['onset'] for r in res]} | lags {[r['lag'] for r in res]} | ends {[r['end_lag'] for r in res]}")
print("\n=== (b) END with a second condition (v7 episodes) ===")
def sd(s,lag): x=s.copy(); x.index=x.index+pd.Timedelta(days=lag); return x.reindex(cal).ffill().values
cc=load(ODD+"01_labor_unemployment/weekly/CCSA.csv")
CONF={"none":None,"IUR 4wk off peak":sd(iur.rolling(4).mean(),12),"IUR 8wk off peak":sd(iur.rolling(8).mean(),12),"CC 4wk off peak":sd(cc.rolling(4).mean(),12),"CC 8wk off peak":sd(cc.rolling(8).mean(),12)}
TR=[t for p,t in T_P1]
for cn,cf in CONF.items():
    for pct in [0.02,0.03]:
        eps=replay(t7,pct,cf); res,false=score_eps(eps,T_P1)
        # count withdrawn: an end call that a later new claims high overturns is recorded as endcall reset; recount directly
        wd=0
        for e,tr in zip(eps,TR):
            i0=int(np.where(cal==e["onset"])[0][0]); i1=int(np.where(cal==e["close"])[0][0]) if e["close"] is not None else N-1
            runmax=-np.inf; pk=None; called=None
            for i in range(i0,i1+1):
                v=ma8d[i]
                if not np.isnan(v):
                    if v>runmax:
                        if called is not None: wd+=1; called=None
                        runmax=v; pk=i
                cok=(cf is None) or ((not np.isnan(cf[i])) and cf[i]<np.nanmax(cf[i0:i+1])-1e-12)
                if (not np.isnan(v)) and pk is not None and v<=runmax*(1-pct) and cok and called is None: called=i
        L=[r["end_lag"] for r in res]
        print(f"  end claims -{int(pct*100)}% & {cn:18s}: end lags {L} | within a month {sum(1 for x in L if x is not None and abs(x)<=1)} | withdrawn {wd} | trough err {[r['tr_err'] for r in res]}")
