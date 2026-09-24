"""STEP 1a — THE PAUSE-AND-TROUGH TABLE. For each of the nine troughs of the main sample and the five mid-episode
pauses at which every fast closer so far has fired early, every candidate object's reading, week by week and month by
month, with the date it was public. First prints and actual release dates where they exist. The question: what is
public inside the month after a trough that is NOT public inside a pause?"""
import sys, io, contextlib
sys.argv=['x','2011','2012','wt1a']
src=open('walk26.py').read().split("Y0,Y1,VAR=int(sys.argv[1])")[0]
with contextlib.redirect_stdout(io.StringIO()): exec(src)
out.close()
import pandas as pd, numpy as np
OUT=open('out/t1a.txt','w')
def P(*a):
    print(*a); print(*a,file=OUT); OUT.flush()
ODD=W.replace('24_bristow_rule_lab/workspace','')
# ---------------- events
OPENS={'1970':'1969-08-21','1975':'1973-09-15','1980':'1979-11-29','1982':'1981-02-26','1991':'1990-08-03',
       '2001':'2001-03-10','2009':'2007-12-13','2020':'2020-03-26','2024':'2024-05-03'}
EV=[('T','1970-11','1970'),('P','1970-08','1970'),('T','1975-03','1975'),('P','1974-07','1975'),('T','1980-07','1980'),
    ('T','1982-11','1982'),('P','1982-05','1982'),('T','1991-03','1991'),('T','2001-11','2001'),('P','2001-06','2001'),
    ('T','2009-06','2009'),('P','2008-05','2009'),('T','2020-04','2020'),('T','2024-08','2024')]
