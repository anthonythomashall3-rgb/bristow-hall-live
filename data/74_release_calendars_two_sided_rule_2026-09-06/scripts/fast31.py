"""Demand-side candidates held on the Mac, tested as confirmers of the low insured-rate branch beside the starts half (rate half four tenths):
auto sales (TOTALSA latest vintage 1976-; ALTSALES first prints 1997-) and industrial production first prints (INDPRO, ALFRED 1927-),
each as '2-month mean X% below its 12-month max', read at its own release (autos ~2nd of m+1; IP on ALFRED's first-release dates)."""
from mini import *
from legu_min import s_cur, spl
exec(open('fast30.py').read().split("for vint,s in [('CURRENT FILE',s_cur),('FIRST PRINTS',spl)]:")[0].replace("out=open('fast30.out','w')","out=open('fast31.out','w')"))
import csv
def latest_vintage(series):
    rows=list(csv.reader(open(AL+series+"_all_vintages.csv"))); dates=[pd.Timestamp(r[0]) for r in rows[1:]]
    return pd.Series({dates[i]:float(rows[1+i][-1]) for i in range(len(dates)) if rows[1+i][-1] not in ('','.')}).sort_index()
TOT=latest_vintage('TOTALSA'); lt=np.log(TOT)*100
IP=first_prints('INDPRO'); lip=np.log(IP)*100
from relcal import release_calendar
relI=release_calendar('INDPRO')['first_release']; relI=relI[relI.index>=pd.Timestamp('1960-01-01')]
def half(l,X): return (l.rolling(12).max()-l.rolling(2).mean())/X
def pair_generic(rate_h,dem_h,rel_dem):
    ev=[(rel_dem[m],'D',m) for m in dem_h.index if m in rel_dem.index]+[(relU[m],'U',m) for m in rate_h.index if m in relU.index and m>=pd.Timestamp('1960-01-01')]
    ev.sort(key=lambda x:(x[0],x[1])); lastD=None; lastU=None; fires={}; mx={}
    for d,kind,m in ev:
        if kind=='D': lastD=m if (lastD is None or m>lastD) else lastD
        else: lastU=m if (lastU is None or m>lastU) else lastU
        if lastD is None or lastU is None: continue
        v=min(dem_h.get(lastD,np.nan),rate_h.get(lastU,np.nan))
        if np.isnan(v): continue
        key=max(lastD,lastU); mx[key]=max(mx.get(key,-9),v)
        if v>=1.0 and key not in fires: fires[key]=d
    G=pd.Series({m:(1.0 if m in fires else mx[m]) for m in mx}).sort_index(); PB=pd.Series({m:fires.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=2)) for m in mx}).sort_index()
    return dict(gap=G,line=1.0,pubs=PB), pd.Series(mx).sort_index()
relA=pd.Series({m:pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=1) for m in lt.index})   # unit sales public ~2nd of m+1
def quiet(idx):
    q=pd.Series(True,index=idx)
    for p,t in zip(PK,TR): q[(idx>=p-pd.DateOffset(months=9))&(idx<=t+pd.DateOffset(months=18))]=False
    return q
for nm,l,relD,Xs in [('AUTO SALES (TOTALSA, 1976-)',lt,relA,[15,20,25]),('INDUSTRIAL PRODUCTION first prints',lip,relI,[2,3,4])]:
    for X in Xs:
        cf,MX=pair_generic(rate4,half(l,X),relD); cf['name']=f'{nm[:4]}{X}x_r4'
        h=(MX>=1.0).reindex(pd.date_range('1960-01-01','2026-07-01',freq='MS')).fillna(False); q=quiet(h.index)
        P(f"\n{nm} at {X}: quiet months at line {[m.strftime('%Y-%m') for m,v in h.items() if v and q[m]]}")
        for vint,s in [('current',s_cur),('first prints',spl)]:
            ql=[(p,dd) for p,dd in leg_gapx(s,0.25,rearm='window') if not inw(dd)]
            P(f"   {vint}: U25 quiet-window maxima {sorted([wmax_m(MX,dd) for p,dd in ql],reverse=True)[:3]}")
            X_=hub_actual(0.43,vr,0.30); U1=confirm_w(leg_gapx(s,0.45,rearm='zero')+FHz,[VJ30],'month')
            run3(f"   {nm} {X} as SOLE confirmer of U25 (corner lines, {vint})",{'U':U1,'L':confirm_w(leg_gapx(s,0.25,rearm='window'),[cf],'month'),'X':X_})
            run3(f"   starts OR {nm} {X} (corner lines, {vint})",{'U':U1,'L':confirm_w(leg_gapx(s,0.25,rearm='window'),[H4a,cf],'month'),'X':X_})
out.close()
