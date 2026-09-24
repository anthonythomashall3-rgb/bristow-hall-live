"""The pair's rate half at FOUR tenths (the safest clean reading: the four recession firings read 4,5,4,5 tenths; the quiet maxima 3):
same-month and real-time clocks; record, quiet maxima, Fieldhouse era, exposure."""
from mini import *
from legu_min import s_cur, spl
exec(open('fast26.py').read().split("L25=confirm_w(FH25,[Hp3rt],'month')")[0].replace("out=open('fast26.out','w')","out=open('fast28.out','w')"))
rate4=(((UR-UR.rolling(12).min())*10).round()/4.0); PAIR4=pd.concat([hous_half,rate4],axis=1).min(axis=1,skipna=False).dropna(); Hp4=dict(name='housing35x_r4',gap=PAIR4,line=1.0,pub_day=18)
G4,PB4,MX4=rt_pair(rate4,hous_half); Hp4rt=dict(name='housing35x_r4_rt',gap=G4,line=1.0,pubs=PB4)
P("pair (4 tenths) same-month months at line:",[m.strftime('%Y-%m') for m,v in PAIR4.items() if v>=1.0])
P("pair (4 tenths) real-time extra months:",[m.strftime('%Y-%m') for m in G4.index if G4[m]>=1.0 and PAIR4.get(m,0)<1.0])
for nm,Hs,Hr in [('4 tenths',Hp4,Hp4rt)]:
    P(f"Fieldhouse era, low branch, {nm}: same-month calls {[(p.strftime('%Y-%m-%d'),dd.strftime('%Y-%m'),c) for p,dd,c in confirm_w(FH25,[Hs],'month')]}; rt calls {[(p.strftime('%Y-%m-%d'),dd.strftime('%Y-%m'),c) for p,dd,c in confirm_w(FH25,[Hr],'month')]}; quiet maxima same {[(dd.strftime('%Y-%m'),wmax_m(PAIR4,dd)) for p,dd in FH25 if not inw(dd) and wmax_m(PAIR4,dd)[0]>=0.4]} rt {[(dd.strftime('%Y-%m'),wmax_m(MX4,dd)) for p,dd in FH25 if not inw(dd) and wmax_m(MX4,dd)[0]>=0.4]}")
for vint,s in [('CURRENT FILE',s_cur),('FIRST PRINTS',spl)]:
    P(f"\n==== {vint} ====")
    ql=[(p,dd) for p,dd in leg_gapx(s,0.25,rearm='window') if not inw(dd)]
    P(f"   U25 quiet proposals {len(ql)}: pair(4) same-month maxima {sorted([wmax_m(PAIR4,dd) for p,dd in ql],reverse=True)[:4]} | real-time {sorted([wmax_m(MX4,dd) for p,dd in ql],reverse=True)[:4]}")
    for lab_,Vc,sl in [('a-priori (vac .36, Sahm .50)',V36,0.50),('construction-grade (vac .30, Sahm .43)',V30,0.43)]:
        X=hub(sl,vr,Vc['line']); U1=confirm_w(leg_gapx(s,0.45,rearm='zero')+FHz,[Vc],'month'); U2=confirm_w(leg_gapx(s,0.45,rearm='zero')+FHz,[Vc,Ppx],'month')
        run3(f"four series, pair 4 tenths SAME-MONTH, {lab_}",{'U':U1,'L':confirm_w(leg_gapx(s,0.25,rearm='window'),[Hp4],'month'),'X':X})
        run3(f"four series, pair 4 tenths REAL-TIME, {lab_}",{'U':U1,'L':confirm_w(leg_gapx(s,0.25,rearm='window'),[Hp4rt],'month'),'X':X})
        run3(f"six series (hours pair), pair 4 tenths REAL-TIME, {lab_}",{'U':U2,'L':confirm_w(leg_gapx(s,0.25,rearm='window'),[Hp4rt],'month'),'X':X})
for nm,ser in [('4 tenths same-month',PAIR4),('4 tenths real-time',MX4)]:
    e,n=win_expo([hits(ser,1.0)]); P(f"pair {nm}: quiet months at line {[m.strftime('%Y-%m') for m,v in hits(ser,1.0).items() if v and quiet(hits(ser,1.0).index)[m] and m>=pd.Timestamp('1960-01-01')]}; window exposure {e:.2f}%")
out.close()
