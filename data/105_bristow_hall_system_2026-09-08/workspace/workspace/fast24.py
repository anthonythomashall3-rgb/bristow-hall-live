"""v2.2 RECORD SCRIPT. The two-sided labour rule, fast form, after the window audit and the 1966 exposure:
  supply proposes: IURSA 52-wk gap >= 0.45 (re-arm at a new low; Fieldhouse monthly rate before 1971) confirmed by vacancy (2,6) | hours x nondurable pair;
                   IURSA gap >= 0.25 (window re-arm) confirmed ONLY by the housing x rate pair with the rate half at THREE tenths;
                   hub: Sahm on first prints >= line with vacancy at line in the prior six months, dated crossing-3.
  Windows on DATA MONTHS [dated month-6, dated month+4]. Exact arithmetic on every one-decimal object. Closers K H S (+J on Fieldhouse for 1949)."""
from mini import *
from legu_min import s_cur, spl
from scipy import stats
exec(open('fast21.py').read().split("FHz=[x for x in leg_gap_mx(gm,0.45,rearm='window')")[0].replace("out=open('fast21.out','w')","out=open('fast24.out','w')"))
# ---- exact arithmetic on the hours x nondurable pair (hours to one decimal; employment in thousands)
AWHt=(AWH*10).round().astype('Int64'); mx=AWHt.rolling(12).max(); hours_fire=(100*(mx-AWHt)>=2*AWHt).fillna(False).astype(bool)      # hours 2.0% or more below the 12-month max, exact
NDt=ND.round().astype('Int64'); nd3=NDt.shift(3); nd_fire=(1000*(nd3-NDt)>=12*nd3).fillna(False).astype(bool)                        # nondurable employment down 1.20% or more over three months, exact
P1x=P1.copy()
for m in P1.index:
    ex=bool(hours_fire.get(m,False)) and bool(nd_fire.get(m,False))
    if ex and P1[m]<1.0: P1x[m]=1.0
    if (not ex) and P1[m]>=1.0: P1x[m]=0.999
P("hours pair: months where exact and float disagree:",[m.strftime('%Y-%m') for m in P1.index if (P1[m]>=1.0)!=(P1x[m]>=1.0)])
Ppx=dict(name='hourspair',gap=P1x,line=1.0,pub_day=5)
rate3=(((UR-UR.rolling(12).min())*10).round()/3.0); PAIR3=pd.concat([hous_half,rate3],axis=1).min(axis=1,skipna=False).dropna(); Hp3=dict(name='housing35x_r3',gap=PAIR3,line=1.0,pub_day=18)
FHz=[x for x in leg_gap_mx(gm,0.45,rearm='window') if x[1]<pd.Timestamp('1971-01-01')]
FH25=[x for x in leg_gap_mx(gm,0.25,rearm='window') if x[1]<pd.Timestamp('1971-01-01')]
def inw(dd): return any(p-pd.DateOffset(months=6)<=dd<=t for p,t in zip(PK,TR))
def wmax_m(ser,dd,back=6,fwd=4): seg=ser[(ser.index>=dd-pd.DateOffset(months=back))&(ser.index<=dd+pd.DateOffset(months=fwd))]; return (round(float(seg.max()),2),seg.idxmax().strftime('%Y-%m')) if len(seg) else (float('nan'),'')
P("pair (rate half three tenths) months at line:",[m.strftime('%Y-%m') for m,v in PAIR3.items() if v>=1.0])
P("Sahm gap is rounded to four decimals by the lab (multiples of 1/30): readings at exactly 0.50:",[m.strftime('%Y-%m') for m,v in g.items() if abs(v-0.5)<1e-9])
RES={}
for vint,s in [('CURRENT FILE',s_cur),('FIRST PRINTS',spl)]:
    P(f"\n==== {vint} ====")
    for lab_,Vc,sl in [('a-priori (vac .36, Sahm .50)',V36,0.50),('construction-grade (vac .30, Sahm .43)',V30,0.43)]:
        X=hub(sl,vr,Vc['line']); U2=confirm_w(leg_gapx(s,0.45,rearm='zero')+FHz,[Vc,Ppx],'month'); L3=confirm_w(leg_gapx(s,0.25,rearm='window'),[Hp3],'month')
        r=run3(f"v2.2 {lab_}: U45{{V|P}} + U25{{H3}} + hub; closers K H S J",{'U':U2,'L':L3,'X':X}); RES[(vint,lab_)]=r
        P("      peak date errors",[r['errs_p'].get(i) for i in range(13)],"trough date errors",[r['errs_t'].get(i) for i in range(13)])
        P("      trough calls: "+" | ".join(f"{TR[i]:%Y-%m}:{[t for t in r['turns'] if t['kind']=='trough' and (t['published']-me(TR[i])).days==r['lags_t'][i]][0]['published']:%Y-%m-%d} {[t for t in r['turns'] if t['kind']=='trough' and (t['published']-me(TR[i])).days==r['lags_t'][i]][0]['leg']}" for i in range(13) if i in r['lags_t']))
    ql=[(p,dd) for p,dd in leg_gapx(s,0.25,rearm='window') if not inw(dd)]; qu=[(p,dd) for p,dd in leg_gapx(s,0.45,rearm='zero') if not inw(dd)]
    P(f"   quiet proposals: U25 {len(ql)} (pair maxima {sorted([wmax_m(PAIR3,dd) for p,dd in ql],reverse=True)[:4]}); U45 {len(qu)}")
