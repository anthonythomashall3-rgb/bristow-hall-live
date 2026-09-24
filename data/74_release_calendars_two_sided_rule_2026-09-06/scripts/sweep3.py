"""Fine grid on the starts line between 33 and 29, with vacancy 0.35; margins and hazard for the survivors."""
from mini import *
from legu_min import s_cur, spl
exec(open('sweep2.py').read().split("for vac in [0.36,0.35]:")[0].replace("out=open('sweep2.out','w')","out=open('sweep3.out','w')"))
def quiet(idx):
    q=pd.Series(True,index=idx)
    for p_,t in zip(PK,TR): q[(idx>=p_-pd.DateOffset(months=9))&(idx<=t+pd.DateOffset(months=18))]=False
    return q
def hits(o,line): o=o.dropna(); return (o>=line).reindex(pd.date_range('1949-01-01','2026-07-01',freq='MS')).fillna(False)
def win_expo(hl,back=7,fwd=5,start='1960-01-01'):
    idx=pd.date_range(start,'2026-07-01',freq='MS'); h=np.zeros(len(idx),bool)
    for x in hl: h|=x.reindex(idx).fillna(False).values.astype(bool)
    s=pd.Series(h,index=idx); q=quiet(idx)
    return ((s[::-1].rolling(fwd,min_periods=1).max()[::-1].astype(bool))|(s.rolling(back,min_periods=1).max().astype(bool)))[q].mean()*100
def inw(dd): return any(p_-pd.DateOffset(months=6)<=dd<=t for p_,t in zip(PK,TR))
def wmax(ser,dd): seg=ser[(ser.index>=dd-pd.DateOffset(months=6))&(ser.index<=dd+pd.DateOffset(months=4))]; return round(float(seg.max()),3) if len(seg) else float('nan')
QL=sorted({dd for p_,dd in leg_gapx(s_cur,0.25,rearm='window') if not inw(dd)}|{dd for p_,dd in leg_gapx(spl,0.25,rearm='window') if not inw(dd)}|{dd for p_,dd in leg_gap_mx2(gm,0.25,boundary='ge') if dd<pd.Timestamp('1971-01-01') and not inw(dd)})
for st in [35,34,33,32,31,30,29]:
    ok,lp=full(f'vacancy 0.35, starts {st}',{**BASE,'vac':0.35,'starts':st})
    _,MX=mkpair(st,4); mm=sorted([(wmax(MX,dd),dd.strftime('%Y-%m')) for dd in QL if not np.isnan(wmax(MX,dd))],reverse=True)[:3]
    e=win_expo([hits(MX,1.0)]); P(f"     margins: highest pair reading in a quiet proposal's window {mm} -> margin {1-mm[0][0]:.3f}; quiet-month window exposure {e:.2f}%")
P("\nhub and 0.45-branch exposure at vacancy 0.35 vs 0.36:")
for vl in [0.36,0.35]:
    P(f"   vacancy {vl}: confirmer window exposure V {win_expo([hits(vr,vl)]):.2f}%, V|hours {win_expo([hits(vr,vl),hits(P1x,1.0)]):.2f}%; hub six-back exposure {win_expo([hits(vr,vl)],back=7,fwd=1,start='1949-01-01'):.2f}% -> hub hazard {2/((quiet(pd.date_range('1949-01-01','2026-07-01',freq='MS')).sum())/12)*win_expo([hits(vr,vl)],back=7,fwd=1,start='1949-01-01'):.3f}%/yr, one in {1/(2/((quiet(pd.date_range('1949-01-01','2026-07-01',freq='MS')).sum())/12)*win_expo([hits(vr,vl)],back=7,fwd=1,start='1949-01-01')/100):.0f}")
out.close()
