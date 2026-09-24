"""v2.5's slow turns, object by object: 1960 (153 days), 1953 (71), 1981 (63), 2007 first prints (80). What each object read in the window,
and whether any object already in the rule could have carried the call sooner."""
from mini import *
from legu_min import s_cur, spl
exec(open('fast38.py').read().split("P(\"Sahm first prints 2024")[0].replace("out=open('fast38.out','w')","out=open('speed60.out','w')"))
FH45=[x for x in leg_gap_mx(gm,0.45,rearm='window') if x[1]<pd.Timestamp('1971-01-01')]
FH25=[x for x in leg_gap_mx(gm,0.25,rearm='window') if x[1]<pd.Timestamp('1971-01-01')]
P("Fieldhouse insured-rate proposals before 1971 — 0.45 branch:",[(p.strftime('%Y-%m-%d'),dd.strftime('%Y-%m')) for p,dd in FH45])
P("                                              — 0.25 branch:",[(p.strftime('%Y-%m-%d'),dd.strftime('%Y-%m')) for p,dd in FH25])
for nm,(a,b) in [('1953',('1953-01','1954-06')),('1957',('1957-02','1958-06')),('1960',('1959-08','1961-03')),('1969',('1969-06','1970-12'))]:
    P(f"\n--- {nm} window {a}..{b} ---")
    P(f"   Fieldhouse insured gap: {[(m.strftime('%Y-%m'),round(v,2)) for m,v in gm[a:b].items()]}")
    P(f"   vacancy (2,6) gap:      {[(m.strftime('%Y-%m'),round(v,2)) for m,v in vr[a:b].items()]}")
    P(f"   Sahm first prints:      {[(m.strftime('%Y-%m'),round(v,2)) for m,v in g[a:b].items()]}")
    P(f"   housing pair (4 tenths, real-time): {[(m.strftime('%Y-%m'),round(v,2)) for m,v in M35[a:b].items()] if len(M35[a:b]) else 'starts vintages begin Jul 1960'}")
    P(f"   hours pair:             {[(m.strftime('%Y-%m'),round(v,2)) for m,v in P1x[a:b].items()] if len(P1x[a:b]) else 'AWHMAN vintages begin 1961'}")
P("\n--- 2007 on FIRST PRINTS (the +80) ---")
gs=(spl-spl.rolling(52,min_periods=52).min().shift(1)).dropna()
P(f"   advance insured-rate gap weekly, Oct 2007-Apr 2008: {[(t.strftime('%Y-%m-%d'),round(v,2)) for t,v in gs['2007-10':'2008-04'].items()][::2]}")
P(f"   housing pair (real-time): {[(m.strftime('%Y-%m'),round(v,2)) for m,v in M35['2007-08':'2008-04'].items()]}")
P(f"   Sahm first prints: {[(m.strftime('%Y-%m'),round(v,2)) for m,v in g['2007-08':'2008-05'].items()]}")
P(f"   vacancy: {[(m.strftime('%Y-%m'),round(v,2)) for m,v in vr['2007-06':'2008-04'].items()]}")
out.close()
