"""Stage 44: extreme-value estimate of the false-alarm rate, and a knockout estimate of the miss rate.
A bootstrap cannot exceed the observed maximum, so the quiet tail is fitted instead: annual maxima of each frozen channel's
quiet statistic -> GEV -> P(annual max >= threshold). Union across channels gives the rule's annual false-alarm probability."""
exec(open("stage43_risk2.py").read().split('print("\\n=== BLOCK BOOTSTRAP')[0])
from scipy import stats
print("\n=== (B) EXTREME-VALUE FALSE-ALARM RATE (GEV on annual quiet maxima) ===")
print(f"{'channel':20s} {'thresh':>7s} {'n yrs':>5s} {'quiet max':>9s} {'P(year)':>9s} {'1-in-N yrs':>11s}")
ps={}
for nm,st,lag,thr,gated,k in CH:
    if nm not in SER: continue
    x=dl(st,lag)
    if k>1: x=pd.Series(np.minimum(x.values,np.r_[np.nan,x.values[:-1]]), index=x.index)
    v=x.reindex(cal).ffill(); q=(~allowed)&(~openmask)&(cal>=pd.Timestamp("1968-06-01"))&(GATE[12] if gated else np.ones(N,bool))
    s=pd.Series(v.values[q], index=cal[q]).dropna()
    am=s.groupby(s.index.year).max(); am=am[s.groupby(s.index.year).size()>=60]
    if len(am)<12: print(f"{nm:20s} too few quiet years ({len(am)})"); continue
    try:
        c,loc,sc=stats.genextreme.fit(am.values)
        p=float(stats.genextreme.sf(thr,c,loc,sc))
    except Exception: p=np.nan
    ps[nm]=p
    print(f"{nm:20s} {thr:7.3f} {len(am):5d} {am.max():9.3f} {p:9.5f} {('1 in %.0f'%(1/p)) if p>0 else 'never':>11s}")
good=[p for p in ps.values() if p==p]
pu_ind=1-np.prod([1-p for p in good])
print(f"\n  union, independent channels: P(false alarm in a year) = {pu_ind:.4f}  -> about 1 in {1/pu_ind:.0f} years")
print(f"  union, perfectly dependent (max channel): {max(good):.4f} -> 1 in {1/max(good):.0f} years")
print(f"  10-year probability of at least one false alarm: {1-(1-pu_ind)**10:.3f} (independent) to {1-(1-max(good))**10:.3f} (dependent)")
print(f"  cross-check, rule of three on 0 in 58 gated quiet years: annual rate <= {3/58:.4f} at 95% confidence")
print("\n=== (C) MISS RATE: channel knockout on the record ===")
FAST=[SAHM[0.35], gapch(iur4,0.40), PAY, UM["um_d1_10"], persist2(h3,20), fall(tb6,60,1.43)]
fastn=["Sahm","IUR","payrolls","sentiment","housing","bill"]
seln=['Sahm>=0.55 x1 [nogate]','IUR gap>=0.5 [nogate]','claims 8wk>=40% [nogate]','bill fall>=2.5/60d [nogate]','sentiment -15 [nogate]','housing -25% x2 [nogate]','IP 3m first print <=-2.0% x2 [nogate]']
def episodes(fast_idx, bs_idx):
    trig=np.zeros(N,bool)
    for i in fast_idx: trig|=fresh(FAST[i],120)&GATE[12]
    for j in bs_idx: trig|=fresh(BS[seln[j]],120)
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
            eps.append(dict(onset=cal[start],trough_week=cal[pk],end_call=cal[endcall],close=cal[i])); open_=False
        i+=1
    if open_: eps.append(dict(onset=cal[start],trough_week=cal[pk] if pk else None,end_call=cal[endcall] if endcall else None,close=None))
    return eps
base=list(range(6)); bs=list(range(7))
r0,_=score_eps(episodes(base,bs),T_P1); print("  full rule: misses", sum(1 for r in r0 if r['lag'] is None))
for i,nm in enumerate(fastn):
    r,_=score_eps(episodes([x for x in base if x!=i],bs),T_P1); m=[r0[j]['peak'] for j in range(9) if r[j]['lag'] is None]
    late=[(r0[j]['peak'], r[j]['lag']) for j in range(9) if r[j]['lag'] is not None and r0[j]['lag'] is not None and r[j]['lag']>r0[j]['lag']]
    print(f"  drop fast '{nm}': misses {m if m else 'none'}; later calls {late if late else 'none'}")
for j,nm in enumerate(seln):
    r,_=score_eps(episodes(base,[x for x in bs if x!=j]),T_P1); m=[r0[i]['peak'] for i in range(9) if r[i]['lag'] is None]
    if m: print(f"  drop backstop '{nm}': misses {m}")
print("  (backstops not listed change nothing on the record — the fast channels fire first)")
