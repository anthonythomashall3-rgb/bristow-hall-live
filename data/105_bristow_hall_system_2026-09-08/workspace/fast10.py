"""Margins of the fast form: every quiet proposal of every branch, and the demand-side readings that blocked it."""
from mini import *
from hub import leg_X2
from legu_min import s_cur, spl
exec(open('fast8.py').read().split("X43=[(p,dd,'hub')")[0].replace("out=open('fast8.out','w')","out=open('fast10.out','w')"))
sys.path.insert(0,W+'/lab/slack'); from objects import load
fh=load()['IUR (FH)'].dropna(); gm=(fh-fh.rolling(12,min_periods=12).min().shift(1)).dropna()
def leg_gap_m(gap,line,rearm=0.0,pub_day=10):
    c=[]; armed=True
    for m,v in gap.items():
        if armed and v>=line: c.append((pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=pub_day-1),pd.Timestamp(m.year,m.month,1))); armed=False
        elif not armed and v<=rearm: armed=True
    return c
def inw(dd): return any(p-pd.DateOffset(months=6)<=dd<=t for p,t in zip(PK,TR))
def wmax(ser,p,back=6,fwd=4):
    seg=ser[(ser.index>=p-pd.DateOffset(months=back))&(ser.index<=p+pd.DateOffset(months=fwd))]; return seg.max() if len(seg) else float('nan')
P("\n== MARGINS: quiet proposals of each branch and the demand-side maxima inside the (6 back, 4 forward) window ==")
for vint,s,Bx in [('current file',s_cur,BR),('first prints',spl,BRs)]:
    gp=gapof(s)
    P(f"\n-- {vint} --")
    for nm,calls,confs in [("IUR >= 0.45 {vacancy .30 | housing | hours}",leg_gap(gp,0.45),['V','H','P']),("IUR >= 0.25 {housing}",leg_gap(gp,0.25),['H']),("breadth >= 50 {housing}",leg_br(Bx),['H'])]:
        qs=[(p,dd) for p,dd in calls if not inw(dd)]
        P(f"  {nm}: {len(calls)} proposals, {len(qs)} quiet")
        for p,dd in qs:
            P(f"     {p:%Y-%m-%d}  vacancy {wmax(vr,p):.2f} (line .30)  housing pair {wmax(PAIR,p):.2f} (line 1.0)  hours pair {wmax(P1,p):.2f} (line 1.0)")
qs=[(p,dd) for p,dd in leg_gap_m(gm,0.45) if dd<pd.Timestamp('1971-01-01') and not inw(dd)]
P("\n-- Fieldhouse insured rate, monthly, before 1971: IUR >= 0.45 {vacancy | housing | hours} quiet proposals --")
for p,dd in qs: P(f"     {p:%Y-%m-%d}  vacancy {wmax(vr,p):.2f}  housing pair {wmax(PAIR,p):.2f}  hours pair {wmax(P1,p):.2f}")
P("\n-- the hub: Sahm first prints >= 0.43 quiet crossings and the vacancy in the six months back --")
armed=True
for m,v in g.items():
    if m<pd.Timestamp('1949-01-01'): continue
    if armed and v>=0.43:
        armed=False
        if not inw(m): w=vr[(vr.index>=m-pd.DateOffset(months=6))&(vr.index<=m)]; P(f"     {m:%Y-%m} Sahm {v:.2f} vacancy max {w.max():.2f} (line .30)")
    elif not armed and v<0.43: armed=True
P("   Sahm first prints 0.35-0.42 in quiet months with the vacancy >= .30 (the readings that set the hub's line):")
for m,v in g.items():
    if 0.35<=v<0.43 and not inw(m) and m>=pd.Timestamp('1968-01-01') and not any(p-pd.DateOffset(months=6)<=m<=t+pd.DateOffset(months=12) for p,t in zip(PK,TR)):
        w=vr[(vr.index>=m-pd.DateOffset(months=6))&(vr.index<=m)]
        if w.max()>=0.30: P(f"     {m:%Y-%m} Sahm {v:.2f} vacancy max {w.max():.2f}")
out.close()