def me(t): return t+pd.offsets.MonthEnd(0)
# ---------------- weekly objects
IC4=ICfp.dropna().rolling(4).mean().dropna()                    # initial claims, first prints where they exist
CC=pd.read_csv(W+'/lab/data/fred_weekly/CCSA.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
CC4=CC.rolling(4).mean().dropna()
IU=IURW.dropna()                                                # weekly insured rate, own transcription then IURSA
SPX=pd.read_csv(W+'/lab/speed2/data/sp500_daily_yahoo.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
SPW=SPX.resample('W-FRI').last().dropna()
SPlow=(SPW/SPW.rolling(26,min_periods=13).min()-1)*100          # per cent above the 26-week low
SM=Sm.dropna()                                                  # paper spread, 13-week mean
# state panels
p539=pd.read_csv(ODD+'37_dol_eta5159_2026-09/panel/panel_539_weekly.csv',parse_dates=['week'])
p539=p539[~p539.st.isin(['PR','VI'])]
W539=p539.pivot_table(index='week',columns='st',values='ic',aggfunc='first').sort_index().apply(pd.to_numeric,errors='coerce')
ICN=pd.read_csv(W+'/lab/data/fred_weekly/ICNSA.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
ICS=pd.read_csv(W+'/lab/data/fred_weekly/ICSA.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
FAC=(ICS/ICN).dropna()                                          # the Department's own weekly seasonal factor, national
W539=W539.mul(FAC.reindex(W539.index),axis=0)                    # states adjusted with the national factor (real-time: published with the week)
W539m=W539.rolling(4).mean()
p5159=pd.read_csv(ODD+'37_dol_eta5159_2026-09/panel/panel_5159_monthly.csv',parse_dates=['month'])
p5159=p5159[~p5159.st.isin(['PR','VI'])]
M5159=p5159.pivot_table(index='month',columns='st',values='ic_total',aggfunc='first').sort_index().apply(pd.to_numeric,errors='coerce')
_mN=ICN.resample('MS').sum(); _mS=ICS.resample('MS').sum(); MFAC=(_mS/_mN).dropna()
M5159=M5159.mul(MFAC.reindex(M5159.index),axis=0)
W59=pd.read_csv(ODD+'59_dol_weekly_state_claims_1945-1983_2026-09/ic_weekly_state_1945_1983_wide.csv',index_col=0,parse_dates=True)
W59=W59.drop(columns=[c for c in W59.columns if c in ('Puerto Rico','Virgin Islands')],errors='ignore')
W59=W59.resample('W-SAT').last()
W59=W59.mul(FAC.reindex(W59.index),axis=0)
W59m=W59.rolling(4,min_periods=3).mean()
def breadth_rec(panel,open_,upto,x):
    """share of units whose own reading stands x per cent below its own maximum since the open"""
    seg=panel[(panel.index>=open_)&(panel.index<=upto)]
    if len(seg)<3: return np.nan,0
    mx=seg.max(); cur=seg.iloc[-1]; ok=cur.notna()&mx.notna()&(mx>0)
    if ok.sum()<20: return np.nan,int(ok.sum())
    return float(((cur[ok]/mx[ok]-1)*100<=-x).mean()*100),int(ok.sum())
# ---------------- monthly objects
PAY=first_prints('PAYEMS')
UMC=first_prints('UMCSENT') if os.path.exists(AL+'UMCSENT_all_vintages.csv') else None
_umc_cur=pd.read_csv(W+'/lab/ind/UMCSENT.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
UMC=pd.concat([_umc_cur[_umc_cur.index<UMC.index.min()],UMC]).sort_index() if UMC is not None else _umc_cur
_swd=pd.read_csv(ODD+'Bristow Hall Rule/Paper 2 v2/data/SURVEY_WEEK_INSURED_RATE.csv',parse_dates=['month','published']); SWPUB=_swd.set_index('month')['published']
bos=pd.read_csv(W+'/lab/acq/ussurv/bos_history.csv'); bos['m']=pd.to_datetime(bos['DATE'],format='%b-%y'); BOS=bos.set_index('m')['gacdfsa']
def third_thursday(m):
    d=pd.Timestamp(m.year,m.month,1); off=(3-d.weekday())%7; return d+pd.Timedelta(days=off+14)
def fmt(v,f='{:.1f}'):
    return '   .  ' if v is None or (isinstance(v,float) and np.isnan(v)) else f.format(v)
for kind,ev,epi in EV:
    E=pd.Timestamp(ev+'-01'); op=pd.Timestamp(OPENS[epi]); mend=me(E); deadline=mend+pd.Timedelta(days=31)
    P(f"\n{'='*118}\n{'TROUGH' if kind=='T' else 'PAUSE '} {ev}   episode opened {op:%Y-%m-%d}   month ends {mend:%Y-%m-%d}   inside-the-month deadline {deadline:%Y-%m-%d}")
    # weekly block
    P("  week        pub-IC   IC4k  dIC  fall | pub-CC   CC4k  dCC | IUR  dIUR | brd5 brd10 (n) pub-brd | S&P%>26wlo | spread dSPR")
    wk0=E-pd.DateOffset(months=2); wk1=me(E+pd.DateOffset(months=2))
    weeks=IC4[(IC4.index>=wk0)&(IC4.index<=wk1)].index if E>pd.Timestamp('1967-06-01') else IU[(IU.index>=wk0)&(IU.index<=wk1)].index
    fall=0; prev=None
    for wkd in weeks:
        # initial claims
        segI=IC4[(IC4.index>=op)&(IC4.index<=wkd)]
        if len(segI):
            v=segI.iloc[-1]; dI=100*(np.log(segI.max())-np.log(v))
            fall=fall+1 if (prev is not None and v<prev) else 0; prev=v
        else: v=dI=np.nan; fall=0
        segC=CC4[(CC4.index>=op)&(CC4.index<=wkd)]
        vc=segC.iloc[-1] if len(segC) else np.nan; dC=100*(np.log(segC.max())-np.log(vc)) if len(segC) else np.nan
        segU=IU[(IU.index>=op)&(IU.index<=wkd)]
        vu=segU.iloc[-1] if len(segU) else np.nan; dU=(segU.max()-vu) if len(segU) else np.nan
        # breadth: weekly 539 from 1986, else the 1945-83 weekly panel
        if wkd>=pd.Timestamp('1986-06-01'): b5,n=breadth_rec(W539m,op,wkd,5); b10,_=breadth_rec(W539m,op,wkd,10); pb=wkd+pd.Timedelta(days=19)
        elif wkd<=pd.Timestamp('1983-04-30'): b5,n=breadth_rec(W59m,op,wkd,5); b10,_=breadth_rec(W59m,op,wkd,10); pb=wkd+pd.Timedelta(days=19)
        else: b5=b10=np.nan; n=0; pb=wkd
        sp=SPlow[SPlow.index<=wkd+pd.Timedelta(days=6)]; spv=sp.iloc[-1] if len(sp) else np.nan
        segS=SM[(SM.index>=op)&(SM.index<=wkd+pd.Timedelta(days=6))]
        sv=segS.iloc[-1] if len(segS) else np.nan; dS=(segS.max()-sv) if len(segS) else np.nan
        flag='*' if (wkd+pd.Timedelta(days=5))<=deadline and (wkd+pd.Timedelta(days=5))>mend else ' '
        P(f"{flag} {wkd:%Y-%m-%d}  {wkd+pd.Timedelta(days=5):%m-%d}  {fmt(v/1000,'{:6.0f}')} {fmt(dI,'{:5.1f}')} {fall:3d}  | {wkd+pd.Timedelta(days=12):%m-%d}  {fmt(vc/1000,'{:6.0f}')} {fmt(dC,'{:5.1f}')} | {fmt(vu,'{:4.1f}')} {fmt(dU,'{:4.1f}')} | {fmt(b5,'{:4.0f}')} {fmt(b10,'{:5.0f}')} ({n:2d}) {pb:%m-%d} | {fmt(spv,'{:6.1f}')} | {fmt(sv,'{:5.2f}')} {fmt(dS,'{:5.2f}')}")
    # monthly block
    P("  month  | UR(fp) dUR pub  | PAY(fp)k dPAY  | AWH dAWH | starts(fp) %vs12lo 3m/prev3m pub | SW dSW pub | vac  | BOS(gac) pub | UMC | sahm")
    for k in range(-3,3):
        m=E+pd.DateOffset(months=k)
        ur=float(UR.get(m,np.nan)); urp=float(UR.get(m-pd.DateOffset(months=1),np.nan)); dur=(round(ur*10)-round(urp*10)) if not np.isnan(ur) and not np.isnan(urp) else np.nan
        pu=rel.get(m,pd.NaT)
        pay=float(PAY.get(m,np.nan)); payp=float(PAY.get(m-pd.DateOffset(months=1),np.nan)); dpay=pay-payp
        aw=float(AWH.get(m,np.nan)); awp=float(AWH.get(m-pd.DateOffset(months=1),np.nan)); daw=aw-awp if not np.isnan(aw) and not np.isnan(awp) else np.nan
        hs=float(HO.get(m,np.nan)); lo12=HO[(HO.index>m-pd.DateOffset(months=12))&(HO.index<=m)].min(); pct=(hs/lo12-1)*100 if not np.isnan(hs) else np.nan
        h3=HO[(HO.index>m-pd.DateOffset(months=3))&(HO.index<=m)].mean(); h3p=HO[(HO.index>m-pd.DateOffset(months=6))&(HO.index<=m-pd.DateOffset(months=3))].mean()
        r3=(h3/h3p-1)*100 if not np.isnan(h3) and not np.isnan(h3p) else np.nan
        ph=relH.get(m,pd.NaT)
        sw=float(SI.get(m,np.nan)); swp=float(SI.get(m-pd.DateOffset(months=1),np.nan)); dsw=sw-swp if not np.isnan(sw) and not np.isnan(swp) else np.nan
        swpub=SWPUB.get(m,pd.NaT)
        vac=float(vr.get(m,np.nan))
        bo=float(BOS.get(m,np.nan)); bpub=third_thursday(m)
        um=float(UMC.get(m,np.nan)) if UMC is not None else np.nan
        sg=float(g.get(m,np.nan))
        P(f"  {m:%Y-%m} | {fmt(ur,'{:4.1f}')} {fmt(dur,'{:+3.0f}')} {pu:%m-%d} | {fmt(pay/1000,'{:7.0f}') if not np.isnan(pay) else '    .  '} {fmt(dpay,'{:+5.0f}')}  | {fmt(aw,'{:4.1f}')} {fmt(daw,'{:+4.1f}')} | {fmt(hs,'{:6.0f}')} {fmt(pct,'{:6.1f}')} {fmt(r3,'{:+6.1f}')} {ph:%m-%d} | {fmt(sw,'{:4.2f}')} {fmt(dsw,'{:+5.2f}')} {swpub:%m-%d} | {fmt(vac,'{:4.2f}')} | {fmt(bo,'{:6.1f}')} {bpub:%m-%d} | {fmt(um,'{:5.1f}')} | {fmt(sg,'{:5.3f}')}")
    # monthly state breadth of recovery from ETA 5159 (1971 on): share of states whose monthly initial claims stand x below own max since the open
    if E>=pd.Timestamp('1971-06-01') and E<pd.Timestamp('1986-06-01'):
        P("  ETA 5159 monthly state breadth of recovery (share of states with IC >=5%/10%/20% below own max since the open), published ~20th of the following month:")
        for k in range(-3,3):
            m=E+pd.DateOffset(months=k)
            b5,n=breadth_rec(M5159,op,m,5); b10,_=breadth_rec(M5159,op,m,10); b20,_=breadth_rec(M5159,op,m,20)
            P(f"     {m:%Y-%m}: {fmt(b5,'{:4.0f}')} {fmt(b10,'{:4.0f}')} {fmt(b20,'{:4.0f}')} ({n}) pub {m+pd.DateOffset(months=1)+pd.Timedelta(days=19):%Y-%m-%d}")
OUT.close()
