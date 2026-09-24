"""(a) THE LIVE EDGE — what v2.4 reads on the latest data of every object, today; (b) the real-time grade of every object;
(c) the strictly-real-time era (claims advance figures 2002-, JOLTS vintages 2010-): what the rule did there."""
from mini import *
from legu_min import s_cur, spl
exec(open('fast37.py').read().split("RES={}")[0].replace("out=open('fast37.out','w')","out=open('rt2.out','w')"))
P("OBJECT SPANS AND REAL-TIME GRADE")
gp=(spl-spl.rolling(52,min_periods=52).min().shift(1)).dropna()
P(f"   insured unemployment rate (weekly): {spl.index.min().date()} -> {spl.index.max().date()}; genuine first prints from 2002-10 (DOL advance, collection 45); before that the Department's current file (Greenbook monthly first prints 1973-85 in collection 74 grade it)")
P(f"   unemployment rate (Sahm, pair half): ALFRED first prints {g.index.min().date()} -> {g.index.max().date()}, actual release dates")
P(f"   housing starts: ALFRED first prints, vintages from 1960-07, actual release dates; latest {hous_half.dropna().index.max().date()}")
P(f"   vacancy rate: JOLTS ALFRED vintages from {relJ.index.min().date()} (release dates 2004-09 from the BLS archive); BEFORE Dec 2000 the Barnichon/PNZ help-wanted RECONSTRUCTION — not a vintage series")
P(f"   hours x nondurable pair: ALFRED first prints, vintages from 1961")
P(f"   closers K, H: the Department's current weekly/monthly file (K continued claims, H initial claims); S on the unemployment rate's first prints")
P("\nLIVE EDGE — latest reading of every object")
P(f"   insured rate gap (52-week low), latest week {gp.index.max().date()}: {gp.iloc[-1]:.2f}  (0.45 branch line 0.45, low branch 0.25); last 8 weeks {[round(x,2) for x in gp.tail(8)]}")
P(f"   Sahm on first prints, latest month {g.index.max():%Y-%m}: {g.iloc[-1]:.2f} (line 0.43); last 8 {[round(x,2) for x in g.tail(8)]}")
P(f"   vacancy (2,6) gap, latest {vr.index.max():%Y-%m}: {vr.iloc[-1]:.2f} (line 0.36); last 8 {[round(x,2) for x in vr.tail(8)]}")
P(f"   housing half (starts 35), latest {hous_half.dropna().index.max():%Y-%m}: {hous_half.dropna().iloc[-1]:.2f}; rate half (4 tenths) {rate4.dropna().iloc[-1]:.2f}; pair {M35.iloc[-1]:.2f} (line 1.0); pair last 8 {[round(x,2) for x in M35.tail(8)]}")
P(f"   hours pair, latest {P1x.index.max():%Y-%m}: {P1x.iloc[-1]:.2f} (line 1.0)")
LP=leg_gapx(spl,0.25,rearm='window')+FH25; L=confirm_w(LP,[H35],'month'); X=hub_actual(0.43,vr,0.36); U1=confirm_w(leg_gapx(spl,0.45,rearm='zero')+FHz,[VJ36,Ppx],'month')
allc=sorted([(p,dd,c) for v in [U1,L,X] for p,dd,c in v])
P(f"   last proposal of any branch: {[(p.strftime('%Y-%m-%d'),dd.strftime('%Y-%m'),c) for p,dd,c in allc if p>pd.Timestamp('2024-01-01')]}")
P(f"   STATE: closed since 2024-12-05 (leg S, dated 2024-08). No branch proposes 2025-26.")
P("\nSTRICTLY REAL-TIME ERA (every object a genuine first print): claims from 2002-10, JOLTS from 2010-07")
r=run3("v2.4, first prints",{'U':U1,'L':L,'X':X})
for i in [10,11,12]:
    t=r['opens'].get(i); c=[c for v in [U1,L] for p,dd,c in v if t and p==t['published'] and dd==t['date']]
    P(f"   {PK[i]:%Y-%m}: {t['published']:%Y-%m-%d} ({r['lags_p'][i]} d) by {c[0] if c else 'hub'}; every object first-print except the vacancy before 2010 (2007 uses starts + the rate, both first prints — fully real-time)")
P("\n2025-26 on every object (the live no-call, both vintages):")
for nm,ser,line in [('insured-rate gap',gp,0.25),('Sahm fp',g,0.43),('vacancy gap',vr,0.36),('pair',M35,1.0)]:
    w=ser['2025-06':]; P(f"   {nm}: max {w.max():.2f} at {w.idxmax():%Y-%m}{'' if hasattr(w.index,'month') else ''} vs line {line}")
out.close()
