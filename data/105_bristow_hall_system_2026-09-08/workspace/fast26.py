"""REAL-TIME PAIR. The housing x rate pair was evaluated on same-month halves, published with the housing release (18th of m+1).
In real time each half is read at its own release: on the unemployment-rate release for month m (~5th of m+1) the latest starts are m-1.
So the pair also fires at that release when min(rate[m], housing[m-1]) >= 1. No new data, no new line: a clock correction of the same
class as the 12-day claims lag. Re-run v2.2-lite with the pair on its real-time clock; margins, 1966 test, exposure."""
from mini import *
from legu_min import s_cur, spl
exec(open('fast24.py').read().split("RES={}")[0].replace("out=open('fast24.out','w')","out=open('fast26.out','w')"))
def rt_pair(rate_h, hous_h):
    idx=rate_h.index.intersection(hous_h.index); gap={}; pubs={}; both={}
    for m in idx:
        hm1=hous_h.get(m-pd.DateOffset(months=1),np.nan); c1=min(rate_h[m],hm1) if not np.isnan(hm1) else np.nan; c2=min(rate_h[m],hous_h[m])
        d_ur=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4)); d_h=pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=17)
        if not np.isnan(c1) and c1>=1.0: gap[m]=c1; pubs[m]=d_ur
        else: gap[m]=c2; pubs[m]=d_h
        both[m]=np.nanmax([c1,c2])
    return pd.Series(gap).dropna(), pd.Series(pubs), pd.Series(both).dropna()
def pubof(cf,t):
    if 'pubs' in cf: return cf['pubs'][t]
    return (t+pd.Timedelta(days=cf['pub_lag_days'])) if 'pub_lag_days' in cf else (pd.Timestamp(t.year,t.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=cf['pub_day']-1))
G3,PB3,MX3=rt_pair(rate3,hous_half); Hp3rt=dict(name='housing35x_r3_rt',gap=G3,line=1.0,pubs=PB3)
G2,PB2,MX2=rt_pair(rate_half,hous_half)
P("real-time pair (3 tenths): months firing at the UR release (housing m-1) that do NOT fire same-month:",[m.strftime('%Y-%m') for m in G3.index if G3[m]>=1.0 and PAIR3.get(m,0)<1.0])
P("real-time pair (3 tenths): months at line:",[m.strftime('%Y-%m') for m,v in G3.items() if v>=1.0])
P("real-time pair (2 tenths): extra firing months vs same-month:",[m.strftime('%Y-%m') for m in G2.index if G2[m]>=1.0 and PAIRX2.get(m,0)<1.0])
def inw(dd): return any(p-pd.DateOffset(months=6)<=dd<=t for p,t in zip(PK,TR))
def wmax_m(ser,dd,back=6,fwd=4): seg=ser[(ser.index>=dd-pd.DateOffset(months=back))&(ser.index<=dd+pd.DateOffset(months=fwd))]; return (round(float(seg.max()),2),seg.idxmax().strftime('%Y-%m')) if len(seg) else (float('nan'),'')
L25=confirm_w(FH25,[Hp3rt],'month'); P("Fieldhouse era, U25 branch with the real-time pair: calls",[(p.strftime('%Y-%m-%d'),dd.strftime('%Y-%m'),c) for p,dd,c in L25]," | quiet maxima:",[(dd.strftime('%Y-%m'),wmax_m(MX3,dd)) for p,dd in FH25 if not inw(dd) and wmax_m(MX3,dd)[0]>=0.5])
for vint,s in [('CURRENT FILE',s_cur),('FIRST PRINTS',spl)]:
    P(f"\n==== {vint} ====")
    for lab_,Vc,sl in [('a-priori (vac .36, Sahm .50)',V36,0.50),('construction-grade (vac .30, Sahm .43)',V30,0.43)]:
        X=hub(sl,vr,Vc['line']); U1=confirm_w(leg_gapx(s,0.45,rearm='zero')+FHz,[Vc],'month'); U2=confirm_w(leg_gapx(s,0.45,rearm='zero')+FHz,[Vc,Ppx],'month')
        run3(f"v2.2-lite {lab_}, pair on the housing release (as before)",{'U':U1,'L':confirm_w(leg_gapx(s,0.25,rearm='window'),[Hp3],'month'),'X':X})
        run3(f"v2.3-lite {lab_}, pair on its REAL-TIME clock",{'U':U1,'L':confirm_w(leg_gapx(s,0.25,rearm='window'),[Hp3rt],'month'),'X':X})
        run3(f"v2.3 {lab_}, real-time pair + hours pair (six series)",{'U':U2,'L':confirm_w(leg_gapx(s,0.25,rearm='window'),[Hp3rt],'month'),'X':X})
    ql=[(p,dd) for p,dd in leg_gapx(s,0.25,rearm='window') if not inw(dd)]
    P(f"   U25 quiet proposals {len(ql)}: real-time pair maxima {sorted([wmax_m(MX3,dd) for p,dd in ql],reverse=True)[:5]}")
eH,nq=win_expo([hits(MX3,1.0)]); P(f"\nreal-time pair (3 tenths) window exposure on Paper 1's quiet set 1960-2026: {eH:.2f}% ({nq} quiet months); quiet months at line: {[m.strftime('%Y-%m') for m,v in hits(MX3,1.0).items() if v and quiet(hits(MX3,1.0).index)[m] and m>=pd.Timestamp('1960-01-01')]}")
out.close()
