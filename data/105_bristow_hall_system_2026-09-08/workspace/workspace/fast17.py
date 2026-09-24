"""Fast form v2: corrected lags, window re-arm on both insured-rate legs, no breadth object. Margins re-checked."""
from mini import *
from legu_min import s_cur, spl
exec(open('fast16.py').read().split("for vint,s,Bx in [('CURRENT FILE',s_cur,BR),('FIRST PRINTS',spl,BRs)]:")[0].replace("out=open('fast16.out','w')","out=open('fast17.out','w')"))
def leg_gap_mx(gap,line,pub_day=10,rearm='window'):
    c=[]; armed=True; last=None
    for m,v in gap.items():
        if armed and v>=line: c.append((pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=pub_day-1),m)); armed=False; last=m
        elif not armed:
            if rearm=='zero' and v<=0: armed=True
            elif rearm=='window' and v<line and m>last+pd.DateOffset(months=4): armed=True
    return c
def inw(dd): return any(p-pd.DateOffset(months=6)<=dd<=t for p,t in zip(PK,TR))
def wmax(ser,p,back=6,fwd=4): seg=ser[(ser.index>=p-pd.DateOffset(months=back))&(ser.index<=p+pd.DateOffset(months=fwd))]; return seg.max() if len(seg) else float('nan')
for vint,s in [('CURRENT FILE',s_cur),('FIRST PRINTS',spl)]:
    P(f"\n==== {vint} ====")
    for lab_,Vc,sl in [('a-priori lines (vacancy .36, Sahm .50)',V36,0.50),('construction-grade (vacancy .30, Sahm .43)',V30,0.43)]:
        for rr in ['zero','window']:
            FHx=[x for x in leg_gap_mx(gm,0.45,rearm=rr) if x[1]<pd.Timestamp('1971-01-01')]
            U=confirm(leg_gapx(s,0.45,rearm=rr)+FHx,[Vc,HpX,Pp]); L=confirm(leg_gapx(s,0.25,rearm=rr),[HpX]); X=hub(sl,vr,Vc['line'])
            r=run2(f"{lab_}; re-arm {rr}: U45{{V|H|P}} + U-low{{H}} + hub",{'U':U,'L':L,'X':X})
    # margins for the window re-arm at a-priori lines
    ql=[(p,dd) for p,dd in leg_gapx(s,0.25,rearm='window') if not inw(dd)]; qu=[(p,dd) for p,dd in leg_gapx(s,0.45,rearm='window') if not inw(dd)]
    P(f"  margins, window re-arm: U-low quiet proposals {len(ql)} — housing pair max {max(wmax(PAIRX,p) for p,_ in ql):.2f}; U45 quiet proposals {len(qu)} {[dd.strftime('%Y-%m') for p,dd in qu]} — vacancy max {max([wmax(vr,p) for p,_ in qu]+[float('nan')]) if qu else float('nan'):.2f}, housing max {max([wmax(PAIRX,p) for p,_ in qu]+[0]):.2f}, hours max {max([wmax(P1,p) for p,_ in qu]+[0]):.2f}")
    P("  U-low quiet proposals with housing pair >= 0.6:",[(p.strftime('%Y-%m-%d'),round(wmax(PAIRX,p),2)) for p,dd in ql if wmax(PAIRX,p)>=0.6])
qf=[(p,dd) for p,dd in leg_gap_mx(gm,0.45) if dd<pd.Timestamp('1971-01-01') and not inw(dd)]
P("\nFH branch (window re-arm) quiet proposals before 1971:",[(dd.strftime('%Y-%m'),round(wmax(vr,p),2),round(wmax(PAIRX,p),2) if not np.isnan(wmax(PAIRX,p)) else None,round(wmax(P1,p),2) if not np.isnan(wmax(P1,p)) else None) for p,dd in qf],"(vacancy, housing, hours maxima)")
out.close()
