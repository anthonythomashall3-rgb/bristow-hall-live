"""THE DIARY ON THE SAMPLE THE INSTRUMENT ACTUALLY REACHES. Anthony: start where the data we need exists, and only the
walk-forward counts. The rule needs seven objects. The last of them to acquire a vintage record is the factory-hours
pair — ALFRED's AWHMAN and NDMANEMP vintages begin 3 NOVEMBER 1961. Housing starts begin 21 July 1960, the unemployment
rate 15 March 1960 (which is why SAHMREALTIME starts in December 1959), the paper spread 20 April 1956. So the first
date on which the WHOLE instrument exists is November 1961, and the first recession it can be tested on is 1969.
Everything before that is a data wall, not a miss (Rule 22, scoping). The diary is rescored on that sample."""
exec(open('causal28.py').read().split('MODE=sys.argv[2]')[0].replace("out=open('causal28_%s.out'%(sys.argv[2] if len(sys.argv)>2 else 'fast'),'w')","out=open('walk4.out','w')"))
import pickle,glob
LOG=[]
for f in sorted(glob.glob('cache/walk1_*.pkl')): LOG+=pickle.load(open(f,'rb'))
LOG.sort(key=lambda x:x[0])
START=pd.Timestamp('1961-11-03')
P("THE INSTRUMENT'S OWN START DATE, object by object (first vintage or first observation):")
P("   paper spread (H.15 commercial paper less the bill)   20 April 1956   — printed at the time, never revised")
P("   unemployment rate (ALFRED UNRATE vintages)           15 March 1960   — SAHMREALTIME starts December 1959 for this reason")
P("   housing starts (ALFRED HOUST vintages)               21 July 1960")
P("   factory hours and nondurable employment (ALFRED)      3 November 1961  <- the binding one")
P("   insured unemployment rate (Department first prints)   1949")
P("   initial claims (advance figures)                     October 2002; the current file before")
P("   vacancy rate (JOLTS vintages)                        11 August 2010; the Barnichon reconstruction before")
P(f"\n   THE WHOLE INSTRUMENT EXISTS FROM {START:%d %B %Y}. The first recession it can be tested on is December 1969.")
opens=[x for x in LOG if x[1]=='OPEN']
used=set(); rows=[]; fa=[]
for pub,kind,dt,leg,p in opens:
    hit=None
    for i,(pk,tr) in enumerate(zip(PK,TR)):
        if pk-pd.DateOffset(months=6)<=dt<=tr and i not in used: hit=i; break
    if hit is None: fa.append((pub,dt)); continue
    used.add(hit); rows.append((hit,pub,dt,leg,(pub-me(PK[hit])).days,(dt.year-PK[hit].year)*12+dt.month-PK[hit].month))
IN=[r for r in rows if PK[r[0]]>=pd.Timestamp('1969-01-01')]
fa_in=[x for x in fa if x[0]>=START]
P(f"\nTHE DIARY ON THE INSTRUMENT'S OWN SAMPLE — the nine recessions from December 1969")
P(f"{'peak':9s} {'published':11s} {'dated':8s} {'leg':4s} {'lag':>5s} {'err':>4s}")
for i,pub,dt,leg,lag,err in IN: P(f"{PK[i]:%Y-%m}  {pub:%Y-%m-%d}  {dt:%Y-%m}  {leg:4s} {lag:5d} {err:+4d}")
lg=[r[4] for r in IN]; er=[r[5] for r in IN]
P(f"\n   detected {len(IN)}/9")
P(f"   FALSE ALARMS from {START:%B %Y} to today ({(pd.Timestamp('2026-09-01')-START).days/365.25:.0f} years): {len(fa_in)}")
P(f"   lags {sorted(lg)}")
P(f"   MEDIAN {np.median(lg):.0f} days, mean {np.mean(lg):.1f}, within the month {sum(1 for x in lg if x<=31)}/9")
P(f"   dates exact {sum(1 for e in er if e==0)}, within one month {sum(1 for e in er if abs(e)<=1)}, worst {max(abs(e) for e in er)}")
P(f"\n   for comparison, the whole diary 1950-2026: median 36, mean 50.3, 12/12 detected, zero false alarms")
P(f"   and the three turns dropped (1953, 1957, 1960) are the ones §5gg proved cannot be brought inside the month:")
P(f"   at each of them exactly ONE demand object existed in the world.")
out.close()
