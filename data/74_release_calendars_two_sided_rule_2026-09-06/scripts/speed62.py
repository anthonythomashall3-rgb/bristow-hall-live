"""THE 1960 HAIR, priced. The Fieldhouse 0.45 branch proposes March 1960 once the four-month re-arm boundary is written 'at four months'
rather than 'after four months'; its confirmation then needs the vacancy in Sep 1959-Jul 1960, whose maximum is 0.35977 — SHORT OF THE
0.36 LINE BY TWO TEN-THOUSANDTHS, on a series that before Dec 2000 is a reconstruction. Priced: the vacancy at 0.35, which is inside the
clean band already established (>=0.30 clears Jul 2003's 0.28; the causal safe pick is 0.42)."""
from mini import *
from legu_min import s_cur, spl
exec(open('speed61.py').read().split("for vint,s in [('CURRENT FILE',s_cur),('FIRST PRINTS',spl)]:")[0].replace("out=open('speed61.out','w')","out=open('speed62.out','w')"))
def quiet(idx):
    q=pd.Series(True,index=idx)
    for p,t in zip(PK,TR): q[(idx>=p-pd.DateOffset(months=9))&(idx<=t+pd.DateOffset(months=18))]=False
    return q
def hits(o,line): o=o.dropna(); return (o>=line).reindex(pd.date_range('1949-01-01','2026-07-01',freq='MS')).fillna(False)
def win_expo(hl,back=7,fwd=5,start='1960-01-01'):
    idx=pd.date_range(start,'2026-07-01',freq='MS'); h=np.zeros(len(idx),bool)
    for x in hl: h|=x.reindex(idx).fillna(False).values.astype(bool)
    s=pd.Series(h,index=idx); q=quiet(idx)
    return ((s[::-1].rolling(fwd,min_periods=1).max()[::-1].astype(bool))|(s.rolling(back,min_periods=1).max().astype(bool)))[q].mean()*100
F45=[x for x in leg_gap_mx2(gm,0.45,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]; F25=[x for x in leg_gap_mx2(gm,0.25,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
for vl in [0.36,0.35,0.34,0.30]:
    V=dict(name=f'vac{vl}',gap=vr,line=vl,pubs=VJ36['pubs'])
    eps=[]; armed=True; idx2=pd.date_range('1949-01-01','2026-07-01',freq='MS'); q2=quiet(idx2)
    for m,v in g.items():
        if m<idx2[0]: continue
        if armed and v>=0.50:
            armed=False
            if q2.reindex([m]).fillna(False).iloc[0]: eps.append(m.strftime('%Y-%m'))
        elif not armed and v<0.50: armed=True
    eVb=win_expo([hits(vr,vl)],back=7,fwd=1,start='1949-01-01'); hz=len(eps)/(q2.sum()/12)*eVb
    P(f"\n### vacancy line {vl}: window exposure {win_expo([hits(vr,vl)]):.2f}% (V|P {win_expo([hits(vr,vl),hits(P1x,1.0)]):.2f}%); hub quiet crossings {eps}; hub hazard {hz:.3f}%/yr one in {1/(hz/100):.0f}")
    for vint,s in [('current',s_cur),('first prints',spl)]:
        X=hub_actual(0.50,vr,vl); U1=confirm_w(leg_gapx(s,0.45,rearm='zero')+F45,[V,Ppx],'month'); L=confirm_w(leg_gapx(s,0.25,rearm='window')+F25,[H35],'month')
        r=run3(f"   vacancy {vl}, {vint}",{'U':U1,'L':L,'X':X}); P("      date errors",[r['errs_p'].get(i) for i in range(13)])
    qf=[(p,dd) for p,dd in F45 if not any(pp-pd.DateOffset(months=6)<=dd<=tt for pp,tt in zip(PK,TR))]
    P(f"   pre-1971 quiet 0.45 proposals and the vacancy maximum in their windows: {[(dd.strftime('%Y-%m'),round(float(vr[(vr.index>=dd-pd.DateOffset(months=6))&(vr.index<=dd+pd.DateOffset(months=4))].max()),3)) for p,dd in qf]} — line {vl}")
out.close()
