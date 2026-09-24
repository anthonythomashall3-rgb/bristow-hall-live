"""v2.4 RECORD SCRIPT — 'the safest thing for speed' (Anthony, 6 Sep 2026). v2.3 with the two changes that buy speed at the least hazard:
  the hub's Sahm line at 0.43 (buys 2024: 94 -> 66 days; hub hazard 0.17 -> 0.35%/yr, one in 575 -> one in 288) with the vacancy kept at 0.36;
  the hours x nondurable pair restored as a second confirmer of the 0.45 branch (buys 1980: 30 -> -7; zero quiet proposals on that branch, so
  the observed hazard is unchanged and only the ceiling moves, 0.47 -> 0.60%/yr).
  Refused as dearer per day: vacancy 0.30 (1960 21 d, 2007 first prints 13 d; hub hazard x1.37, U45 ceiling x1.5, 1967 vacancy margin 0.12 -> 0.06).
Everything else as v2.3: insured rate 0.45 (new-low re-arm) and 0.25 (window re-arm); starts 35 x rate four tenths, each half at its own release;
actual ALFRED release dates; Fieldhouse monthly rate before 1971 on both branches; windows on data months; exact arithmetic; closers K H S J."""
from mini import *
from legu_min import s_cur, spl
from scipy import stats
exec(open('fast36.py').read().split("for sl in [0.50,0.43]:\n    for vl in [0.36,0.30]:")[0].replace("out=open('fast36.out','w')","out=open('fast37.out','w')"))
RES={}
for vint,s in [('CURRENT FILE',s_cur),('FIRST PRINTS',spl)]:
    P(f"\n==== {vint} ====")
    LP=leg_gapx(s,0.25,rearm='window')+FH25; L=confirm_w(LP,[H35],'month'); X=hub_actual(0.43,vr,0.36); U1=confirm_w(leg_gapx(s,0.45,rearm='zero')+FHz,[VJ36,Ppx],'month')
    r=run3("v2.4: U45{vacancy .36 | hours pair} + U25{starts 35 x rate 4 tenths, real-time} + hub{Sahm .43, vacancy .36}; K H S J",{'U':U1,'L':L,'X':X}); RES[vint]=r
    P("      peak date errors",[r['errs_p'].get(i) for i in range(13)],"trough date errors",[r['errs_t'].get(i) for i in range(13)])
    P("      trough calls: "+" | ".join(f"{TR[i]:%Y-%m}:{[t for t in r['turns'] if t['kind']=='trough' and (t['published']-me(TR[i])).days==r['lags_t'][i]][0]['published']:%Y-%m-%d} {[t for t in r['turns'] if t['kind']=='trough' and (t['published']-me(TR[i])).days==r['lags_t'][i]][0]['leg']}" for i in range(13) if i in r['lags_t']))
    run3("   (four-series form: without the hours pair)",{'U':confirm_w(leg_gapx(s,0.45,rearm='zero')+FHz,[VJ36],'month'),'L':L,'X':X})
    ql=[(p,dd) for p,dd in leg_gapx(s,0.25,rearm='window') if not inw(dd)]; qu=[(p,dd) for p,dd in leg_gapx(s,0.45,rearm='zero') if not inw(dd)]
    P(f"   quiet proposals: U25 {len(ql)} (pair maxima {sorted([wmax_m(M35,dd) for p,dd in ql if not np.isnan(wmax_m(M35,dd)[0])],reverse=True)[:3]}); U45 {len(qu)}")
qf=[(p,dd) for p,dd in FHz if not inw(dd)]; P("   Fieldhouse era, U45 quiet proposals (vacancy, hours pair maxima):",[(dd.strftime('%Y-%m'),wmax_m(vr,dd),wmax_m(P1x,dd)) for p,dd in qf])
qf2=[(p,dd) for p,dd in FH25 if not inw(dd)]; P("   Fieldhouse era, U25 quiet proposals (pair maxima):",[(dd.strftime('%Y-%m'),wmax_m(M35,dd)) for p,dd in qf2 if not np.isnan(wmax_m(M35,dd)[0]) and wmax_m(M35,dd)[0]>=0.3])
P("   Fieldhouse era calls:",[(p.strftime('%Y-%m-%d'),dd.strftime('%Y-%m'),c) for p,dd,c in confirm_w(FH25,[H35],'month')],[(p.strftime('%Y-%m-%d'),dd.strftime('%Y-%m'),c) for p,dd,c in confirm_w(FHz,[VJ36,Ppx],'month')])
P("\nHAZARD, Paper 1's quiet set, month windows, exact arithmetic:")
eps,eVb,hz=hub_haz(0.43,0.36); P(f"   hub: Sahm 0.43 quiet crossings {eps} ({len(eps)/QY2*100:.2f}%/yr) x six-back vacancy 0.36 exposure {eVb:.2f}% = {hz:.3f}%/yr observed, one in {1/(hz/100):.0f}; at 0.50 it was 0.174 (one in 575)")
eVP,_=win_expo([hits(vr,0.36),hits(P1x,1.0)]); eV,_=win_expo([hits(vr,0.36)]); P(f"   U45 branch: 0 quiet proposals in 30.3 quiet years since 1972 -> observed 0; ceiling (rule of three 9.89%/yr) x V|P exposure {eVP:.2f}% = {9.89*eVP/100:.2f}%/yr (V alone {eV:.2f}% -> {9.89*eV/100:.2f})")
h=hits(M35,1.0); q=quiet(h.index); P(f"   U25 branch: pair fires in {int((h & q)[h.index>=pd.Timestamp('1960-01-01')].sum())} quiet months of 442 -> observed 0; ceiling 2.5-2.7%/yr (ten or eleven quiet proposals x rule-of-three exposure)")
P(f"   whole rule observed = the hub's {hz:.3f}%/yr (one in {1/(hz/100):.0f}); Sahm's margin above December 2025 (0.40) is 0.03, one tick.")
out.close()
