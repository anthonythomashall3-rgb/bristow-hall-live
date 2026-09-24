"""v2.3 on ACTUAL release dates. Housing starts, the unemployment rate and job openings read on the first-print release dates ALFRED records
(cache/relcal_*.csv from relcal.py), not on day-of-month conventions. The pair is fully real-time: at every release of either half, the
latest published reading of each half; it fires on the first release date at which both stand at their lines. Shutdown-delayed starts
(Dec 1995, Sep-Oct 2013, Dec 2018-Feb 2019, Sep 2025-Mar 2026) are late readings, not missing ones."""
from mini import *
from legu_min import s_cur, spl
exec(open('fast26.py').read().split("L25=confirm_w(FH25,[Hp3rt],'month')")[0].replace("out=open('fast26.out','w')","out=open('fast30.out','w')"))
RC={s:pd.read_csv(f'cache/relcal_{s}.csv',index_col=0,parse_dates=['first_release']) for s in ['HOUST','UNRATE','JTSJOL']}
for s in RC: RC[s].index=pd.to_datetime(RC[s].index)
relH=RC['HOUST']['first_release']; relH=relH[relH.index>=pd.Timestamp('1960-06-01')]; relU=RC['UNRATE']['first_release']; relU=relU[relU.index>=pd.Timestamp('1960-03-01')]; relJ=RC['JTSJOL']['first_release']; relJ=relJ[relJ.index>=pd.Timestamp('2010-07-01')]
rate4=(((UR-UR.rolling(12).min())*10).round()/4.0)
def pair_events(rate_h,hous_h):
    """all release events; returns per data-month the earliest firing date (either half's release) and the max reading"""
    ev=[]
    for m in hous_h.index:
        if m in relH.index: ev.append((relH[m],'H',m))
    for m in rate_h.index:
        if m in relU.index and m>=pd.Timestamp('1960-01-01'): ev.append((relU[m],'U',m))
    ev.sort(key=lambda x:(x[0],x[1]))
    lastH=None; lastU=None; fires={}; mx={}
    for d,kind,m in ev:
        if kind=='H': lastH=m if (lastH is None or m>lastH) else lastH
        else: lastU=m if (lastU is None or m>lastU) else lastU
        if lastH is None or lastU is None: continue
        v=min(hous_h.get(lastH,np.nan),rate_h.get(lastU,np.nan))
        if np.isnan(v): continue
        key=max(lastH,lastU)          # label the reading by the later of the two data months
        mx[key]=max(mx.get(key,-9),v)
        if v>=1.0 and key not in fires: fires[key]=d
    return fires,pd.Series(mx).sort_index()
fires4,MX4a=pair_events(rate4,hous_half)
G4a=pd.Series({m:(1.0 if m in fires4 else MX4a[m]) for m in MX4a.index}).sort_index(); PB4a=pd.Series({m:fires4.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=17)) for m in MX4a.index}).sort_index()
H4a=dict(name='pair_r4_actual',gap=G4a,line=1.0,pubs=PB4a)
P("pair (4 tenths) on actual release dates: firing data-months and dates:",[(m.strftime('%Y-%m'),d.strftime('%Y-%m-%d')) for m,d in sorted(fires4.items()) if m>=pd.Timestamp('1970-01-01')][:60])
# hub on actual JOLTS dates where they exist (2010-), the 30th-of-m+1 convention before
def hub_actual(sahm_line,vac,vac_line,back=6):
    calls=[]; armed=True
    for m,v in g.items():
        if m<pd.Timestamp('1948-06-01'): continue
        if armed and v>=sahm_line:
            w=vac[(vac.index>=m-pd.DateOffset(months=back))&(vac.index<=m)]; hit=w[w>=vac_line]
            if len(hit):
                k=hit.index[0]; sp=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
                pk_=relJ[k] if k in relJ.index else pd.Timestamp(k.year,k.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)
                calls.append((max(sp,pk_),m-pd.DateOffset(months=3),'hub')); armed=False
        elif not armed and v<sahm_line: armed=True
    return calls
VJ36=dict(name='vacancy36',gap=vr,line=0.36,pubs=pd.Series({k:(relJ[k] if k in relJ.index else pd.Timestamp(k.year,k.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for k in vr.index}))
VJ30=dict(name='vacancy30',gap=vr,line=0.30,pubs=VJ36['pubs'])
P("JOLTS actual release: days after month end, median by period:",{p:int(((relJ-(relJ.index+pd.offsets.MonthEnd(0))).dt.days)[str(p):str(p+4)].median()) for p in range(2010,2026,5)})
for vint,s in [('CURRENT FILE',s_cur),('FIRST PRINTS',spl)]:
    P(f"\n==== {vint} ====")
    for lab_,Vc,sl in [('a-priori (vac .36, Sahm .50)',VJ36,0.50),('construction-grade (vac .30, Sahm .43)',VJ30,0.43)]:
        X=hub_actual(sl,vr,Vc['line']); U1=confirm_w(leg_gapx(s,0.45,rearm='zero')+FHz,[Vc],'month'); L=confirm_w(leg_gapx(s,0.25,rearm='window')+FH25,[H4a],'month')
        r=run3(f"v2.3 on ACTUAL release dates {lab_}",{'U':U1,'L':L,'X':X})
    ql=[(p,dd) for p,dd in leg_gapx(s,0.25,rearm='window') if not inw(dd)]
    P(f"   U25 quiet proposals {len(ql)}: pair maxima (actual clock) {sorted([wmax_m(MX4a,dd) for p,dd in ql],reverse=True)[:5]}")
qf2=[(p,dd) for p,dd in FH25 if not inw(dd)]; P("   Fieldhouse era U25 quiet maxima:",[(dd.strftime('%Y-%m'),wmax_m(MX4a,dd)) for p,dd in qf2 if not np.isnan(wmax_m(MX4a,dd)[0]) and wmax_m(MX4a,dd)[0]>=0.4])
def quiet(idx):
    q=pd.Series(True,index=idx)
    for p,t in zip(PK,TR): q[(idx>=p-pd.DateOffset(months=9))&(idx<=t+pd.DateOffset(months=18))]=False
    return q
h=(MX4a>=1.0).reindex(pd.date_range('1960-01-01','2026-07-01',freq='MS')).fillna(False); q=quiet(h.index)
P("   quiet months at the line (actual clock):",[m.strftime('%Y-%m') for m,v in h.items() if v and q[m]])
out.close()
