"""Construction test for leg A: the own field and the Fieldhouse field each as monthly TOTALS (Fieldhouse's form: weekly
average x weekdays/5) and as weekly AVERAGES, through the same real-time adjustment and the same diffusion (36/8, phase 5).
Isolates what the construction does from what the data do."""
import shim, sys, io, contextlib, numpy as np, pandas as pd, warnings; warnings.filterwarnings('ignore')
W=shim.W; sys.path.insert(0,W)
G={}; exec(open('/home/claude/lab/fh/build_rt.py').read().split("L=pd.read_csv(")[0],G); sa_realtime=G['sa_realtime']
import bristow_rule_v3 as B
OWN="/sessions/rcw-01xbsq1sgk1kphgfxvqjpnj7/mnt/Onset Detector Data/59_dol_weekly_state_claims_1945-1983_2026-09/own_panel/"
PK=[pd.Timestamp(x) for x in ('1948-11','1953-07','1957-08','1960-04','1969-12','1973-11','1980-01','1981-07','1990-07','2001-03','2007-12','2020-02')]
def wk(m): return np.busday_count(m.date(),(m+pd.offsets.MonthEnd(0)+pd.Timedelta(days=1)).date())/5.0
own=pd.read_csv(OWN+'OWN_state_claims_nsa_weeklyavg.csv',index_col=0,parse_dates=True)
fh=np.exp(pd.read_csv('/home/claude/lab/fh/FH_state_claims_nsa_log.csv',index_col=0,parse_dates=True))
d2=pd.read_stata('/home/claude/lab/fh/src/CBUR Data.dta'); d2['Date']=pd.to_datetime(d2['Date']).dt.to_period('M').dt.to_timestamp(); wgt=d2.groupby('Date')['MonthtoWeekWeight'].first()
def legA(P):
    parts=[]
    for ch in ('initial claims','continued weeks claimed'):
        cols=[c for c in P.columns if c.endswith('| '+ch)]; parts.append(sa_realtime(P[cols]))
    PAN=pd.concat(parts,axis=1); D=B.claims_diffusion(PAN.rolling(2).mean().dropna(how='all'),36.,8)
    return [(pd.Timestamp(p.year,p.month,20),d) for p,d in B.diffusion_peak_calls(D,phase_min=5)],D
def show(nm,calls):
    calls=[(p,d) for p,d in calls if p>=pd.Timestamp('1949-01-01')]
    hits={}; other=[]
    for p,d in calls:
        near=[i for i,t in enumerate(PK) if -6<=((d.year-t.year)*12+d.month-t.month)<=12 and d<=t+pd.DateOffset(months=12)]
        near=[i for i,t in enumerate(PK) if t-pd.DateOffset(months=6)<=d<=t+pd.DateOffset(months=12)]
        if near and near[0] not in hits: hits[near[0]]=((p-(PK[near[0]]+pd.offsets.MonthEnd(0))).days,(d.year-PK[near[0]].year)*12+d.month-PK[near[0]].month)
        elif not near: other.append(d.strftime('%Y-%m'))
    lags=[hits[i][0] if i in hits else None for i in range(12)]
    print(f"{nm:34} peaks {len(hits)}/12  lags {lags}  quiet calls {other}")
out=io.StringIO()
with contextlib.redirect_stdout(out):
    w_own=pd.Series([wk(m) for m in own.index],index=own.index)
    a,Do=legA(own); show('own, weekly averages',a)
    a,_=legA(own.mul(w_own,axis=0)); show('own, monthly totals (x weekdays/5)',a)
    a,Df=legA(fh); show('Fieldhouse, monthly totals (record)',a)
    a,_=legA(fh.div(wgt.reindex(fh.index),axis=0)); show('Fieldhouse, weekly averages (/weight)',a)
txt=out.getvalue(); print(txt); open('OWN_PANEL_VARIANTS_2026-09-05.txt','w').write(txt)
