"""Priced options on top of v2.3 (four series, starts 35, rate half four tenths, real-time, actual release dates):
 (S30) the starts half at 30 log points instead of 35; (H) the NAHB HMI's fall from its 12-month max (line 16.5 points, from 1985) as the
 housing half; (S35|H) starts 35 or the HMI. Both vintages, both line sets; quiet maxima; the 2023 readings."""
from mini import *
from legu_min import s_cur, spl
exec(open('fast34.py').read().split("P(\"HMI level (reading = -HMI):\"")[0].replace("out=open('fast34.out','w')","out=open('fast35.out','w')"))
rate4=(((UR-UR.rolling(12).min())*10).round()/4.0); fall=(hmi.rolling(12).max()-hmi.rolling(2).mean()).dropna()
def mk_pair(dem_h,rel_dem,name):
    ev=[(rel_dem[m],'D',m) for m in dem_h.index if m in rel_dem.index]+[(relU[m],'U',m) for m in rate4.index if m in relU.index and m>=pd.Timestamp('1960-01-01')]
    ev.sort(key=lambda x:(x[0],x[1])); lastD=None; lastU=None; fires={}; mx={}
    for d,kind,m in ev:
        if kind=='D': lastD=m if (lastD is None or m>lastD) else lastD
        else: lastU=m if (lastU is None or m>lastU) else lastU
        if lastD is None or lastU is None: continue
        v=min(dem_h.get(lastD,np.nan),rate4.get(lastU,np.nan))
        if np.isnan(v): continue
        key=max(lastD,lastU); mx[key]=max(mx.get(key,-9),v)
        if v>=1.0 and key not in fires: fires[key]=d
    G=pd.Series({m:(1.0 if m in fires else mx[m]) for m in mx}).sort_index(); PB=pd.Series({m:fires.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=2)) for m in mx}).sort_index()
    return dict(name=name,gap=G,line=1.0,pubs=PB), pd.Series(mx).sort_index()
H35,M35=mk_pair(hous_half,relH,'starts35'); H30,M30=mk_pair((lh.rolling(12).max()-lh.rolling(2).mean())/30.0,relH,'starts30'); HM,MM=mk_pair(fall/16.5,relN,'hmi16.5')
for vint,s in [('CURRENT FILE',s_cur),('FIRST PRINTS',spl)]:
    P(f"\n==== {vint} ====")
    for lab_,Vc,sl in [('a-priori (vac .36, Sahm .50)',VJ36,0.50),('construction-grade (vac .30, Sahm .43)',VJ30,0.43)]:
        X=hub_actual(sl,vr,Vc['line']); U1=confirm_w(leg_gapx(s,0.45,rearm='zero')+FHz,[Vc],'month'); LP=leg_gapx(s,0.25,rearm='window')+FH25
        run3(f"v2.3 (starts 35) {lab_}",{'U':U1,'L':confirm_w(LP,[H35],'month'),'X':X})
        run3(f"option S30: starts at 30 {lab_}",{'U':U1,'L':confirm_w(LP,[H30],'month'),'X':X})
        run3(f"option H: HMI fall 16.5 as the housing half (1985-), starts 35 before {lab_}",{'U':U1,'L':confirm_w([x for x in LP if x[1]<pd.Timestamp('1985-01-01')],[H35],'month')+confirm_w([x for x in LP if x[1]>=pd.Timestamp('1985-01-01')],[HM],'month'),'X':X})
        run3(f"option S35|H: starts 35 or the HMI {lab_}",{'U':U1,'L':confirm_w(LP,[H35,HM],'month'),'X':X})
    ql=[(p,dd) for p,dd in leg_gapx(s,0.25,rearm='window') if not inw(dd)]
    for nm,M in [('starts35',M35),('starts30',M30),('hmi16.5',MM)]:
        P(f"   {nm}: quiet maxima {sorted([wmax_m(M,dd) for p,dd in ql if not np.isnan(wmax_m(M,dd)[0])],reverse=True)[:4]}")
P("\nreadings with no proposal present, autumn 2023 (Oct 2023 is inside Paper 1's 2024 window): starts35",[(m.strftime('%Y-%m'),round(v,2)) for m,v in M35['2023-08':'2024-01'].items()],"| starts30",[(m.strftime('%Y-%m'),round(v,2)) for m,v in M30['2023-08':'2024-01'].items()],"| HMI",[(m.strftime('%Y-%m'),round(v,2)) for m,v in MM['2023-08':'2024-01'].items()])
P("2025-26 readings: starts35",[(m.strftime('%Y-%m'),round(v,2)) for m,v in M35['2025-06':].items()],"| HMI",[(m.strftime('%Y-%m'),round(v,2)) for m,v in MM['2025-06':].items()])
out.close()
