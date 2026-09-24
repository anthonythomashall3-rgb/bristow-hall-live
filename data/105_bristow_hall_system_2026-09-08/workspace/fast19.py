"""Initial claims (published 5 days after the week, a week before the insured rate) as a supply-side reading."""
from mini import *
from legu_min import s_cur, spl
exec(open('fast17.py').read().split("for vint,s in [('CURRENT FILE',s_cur),('FIRST PRINTS',spl)]:")[0].replace("out=open('fast17.out','w')","out=open('fast19.out','w')"))
n=o['nat67']; rt=o['nat_sa_rt']
ic_rt=rt['ic_sa_rt'].dropna(); ic_cur=n['ic_sa'].dropna()
N45=pd.read_csv(W.replace('24_bristow_rule_lab/workspace','45_dol_first_prints_2026-09/national_first_prints.csv'),parse_dates=['release_date','ic_week_ended','iu_week_ended'])
P("national first prints columns:",list(N45.columns))
icfp_col=[c for c in N45.columns if c.lower() in ('icsa','ic_sa','icsa_adv','initial_sa')]
def leg_ic(series,pct,look=52,pub=5,rearm='window'):
    m4=series.rolling(4).mean(); rise=(m4/m4.rolling(look,min_periods=look).min().shift(1)-1)*100; rise=rise.dropna()
    c=[]; armed=True; last=None
    for t,v in rise.items():
        if armed and v>=pct: c.append((t+pd.Timedelta(days=pub),pd.Timestamp(t.year,t.month,1))); armed=False; last=t
        elif not armed:
            if rearm=='zero' and v<=0: armed=True
            elif rearm=='window' and v<pct and t>last+pd.DateOffset(months=4): armed=True
    return c
def inw(dd): return any(p-pd.DateOffset(months=6)<=dd<=t for p,t in zip(PK,TR))
def wmax(ser,p,back=6,fwd=4): seg=ser[(ser.index>=p-pd.DateOffset(months=back))&(ser.index<=p+pd.DateOffset(months=fwd))]; return seg.max() if len(seg) else float('nan')
for nm,ser in [('real-time SA (lab factors, 1969 on)',ic_rt),('current SA file',ic_cur)]:
    P(f"\n-- initial claims 4-wk avg over 52-wk low, {nm} --")
    for pct in [20,30]:
        for rr in ['zero','window']:
            L=leg_ic(ser,pct,rearm=rr); q=[(p,dd) for p,dd in L if not inw(dd)]
            P(f"  +{pct}% re-arm {rr}: proposals {len(L)}, quiet {len(q)}; quiet housing max {max([wmax(PAIRX,p) for p,_ in q]+[0]):.2f}, quiet vacancy36 hits {sum(1 for p,_ in q if wmax(vr,p)>=0.36)}, quiet hours>=1 {sum(1 for p,_ in q if wmax(P1,p)>=1.0)}; first in recession windows {[ (lambda c: c[0][0].strftime('%Y-%m-%d') if c else '-')([x for x in L if pk-pd.DateOffset(months=6)<=x[1]<=tr]) for pk,tr in zip(PK[5:],TR[5:])]}")
FHz=[x for x in leg_gap_mx(gm,0.45,rearm='window') if x[1]<pd.Timestamp('1971-01-01')]
for vint,s in [('CURRENT FILE (IC real-time SA)',s_cur)]:
    P(f"\n==== {vint} ====")
    U=confirm(leg_gapx(s,0.45,rearm='zero')+FHz,[V36,HpX,Pp]); L=confirm(leg_gapx(s,0.25,rearm='window'),[HpX]); X=hub(0.50,vr,0.36)
    run2("v2 (reference)",{'U':U,'L':L,'X':X})
    for pct in [20,30]:
        run2(f"v2 + IC +{pct}% (window re-arm) {{housing}}",{'U':U,'L':L,'I':confirm(leg_ic(ic_rt,pct),[HpX]),'X':X})
        run2(f"v2 + IC +{pct}% (window re-arm) {{vacancy36|housing|hours}}",{'U':U,'L':L,'I':confirm(leg_ic(ic_rt,pct),[V36,HpX,Pp]),'X':X})
out.close()
