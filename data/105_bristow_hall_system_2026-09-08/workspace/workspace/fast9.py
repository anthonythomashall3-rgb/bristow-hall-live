"""Pre-1971: the insured-rate branches on the Fieldhouse monthly insured unemployment rate (a reconstruction, 1947-2024)."""
from mini import *
from hub import leg_X2
from legu_min import s_cur
exec(open('fast8.py').read().split("X43=[(p,dd,'hub')")[0].replace("out=open('fast8.out','w')","out=open('fast9.out','w')"))
sys.path.insert(0,W+'/lab/slack'); from objects import load
fh=load()['IUR (FH)'].dropna()
P("\nFH monthly insured rate:",fh.index.min().date(),fh.index.max().date())
gm=(fh-fh.rolling(12,min_periods=12).min().shift(1)).dropna()
def leg_gap_m(gap,line,rearm=0.0,pub_day=10):
    c=[]; armed=True
    for m,v in gap.items():
        if armed and v>=line: c.append((pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=pub_day-1),pd.Timestamp(m.year,m.month,1))); armed=False
        elif not armed and v<=rearm: armed=True
    return c
def inw(dd): return any(p-pd.DateOffset(months=6)<=dd<=t for p,t in zip(PK,TR))
for ln in [0.45,0.25]:
    L=leg_gap_m(gm,ln); L=[x for x in L if x[1]<pd.Timestamp('1971-01-01')]
    P(f"FH-IUR monthly gap >= {ln} crossings before 1971:",[(p.strftime('%Y-%m-%d'),('R' if inw(dd) else 'quiet')) for p,dd in L])
FH45=confirm([x for x in leg_gap_m(gm,0.45) if x[1]<pd.Timestamp('1971-01-01')],[V30,Hp,Pp])
FH25=confirm([x for x in leg_gap_m(gm,0.25) if x[1]<pd.Timestamp('1971-01-01')],[Hp])
P("FH45 confirmed:",[(p.strftime('%Y-%m-%d'),dd.strftime('%Y-%m'),c) for p,dd,c in FH45])
P("FH25{housing} confirmed:",[(p.strftime('%Y-%m-%d'),dd.strftime('%Y-%m'),c) for p,dd,c in FH25])
gp=gapof(s_cur); U45=confirm(leg_gap(gp,0.45),[V30,Hp,Pp]); UL=confirm(leg_gap(gp,0.25),[Hp]); BRL=confirm(leg_br(BR),[Hp])
X43=[(p,dd,'hub') for p,dd in leg_X2(sahm_line=0.43,vac_line=0.30)]
run("FAST FORM 1971 on + FH insured rate before 1971 (both branches) + hub",{'U':U45+FH45,'L':UL+FH25,'R':BRL,'X':X43})
run("FAST FORM + FH insured rate 0.45 branch only before 1971",{'U':U45+FH45,'L':UL,'R':BRL,'X':X43})
out.close()
