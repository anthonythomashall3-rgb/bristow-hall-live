"""State unemployment-rate breadth (share of states whose own Sahm gap >= 0.5) as a hub proposer, confirmed by the vacancy."""
from mini import *
from hub import leg_X2
from legu_min import s_cur, spl
exec(open('fast8.py').read().split("X43=[(p,dd,'hub')")[0].replace("out=open('fast8.out','w')","out=open('fast12.out','w')"))
sys.path.insert(0,W+'/lab/slack')
from objects import state_ur, sahm
SU=state_ur()
def breadth_ur(df,state_line=0.5):
    G=df.apply(lambda c: sahm(c.dropna(),3,12)); return ((G>=state_line).sum(axis=1)/G.notna().sum(axis=1)*100).dropna()
BU=breadth_ur(SU)
fpd=pd.read_csv(W+'/lab/cps/21_vintage_realtime/monthly/bls_laus_first_prints/state_ur_first_prints_refmonth_fixed.csv'); fpd['obs_period']=pd.to_datetime(fpd['obs_period'])
FPU=fpd.pivot_table(index='obs_period',columns='geo_code',values='value',aggfunc='first').sort_index(); FPU=FPU[[c for c in FPU.columns if c!='PR']]
BUF=breadth_ur(FPU); BUs=pd.concat([BU[BU.index<BUF.index.min()],BUF]).sort_index()
P("state UR breadth: current",BU.index.min().date(),BU.index.max().date(),"| first prints",BUF.index.min().date(),BUF.index.max().date())
P("current  2024-07..2026-06:",[int(round(v)) for v in BU['2024-07':'2026-06']])
P("first pr 2024-07..2026-06:",[int(round(v)) for v in BUF['2024-07':'2026-06']])
P("current  1985-06..1986-12:",[int(round(v)) for v in BU['1985-06':'1986-12']],"  vacancy(2,6) 1985-06..1986-12:",[round(v,2) for v in vr['1985-06':'1986-12']])
def leg_bu(Bx,line,pub_day=20):
    c=[]; armed=True
    for m,v in Bx.items():
        if armed and v>=line: c.append((pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=pub_day-1),pd.Timestamp(m.year,m.month,1))); armed=False
        elif not armed and v<line*0.5: armed=True     # re-arm when the breadth has fallen to half its line
    return c
def inw(dd): return any(p-pd.DateOffset(months=6)<=dd<=t for p,t in zip(PK,TR))
for vint,Bx in [('current',BU),('first prints',BUs)]:
    for line in [30,35,40]:
        L=leg_bu(Bx,line); qs=[(p,dd) for p,dd in L if not inw(dd)]
        P(f"  {vint} breadth>={line}: proposals {[(dd.strftime('%Y-%m')) for p,dd in L]}; quiet {[(dd.strftime('%Y-%m'), round(float(vr[(vr.index>=p-pd.DateOffset(months=6))&(vr.index<=p+pd.DateOffset(months=4))].max()),2)) for p,dd in qs]} (vacancy max in window)")
V36=dict(name='vacancy36',gap=vr,line=0.36,pub_day=30)
sys.path.insert(0,W+'/lab/slack'); from objects import load
fh=load()['IUR (FH)'].dropna(); gm=(fh-fh.rolling(12,min_periods=12).min().shift(1)).dropna()
def leg_gap_m(gap,line,rearm=0.0,pub_day=10):
    c=[]; armed=True
    for m,v in gap.items():
        if armed and v>=line: c.append((pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=pub_day-1),pd.Timestamp(m.year,m.month,1))); armed=False
        elif not armed and v<=rearm: armed=True
    return c
FH45=[x for x in leg_gap_m(gm,0.45) if x[1]<pd.Timestamp('1971-01-01')]
for vint,s,Bx,BUx in [('CURRENT FILE',s_cur,BR,BU),('FIRST PRINTS',spl,BRs,BUs)]:
    gp=gapof(s)
    for Vc,sl,lab_ in [(V36,0.50,'a-priori'),(V30,0.43,'construction-grade')]:
        U45=confirm(leg_gap(gp,0.45)+FH45,[Vc,Hp,Pp]); UL=confirm(leg_gap(gp,0.25),[Hp]); BRL=confirm(leg_br(Bx),[Hp]); X=[(p,dd,'hub') for p,dd in leg_X2(sahm_line=sl,vac_line=Vc['line'])]
        for line in [30,35,40]:
            SB=confirm(leg_bu(BUx,line),[Vc])
            run(f"{vint}, {lab_} lines: fast form + state-UR breadth>={line} {{vacancy}}",{'U':U45,'L':UL,'R':BRL,'S':SB,'X':X})
out.close()