qf=[(p,dd) for p,dd in FHz if not inw(dd)]; P("   Fieldhouse era, U45 quiet proposals (vacancy, hours pair maxima):",[(dd.strftime('%Y-%m'),wmax_m(vr,dd),wmax_m(P1x,dd)) for p,dd in qf])
qf2=[(p,dd) for p,dd in FH25 if not inw(dd)]; P("   Fieldhouse era, U25 quiet proposals (pair maxima):",[(dd.strftime('%Y-%m'),wmax_m(PAIR3,dd)) for p,dd in qf2])
L25=confirm_w(FH25,[Hp3],'month'); P("   Fieldhouse era, U25 branch calls:",[(p.strftime('%Y-%m-%d'),dd.strftime('%Y-%m'),c) for p,dd,c in L25])
# hazard on Paper 1's quiet set
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
P("\nHAZARD on Paper 1's quiet set (outside peak-9..trough+18), month windows:")
eH,nq=win_expo([hits(PAIR3,1.0)]); P(f"   housing pair (3 tenths): 0 quiet months at line of {nq} (1960-2026); window exposure {eH:.2f}%; rule-of-three ceiling on firing months 3/{nq} x 11 = {3/nq*11*100:.1f}% exposure")
idx=pd.date_range('1972-01-01','2026-07-01',freq='MS'); q=quiet(idx); QY=q.sum()/12
for vint,s in [('current file',s_cur),('first prints',spl)]:
    n25=sum(1 for p,dd in leg_gapx(s,0.25,rearm='window') if q.reindex([dd]).fillna(False).iloc[0]); n45=sum(1 for p,dd in leg_gapx(s,0.45,rearm='zero') if q.reindex([dd]).fillna(False).iloc[0])
    P(f"   {vint}: U25 quiet proposals {n25} in {QY:.1f} quiet yrs ({n25/QY*100:.0f}%/yr) x exposure 0 = 0 observed; ceiling {n25/QY*3/nq*11*100:.2f}%/yr; U45 quiet proposals {n45} -> ceiling {3/QY*100:.2f}%/yr x V|P")
for vl in [0.36,0.30]:
    eVP,_=win_expo([hits(vr,vl),hits(P1x,1.0)]); eVb,_=win_expo([hits(vr,vl)],back=7,fwd=1,start='1949-01-01'); P(f"   vacancy {vl}: V|P window exposure {eVP:.2f}%; six-back vacancy exposure {eVb:.2f}%")
idx2=pd.date_range('1949-01-01','2026-07-01',freq='MS'); q2=quiet(idx2); QY2=q2.sum()/12
for sl,vl in [(0.50,0.36),(0.43,0.30)]:
    eps=[]; armed=True
    for m,v in g.items():
        if m<idx2[0]: continue
        if armed and v>=sl:
            armed=False
            if q2.reindex([m]).fillna(False).iloc[0]: eps.append(m.strftime('%Y-%m'))
        elif not armed and v<sl: armed=True
    eVb,_=win_expo([hits(vr,vl)],back=7,fwd=1,start='1949-01-01'); r=len(eps)/QY2
    P(f"   hub Sahm {sl}: quiet crossings {eps} in {QY2:.1f} quiet yrs = {r*100:.2f}%/yr x six-back vacancy {eVb:.2f}% = {r*eVb:.3f}%/yr observed (one in {1/(r*eVb/100):.0f})")
out.close()
