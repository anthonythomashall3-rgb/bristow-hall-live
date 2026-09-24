"""Final v2 with the pair requiring BOTH halves present (no fire on a missing housing print); full record, both vintages, both line sets."""
from mini import *
from legu_min import s_cur, spl
exec(open('fast17.py').read().split("for vint,s in [('CURRENT FILE',s_cur),('FIRST PRINTS',spl)]:")[0].replace("out=open('fast17.out','w')","out=open('fast20.out','w')"))
PAIRX2=pd.concat([hous_half,rate_half],axis=1).min(axis=1,skipna=False).dropna(); HpX2=dict(name='housing35x',gap=PAIRX2,line=1.0,pub_day=18)
P("months where skipna changed the pair's firing:",[m.strftime('%Y-%m') for m in PAIRX.index if (PAIRX[m]>=1.0)!=(PAIRX2.get(m,0)>=1.0)])
FHz=[x for x in leg_gap_mx(gm,0.45,rearm='window') if x[1]<pd.Timestamp('1971-01-01')]
def inw(dd): return any(p-pd.DateOffset(months=6)<=dd<=t for p,t in zip(PK,TR))
def wmax(ser,p,back=6,fwd=4): seg=ser[(ser.index>=p-pd.DateOffset(months=back))&(ser.index<=p+pd.DateOffset(months=fwd))]; return seg.max() if len(seg) else float('nan')
for vint,s in [('CURRENT FILE',s_cur),('FIRST PRINTS',spl)]:
    P(f"\n==== {vint} ====")
    for lab_,Vc,sl in [('a-priori lines (vacancy .36, Sahm .50)',V36,0.50),('construction-grade (vacancy .30, Sahm .43)',V30,0.43)]:
        U=confirm(leg_gapx(s,0.45,rearm='zero')+FHz,[Vc,HpX2,Pp]); L=confirm(leg_gapx(s,0.25,rearm='window'),[HpX2]); X=hub(sl,vr,Vc['line'])
        r=run2(f"FAST FORM v2, {lab_}",{'U':U,'L':L,'X':X})
        ep=[r['errs_p'].get(i) for i in range(13)]; P(f"   peak date errors {ep}; trough date errors {[r['errs_t'].get(i) for i in range(13)]}")
    ql=[(p,dd) for p,dd in leg_gapx(s,0.25,rearm='window') if not inw(dd)]
    P(f"   U-low (0.25, window re-arm) quiet proposals: {len(ql)}; housing pair maxima >=0.5: {[(p.strftime('%Y-%m-%d'),round(wmax(PAIRX2,p),2)) for p,dd in ql if wmax(PAIRX2,p)>=0.5]}")
    qu=[(p,dd) for p,dd in leg_gapx(s,0.45,rearm='zero') if not inw(dd)]; P(f"   U45 (0.45, zero re-arm) quiet proposals: {len(qu)}")
qf=[(p,dd) for p,dd in FHz if not inw(dd)]; P("\nFH45 (window re-arm) quiet proposals:",[(dd.strftime('%Y-%m'),round(wmax(vr,p),2),round(wmax(P1,p),2) if not np.isnan(wmax(P1,p)) else None) for p,dd in qf],"(vacancy, hours)")
out.close()
