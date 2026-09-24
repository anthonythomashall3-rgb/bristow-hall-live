"""v2.3 RECORD SCRIPT (6 Sep 2026). Four series: insured unemployment rate (IURSA weekly; Fieldhouse monthly before 1971), unemployment rate
(first prints), vacancy rate ((2,6) gap), housing starts (first prints).
  U45: insured rate 0.45 above its 52-week low (re-arm at a new low) confirmed by the vacancy at its line;
  U25: insured rate 0.25 above its low (window re-arm) confirmed by the housing x rate pair — starts' 2-month mean 35 log points below
       their 12-month max AND the unemployment rate FOUR tenths above its 12-month low — each half read at its own release (real-time clock);
  hub: Sahm indicator on first prints at its line with the vacancy at its line in the prior six months, dated crossing-3.
  Windows on data months (6 back, 4 forward). Exact arithmetic. Closers K H S (+J on Fieldhouse for 1949). Both branches run on the
  Fieldhouse monthly rate before 1971. Priced alternative: + hours x nondurable pair on U45 (1980 -7)."""
from mini import *
from legu_min import s_cur, spl
from scipy import stats
exec(open('fast26.py').read().split("L25=confirm_w(FH25,[Hp3rt],'month')")[0].replace("out=open('fast26.out','w')","out=open('fast29.out','w')"))
rate4=(((UR-UR.rolling(12).min())*10).round()/4.0); PAIR4=pd.concat([hous_half,rate4],axis=1).min(axis=1,skipna=False).dropna()
G4,PB4,MX4=rt_pair(rate4,hous_half); H4=dict(name='pair_r4_rt',gap=G4,line=1.0,pubs=PB4); H4s=dict(name='pair_r4_same',gap=PAIR4,line=1.0,pub_day=18)
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
P("pair (4 tenths, real-time) months at line:",[m.strftime('%Y-%m') for m,v in MX4.items() if v>=1.0])
RES={}
for vint,s in [('CURRENT FILE',s_cur),('FIRST PRINTS',spl)]:
    P(f"\n==== {vint} ====")
    for lab_,Vc,sl in [('a-priori (vac .36, Sahm .50)',V36,0.50),('construction-grade (vac .30, Sahm .43)',V30,0.43)]:
        X=hub(sl,vr,Vc['line']); U1=confirm_w(leg_gapx(s,0.45,rearm='zero')+FHz,[Vc],'month'); U2=confirm_w(leg_gapx(s,0.45,rearm='zero')+FHz,[Vc,Ppx],'month')
        L=confirm_w(leg_gapx(s,0.25,rearm='window')+FH25,[H4],'month'); Ls=confirm_w(leg_gapx(s,0.25,rearm='window')+FH25,[H4s],'month')
        r=run3(f"v2.3 FOUR SERIES {lab_}: U45{{V}} + U25{{pair 4 tenths, real-time}} + hub",{'U':U1,'L':L,'X':X}); RES[(vint,lab_)]=r
        P("      peak date errors",[r['errs_p'].get(i) for i in range(13)],"trough date errors",[r['errs_t'].get(i) for i in range(13)])
        P("      trough calls: "+" | ".join(f"{TR[i]:%Y-%m}:{[t for t in r['turns'] if t['kind']=='trough' and (t['published']-me(TR[i])).days==r['lags_t'][i]][0]['published']:%Y-%m-%d} {[t for t in r['turns'] if t['kind']=='trough' and (t['published']-me(TR[i])).days==r['lags_t'][i]][0]['leg']}" for i in range(13) if i in r['lags_t']))
        run3(f"   alt: same-month pair clock {lab_}",{'U':U1,'L':Ls,'X':X})
        run3(f"   alt: + hours pair on U45 (six series) {lab_}",{'U':U2,'L':L,'X':X})
    ql=[(p,dd) for p,dd in leg_gapx(s,0.25,rearm='window') if not inw(dd)]; qu=[(p,dd) for p,dd in leg_gapx(s,0.45,rearm='zero') if not inw(dd)]
    P(f"   quiet proposals: U25 {len(ql)} {[dd.strftime('%Y-%m') for p,dd in ql]}; pair maxima real-time {sorted([wmax_m(MX4,dd) for p,dd in ql],reverse=True)[:5]}; U45 {len(qu)}")
qf=[(p,dd) for p,dd in FHz if not inw(dd)]; P("   Fieldhouse era, U45 quiet proposals (vacancy maxima):",[(dd.strftime('%Y-%m'),wmax_m(vr,dd)) for p,dd in qf])
qf2=[(p,dd) for p,dd in FH25 if not inw(dd)]; P("   Fieldhouse era, U25 quiet proposals (pair maxima):",[(dd.strftime('%Y-%m'),wmax_m(MX4,dd)) for p,dd in qf2 if not np.isnan(wmax_m(MX4,dd)[0])])
P("   Fieldhouse era, U25 branch calls:",[(p.strftime('%Y-%m-%d'),dd.strftime('%Y-%m'),c) for p,dd,c in confirm_w(FH25,[H4],'month')])
P("\nHAZARD on Paper 1's quiet set (outside peak-9..trough+18), month windows:")
for nm,ser in [('4 tenths real-time',MX4),('4 tenths same-month',PAIR4),('3 tenths real-time',MX3),('3 tenths same-month',PAIR3)]:
    h=hits(ser,1.0); q=quiet(h.index); e,n=win_expo([h]); P(f"   pair {nm}: quiet months at line {[m.strftime('%Y-%m') for m,v in h.items() if v and q[m] and m>=pd.Timestamp('1960-01-01')]}; window exposure {e:.2f}% of {n}")
idx=pd.date_range('1972-01-01','2026-07-01',freq='MS'); q=quiet(idx); QY=q.sum()/12
for vint,s in [('current file',s_cur),('first prints',spl)]:
    n25=sum(1 for p,dd in leg_gapx(s,0.25,rearm='window') if q.reindex([dd]).fillna(False).iloc[0]); n45=sum(1 for p,dd in leg_gapx(s,0.45,rearm='zero') if q.reindex([dd]).fillna(False).iloc[0])
    P(f"   {vint}: U25 quiet proposals {n25} in {QY:.1f} quiet yrs ({n25/QY*100:.0f}%/yr) x pair exposure 0 = 0 observed, ceiling {n25/QY*3/442*11*100:.2f}%/yr; U45 quiet proposals {n45}, ceiling {3/QY*100:.2f}%/yr x vacancy window")
for vl in [0.36,0.30]:
    eV,_=win_expo([hits(vr,vl)]); eVb,_=win_expo([hits(vr,vl)],back=7,fwd=1,start='1949-01-01'); P(f"   vacancy {vl}: window exposure {eV:.2f}%; six-back exposure (hub) {eVb:.2f}%")
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
    P(f"   hub Sahm {sl}: quiet crossings {eps} = {r*100:.2f}%/yr x six-back vacancy {eVb:.2f}% = {r*eVb:.3f}%/yr observed (one in {1/(r*eVb/100):.0f})")
out.close()
