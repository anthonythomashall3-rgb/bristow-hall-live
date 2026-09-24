"""TWO CLOCK DEFECTS FOUND IN THE PRE-1971 BRANCH (the class the route chat's 1981 lockout belonged to), and what fixing them buys.
 (1) the four-month re-arm is written m > last+4 months, so a gap that falls below the line EXACTLY four months later never re-arms:
     the Fieldhouse 0.45 branch proposed Oct 1959 (the steel strike, blocked by the vacancy at 0.05), the gap fell to 0.22 in Feb 1960 —
     exactly four months later — and the branch stayed disarmed through the whole 1960 recession. Written m >= last+4 months it re-arms and
     proposes on March 1960's reading.
 (2) the Fieldhouse gap is compared without rounding, so August 1953's 0.25 misses the 0.25 line on float.
Both are clocks, not lines. Record both ways, both vintages."""
from mini import *
from legu_min import s_cur, spl
exec(open('fast38.py').read().split("P(\"Sahm first prints 2024")[0].replace("out=open('fast38.out','w')","out=open('speed61.out','w')"))
def leg_gap_mx2(gap,line,pub_day=10,rearm='window',boundary='ge',rnd=9):
    c=[]; armed=True; last=None
    for m,v in gap.round(rnd).items():
        if armed and v>=line: c.append((pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=pub_day-1),m)); armed=False; last=m
        elif not armed:
            if rearm=='zero' and v<=0: armed=True
            elif rearm=='window' and v<line and ((m>=last+pd.DateOffset(months=4)) if boundary=='ge' else (m>last+pd.DateOffset(months=4))): armed=True
    return c
P("Aug 1953 Fieldhouse gap raw:",repr(gm['1953-08']),"-> rounded to 9 dp:",round(gm['1953-08'],9),"| line 0.25")
P("Feb 1960 gap",round(gm['1960-02'],2),"is exactly four months after the Oct 1959 proposal — the boundary case")
for bd in ['gt','ge']:
    P(f"\nboundary '{bd}': FH 0.45 proposals {[(p.strftime('%Y-%m-%d'),dd.strftime('%Y-%m')) for p,dd in leg_gap_mx2(gm,0.45,boundary=bd) if dd<pd.Timestamp('1971-01-01')]}")
    P(f"boundary '{bd}': FH 0.25 proposals {[(p.strftime('%Y-%m-%d'),dd.strftime('%Y-%m')) for p,dd in leg_gap_mx2(gm,0.25,boundary=bd) if dd<pd.Timestamp('1971-01-01')]}")
def inw(dd): return any(p-pd.DateOffset(months=6)<=dd<=t for p,t in zip(PK,TR))
def wmax_m(ser,dd,back=6,fwd=4): seg=ser[(ser.index>=dd-pd.DateOffset(months=back))&(ser.index<=dd+pd.DateOffset(months=fwd))]; return (round(float(seg.max()),2),seg.idxmax().strftime('%Y-%m')) if len(seg) else (float('nan'),'')
for bd in ['gt','ge']:
    F45=[x for x in leg_gap_mx2(gm,0.45,boundary=bd) if x[1]<pd.Timestamp('1971-01-01')]; F25=[x for x in leg_gap_mx2(gm,0.25,boundary=bd) if x[1]<pd.Timestamp('1971-01-01')]
    P(f"\n   boundary '{bd}' quiet proposals: 0.45 {[(dd.strftime('%Y-%m'),wmax_m(vr,dd),wmax_m(P1x,dd)) for p,dd in F45 if not inw(dd)]}")
    P(f"   boundary '{bd}' quiet proposals: 0.25 {[(dd.strftime('%Y-%m'),wmax_m(M35,dd)) for p,dd in F25 if not inw(dd)]}")
for vint,s in [('CURRENT FILE',s_cur),('FIRST PRINTS',spl)]:
    P(f"\n==== {vint} ====")
    X=hub_actual(0.50,vr,0.36)
    for bd in ['gt','ge']:
        F45=[x for x in leg_gap_mx2(gm,0.45,boundary=bd) if x[1]<pd.Timestamp('1971-01-01')]; F25=[x for x in leg_gap_mx2(gm,0.25,boundary=bd) if x[1]<pd.Timestamp('1971-01-01')]
        U1=confirm_w(leg_gapx(s,0.45,rearm='zero')+F45,[VJ36,Ppx],'month'); L=confirm_w(leg_gapx(s,0.25,rearm='window')+F25,[H35],'month')
        r=run3(f"v2.5, four-month re-arm boundary '{bd}' (ge = the window has closed AT four months), gap rounded",{'U':U1,'L':L,'X':X})
        P("      peak date errors",[r['errs_p'].get(i) for i in range(13)])
out.close()
