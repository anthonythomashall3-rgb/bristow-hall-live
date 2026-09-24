"""The safest way to buy each remaining day: the full matrix on actual release dates — hub Sahm {0.50, 0.43} x vacancy {0.36, 0.30} x U45 confirmers
{vacancy, vacancy|hours pair}; low branch fixed (starts 35, rate half four tenths, real-time). Records both vintages; hazard components."""
from mini import *
from legu_min import s_cur, spl
exec(open('fast35.py').read().split("for vint,s in [('CURRENT FILE',s_cur),('FIRST PRINTS',spl)]:")[0].replace("out=open('fast35.out','w')","out=open('fast36.out','w')"))
def quiet(idx):
    q=pd.Series(True,index=idx)
    for p,t in zip(PK,TR): q[(idx>=p-pd.DateOffset(months=9))&(idx<=t+pd.DateOffset(months=18))]=False
    return q
def hits(o,line): o=o.dropna(); return (o>=line).reindex(pd.date_range('1949-01-01','2026-07-01',freq='MS')).fillna(False)
def win_expo(hitlist, back=7, fwd=5, start='1960-01-01'):
    idx=pd.date_range(start,'2026-07-01',freq='MS'); h=np.zeros(len(idx),bool)
    for x in hitlist: h|=x.reindex(idx).fillna(False).values.astype(bool)
    s=pd.Series(h,index=idx); q=quiet(idx)
    f=s[::-1].rolling(fwd,min_periods=1).max()[::-1].astype(bool); b=s.rolling(back,min_periods=1).max().astype(bool)
    return (f|b)[q].mean()*100, int(q.sum())
idx2=pd.date_range('1949-01-01','2026-07-01',freq='MS'); q2=quiet(idx2); QY2=q2.sum()/12
def hub_haz(sl,vl):
    eps=[]; armed=True
    for m,v in g.items():
        if m<idx2[0]: continue
        if armed and v>=sl:
            armed=False
            if q2.reindex([m]).fillna(False).iloc[0]: eps.append(m.strftime('%Y-%m'))
        elif not armed and v<sl: armed=True
    eVb,_=win_expo([hits(vr,vl)],back=7,fwd=1,start='1949-01-01'); r=len(eps)/QY2
    return eps, eVb, r*eVb
for sl in [0.50,0.43]:
    for vl in [0.36,0.30]:
        eps,eVb,hz=hub_haz(sl,vl); P(f"hub Sahm {sl} x vacancy {vl}: quiet crossings {eps} x six-back exposure {eVb:.2f}% = {hz:.3f}%/yr observed (one in {1/(hz/100):.0f})")
for vl in [0.36,0.30]:
    eV,_=win_expo([hits(vr,vl)]); eVP,_=win_expo([hits(vr,vl),hits(P1x,1.0)]); P(f"U45 confirmer window exposure at vacancy {vl}: V {eV:.2f}%  V|P {eVP:.2f}%  (0 quiet proposals since 1971; ceiling 9.89%/yr x exposure = {9.89*eV/100:.2f} / {9.89*eVP/100:.2f} %/yr)")
for vint,s in [('CURRENT FILE',s_cur),('FIRST PRINTS',spl)]:
    P(f"\n==== {vint} ====")
    LP=leg_gapx(s,0.25,rearm='window')+FH25; L=confirm_w(LP,[H35],'month')
    for sl in [0.50,0.43]:
        for Vc in [VJ36,VJ30]:
            X=hub_actual(sl,vr,Vc['line'])
            for cf,nm in [([Vc],'V'),([Vc,Ppx],'V|P')]:
                U1=confirm_w(leg_gapx(s,0.45,rearm='zero')+FHz,cf,'month')
                run3(f"Sahm {sl}, vacancy {Vc['line']}, U45{{{nm}}}",{'U':U1,'L':L,'X':X})
out.close()
