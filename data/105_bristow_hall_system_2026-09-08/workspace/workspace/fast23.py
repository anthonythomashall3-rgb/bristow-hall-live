"""The 1966 exposure of the fast form: the low insured-rate branch run on the Fieldhouse reconstruction before 1971 calls Dec 1966
(housing pair Jul-Oct 1966: starts -40%, first-print unemployment rate up exactly two tenths). Repricing: (A) core only; (B) fast form as built
(rate half two tenths); (C) fast form with the pair's rate half at THREE tenths (the tightest clean reading on the whole record incl. the reconstruction);
(D) forward-only confirmation of the low branch. Month windows throughout."""
from mini import *
from legu_min import s_cur, spl
exec(open('fast21.py').read().split("FHz=[x for x in leg_gap_mx(gm,0.45,rearm='window')")[0].replace("out=open('fast21.out','w')","out=open('fast23.out','w')"))
FHz=[x for x in leg_gap_mx(gm,0.45,rearm='window') if x[1]<pd.Timestamp('1971-01-01')]
FH25=[x for x in leg_gap_mx(gm,0.25,rearm='window') if x[1]<pd.Timestamp('1971-01-01')]
rate3=(((UR-UR.rolling(12).min())*10).round()/3.0); PAIR3=pd.concat([hous_half,rate3],axis=1).min(axis=1,skipna=False).dropna(); Hp3=dict(name='housing35x_r3',gap=PAIR3,line=1.0,pub_day=18)
def inw(dd): return any(p-pd.DateOffset(months=6)<=dd<=t for p,t in zip(PK,TR))
def wmax_m(ser,dd,back=6,fwd=4): seg=ser[(ser.index>=dd-pd.DateOffset(months=back))&(ser.index<=dd+pd.DateOffset(months=fwd))]; return (round(seg.max(),2),seg.idxmax().strftime('%Y-%m')) if len(seg) else (float('nan'),'')
P("pair with rate half three tenths: months at line:",[m.strftime('%Y-%m') for m,v in PAIR3.items() if v>=1.0])
P("pair with rate half two tenths:   months at line:",[m.strftime('%Y-%m') for m,v in PAIRX2.items() if v>=1.0])
for nm,Hc in [('two tenths',HpX2),('three tenths',Hp3)]:
    L=confirm_w(FH25,[Hc],'month'); P(f"FH low branch (0.25) before 1971, pair rate half {nm}: confirmed {[(p.strftime('%Y-%m-%d'),dd.strftime('%Y-%m'),c) for p,dd,c in L]}; quiet {[(dd.strftime('%Y-%m')) for p,dd,c in L if not inw(dd)]}")
for vint,s in [('CURRENT FILE',s_cur),('FIRST PRINTS',spl)]:
    P(f"\n==== {vint} ====")
    for lab_,Vc,sl in [('a-priori (vac .36, Sahm .50)',V36,0.50),('construction-grade (vac .30, Sahm .43)',V30,0.43)]:
        X=hub(sl,vr,Vc['line']); U2=confirm_w(leg_gapx(s,0.45,rearm='zero')+FHz,[Vc,Pp],'month')
        run3(f"A. CORE {lab_}: U45{{V|P}} + hub",{'U':U2,'X':X})
        run3(f"B. FAST as built {lab_}: + U25{{H, rate half 2 tenths}}",{'U':U2,'L':confirm_w(leg_gapx(s,0.25,rearm='window'),[HpX2],'month'),'X':X})
        run3(f"C. FAST rate half 3 tenths {lab_}: + U25{{H3}}",{'U':U2,'L':confirm_w(leg_gapx(s,0.25,rearm='window'),[Hp3],'month'),'X':X})
        run3(f"D. FAST forward-only low branch {lab_}: + U25{{H, 0 back 4 fwd}}",{'U':U2,'L':confirm_w(leg_gapx(s,0.25,rearm='window'),[HpX2],'month',back=0),'X':X})
    ql=[(p,dd) for p,dd in leg_gapx(s,0.25,rearm='window') if not inw(dd)]
    P(f"   U25 quiet proposals {len(ql)}: pair(2 tenths) max {max(wmax_m(PAIRX2,dd)[0] for p,dd in ql)}, pair(3 tenths) max {max(wmax_m(PAIR3,dd)[0] for p,dd in ql)} {[(dd.strftime('%Y-%m'),wmax_m(PAIR3,dd)) for p,dd in ql if wmax_m(PAIR3,dd)[0]>=0.5]}")
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
for nm,Pr in [('two tenths',PAIRX2),('three tenths',PAIR3)]:
    e,n=win_expo([hits(Pr,1.0)]); e2,n2=win_expo([hits(Pr,1.0)],start='1972-01-01')
    P(f"pair rate half {nm}: window exposure {e:.2f}% of {n} quiet months 1960-2026; {e2:.2f}% of {n2} quiet months 1972-2026")
out.close()
