"""The low branch's line: 0.25 (up three tenths in one-decimal data) against 0.35 (up four tenths); same-month and real-time pair; quiet proposals and their pair maxima."""
from mini import *
from legu_min import s_cur, spl
exec(open('fast26.py').read().split("L25=confirm_w(FH25,[Hp3rt],'month')")[0].replace("out=open('fast26.out','w')","out=open('fast27.out','w')"))
for vint,s in [('CURRENT FILE',s_cur),('FIRST PRINTS',spl)]:
    P(f"\n==== {vint} ====")
    for ll in [0.25,0.35]:
        ql=[(p,dd) for p,dd in leg_gapx(s,ll,rearm='window') if not inw(dd)]
        P(f"   low line {ll}: quiet proposals {len(ql)}: {[dd.strftime('%Y-%m') for p,dd in ql]}")
        P(f"      same-month pair maxima {sorted([wmax_m(PAIR3,dd) for p,dd in ql],reverse=True)[:4]} | real-time {sorted([wmax_m(MX3,dd) for p,dd in ql],reverse=True)[:4]}")
        for lab_,Vc,sl in [('a-priori',V36,0.50),('corner',V30,0.43)]:
            X=hub(sl,vr,Vc['line']); U1=confirm_w(leg_gapx(s,0.45,rearm='zero')+FHz,[Vc],'month')
            run3(f"low line {ll}, same-month pair, {lab_}",{'U':U1,'L':confirm_w(leg_gapx(s,ll,rearm='window'),[Hp3],'month'),'X':X})
            run3(f"low line {ll}, real-time pair, {lab_}",{'U':U1,'L':confirm_w(leg_gapx(s,ll,rearm='window'),[Hp3rt],'month'),'X':X})
FH35=[x for x in leg_gap_mx(gm,0.35,rearm='window') if x[1]<pd.Timestamp('1971-01-01')]
P("\nFieldhouse era, low line 0.35: proposals",[dd.strftime('%Y-%m') for p,dd in FH35],"| quiet maxima same-month",[(dd.strftime('%Y-%m'),wmax_m(PAIR3,dd)) for p,dd in FH35 if not inw(dd) and wmax_m(PAIR3,dd)[0]>=0.3],"| rt",[(dd.strftime('%Y-%m'),wmax_m(MX3,dd)) for p,dd in FH35 if not inw(dd) and wmax_m(MX3,dd)[0]>=0.3])
out.close()
