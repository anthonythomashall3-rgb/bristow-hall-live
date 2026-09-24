from mini import *
from hub import leg_X2
from legu_min import s_cur, spl
exec(open('fast8.py').read().split("X43=[(p,dd,'hub')")[0].replace("out=open('fast8.out','w')","out=open('fast11.out','w')"))
sys.path.insert(0,W+'/lab/slack'); from objects import load
fh=load()['IUR (FH)'].dropna(); gm=(fh-fh.rolling(12,min_periods=12).min().shift(1)).dropna()
def leg_gap_m(gap,line,rearm=0.0,pub_day=10):
    c=[]; armed=True
    for m,v in gap.items():
        if armed and v>=line: c.append((pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=pub_day-1),pd.Timestamp(m.year,m.month,1))); armed=False
        elif not armed and v<=rearm: armed=True
    return c
V36=dict(name='vacancy36',gap=vr,line=0.36,pub_day=30)
for vint,s,Bx in [('CURRENT FILE',s_cur,BR),('FIRST PRINTS',spl,BRs)]:
    gp=gapof(s); FH45=[x for x in leg_gap_m(gm,0.45) if x[1]<pd.Timestamp('1971-01-01')]
    P(f"\n==== {vint} ====")
    for lab_,Vc,sl in [('A-PRIORI LINES (vacancy .36, Sahm .50)',V36,0.50),('CONSTRUCTION-GRADE LINES (vacancy .30, Sahm .43)',V30,0.43)]:
        U45=confirm(leg_gap(gp,0.45)+FH45,[Vc,Hp,Pp]); UL=confirm(leg_gap(gp,0.25),[Hp]); BRL=confirm(leg_br(Bx),[Hp])
        X=[(p,dd,'hub') for p,dd in leg_X2(sahm_line=sl,vac_line=Vc['line'])]
        run(f"FAST FORM, {lab_}",{'U':U45,'L':UL,'R':BRL,'X':X})
out.close()
