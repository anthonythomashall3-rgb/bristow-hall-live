"""THE DIARY SCORED. The three walk-forward runs concatenated and judged as a live record: every OPEN is matched to the
first recession whose window it falls in; anything unmatched is a false alarm."""
exec(open('causal28.py').read().split('MODE=sys.argv[2]')[0].replace("out=open('causal28_%s.out'%(sys.argv[2] if len(sys.argv)>2 else 'fast'),'w')","out=open('walk2.out','w')"))
import pickle,glob
LOG=[]
for f in sorted(glob.glob('cache/walk1_*.pkl')): LOG+=pickle.load(open(f,'rb'))
LOG.sort(key=lambda x:x[0])
P(f"THE WALK-FORWARD DIARY, {LOG[0][0]:%Y} to {LOG[-1][0]:%Y} — {len(LOG)} entries")
P(f"{'published':11s} {'kind':6s} {'dated':8s} {'leg':4s} {'matched to':10s} {'lag d':>6s} {'date err':>9s}")
used=set(); opens=[]; false_alarms=[]
for pub,kind,dt,leg,p in LOG:
    if kind!='OPEN':
        P(f"{pub:%Y-%m-%d}  {kind:6s} {dt:%Y-%m}  {leg:4s}"); continue
    hit=None
    for i,(pk,tr) in enumerate(zip(PK,TR)):
        if pk-pd.DateOffset(months=6)<=dt<=tr and i not in used: hit=i; break
    if hit is None:
        false_alarms.append((pub,dt)); P(f"{pub:%Y-%m-%d}  {kind:6s} {dt:%Y-%m}  {leg:4s} {'FALSE ALARM':10s}")
    else:
        used.add(hit); lag=(pub-me(PK[hit])).days; err=(dt.year-PK[hit].year)*12+dt.month-PK[hit].month
        opens.append((hit,lag,err)); P(f"{pub:%Y-%m-%d}  {kind:6s} {dt:%Y-%m}  {leg:4s} {PK[hit]:%Y-%m}   {lag:6d} {err:+9d}")
lg=[l for _,l,_ in opens]; er=[e for _,_,e in opens]
P(f"\nSCORE OF THE DIARY — the tool as it would actually have run, 1949 forward")
P(f"   recessions the tool was alive for: 12 of 13 (it begins after the 1948-49 recession had already opened)")
P(f"   detected: {len(opens)}/12")
P(f"   FALSE ALARMS in {int((LOG[-1][0]-LOG[0][0]).days/365.25)} years: {len(false_alarms)} {false_alarms}")
P(f"   onset lags: {sorted(lg)}")
P(f"   median {np.median(lg):.1f} days, mean {np.mean(lg):.1f}, within the month {sum(1 for x in lg if x<=31)}/12")
P(f"   dates: exact {sum(1 for e in er if e==0)}, within one month {sum(1 for e in er if abs(e)<=1)}, worst {max(abs(e) for e in er)}")
ex=[l for i,l,_ in opens if PK[i].year!=1960]
P(f"   excluding 1960 (the tool had two prior recessions to learn from): mean {np.mean(ex):.1f}, median {np.median(ex):.1f}")
P(f"\n   FROZEN, for comparison, over the same twelve: mean 32.4, median 33.5")
out.close()
