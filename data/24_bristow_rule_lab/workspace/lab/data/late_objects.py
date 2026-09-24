"""Objects whose history begins after 1967 (no disturbance readable): the nowcast and sentiment series Anthony asked about
(GDPNow real-time 2011-, the SF Fed news sentiment 1980-, the policy-uncertainty index 1985-, the NY Fed nowcast 2001-).
For each object and sign: the recessions its history covers, the LINE = the weakest recession's reach inside the route's window
(so every covered recession is confirmed within 30 days of its claims call), and the WINDOW EXPOSURE at that line (share of
quiet observations on which a claims call would be wrongly confirmed) - Rule 21's two risks, read directly.  Output late_objects.log."""
import sys, warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
PEAKS=['1948-11','1953-07','1957-08','1960-04','1969-12','1973-11','1980-01','1981-07','1990-07','2001-03','2007-12','2020-02','2023-07']
TROUGHS=['1949-10','1954-05','1958-04','1961-02','1970-11','1975-03','1980-07','1982-11','1991-03','2001-11','2009-06','2020-04','2024-08']
CALLS=[('1970-01-31','1969-12'),('1974-02-16','1973-11'),('1980-03-20','1980-01'),('1981-12-20','1981-07'),('1990-09-20','1990-07'),('2001-03-31','2001-03'),('2007-12-28','2007-12'),('2020-03-28','2020-02'),('2023-08-28','2023-07')]
M=lambda s: pd.Timestamp(s+'-01')
FILES={'SF Fed news sentiment (daily 1980-)':('other_daily/sffed_dnsi.csv',21),'policy uncertainty EPU (daily 1985-)':('other_daily/epu_daily.csv',21),
       'GDPNow real-time (2011-)':('other_daily/gdpnow_realtime.csv',21),'NY Fed nowcast, current quarter (weekly 2001-)':('other_weekly/nyfed_nowcast_current_quarter.csv',4),
       'ADS index (daily 1960-, current vintage)':('other_daily/ads_index_current.csv',21),'OFR FSI (daily 2000-)':('other_daily/ofr_fsi.csv',21)}
def objs(x,per):
    W={m:int(round(per*m)) for m in (1,3,6,12)}; out={'level':x,'lvl-mean12m':x-x.rolling(W[12],min_periods=int(W[12]*.8)).mean()}
    for m,w in W.items(): out[f'chg{m}m']=x-x.shift(w)
    return out
def quiet(idx):
    q=pd.Series(True,index=idx)
    for p,t in zip(PEAKS,TROUGHS): q[(idx>=M(p)-pd.DateOffset(months=9))&(idx<=M(t)+pd.DateOffset(months=18))]=False
    return q
log=open('late_objects.log','w')
def P(*a): print(*a); print(*a,file=log)
P('object | sign | recessions covered | line (weakest recession reach in [call-6m, call+30d]) | window exposure on quiet days')
for name,(f,per) in FILES.items():
    df=pd.read_csv(f,index_col=0,parse_dates=True); 
    for col in df.columns:
        x=pd.to_numeric(df[col],errors='coerce').dropna()
        if len(x)<300: continue
        for oname,o in objs(x,per).items():
            o=o.dropna()
            for sign in (1,-1):
                s=sign*o; reads=[]
                for day,pk in CALLS:
                    d=pd.Timestamp(day)
                    if s.index[0]>d-pd.DateOffset(months=6): continue
                    seg=s[d-pd.DateOffset(months=6):d+pd.Timedelta(days=30)]
                    if len(seg): reads.append((pk,float(seg.max())))
                if len(reads)<2: continue
                line=min(v for _,v in reads); q=quiet(s.index); hit=(s>=line)
                fwd=hit[::-1].rolling(per,min_periods=1).max()[::-1].astype(bool); back=hit.rolling(6*per+1,min_periods=1).max().astype(bool)
                expo=float((fwd|back)[q].mean()*100) if q.sum() else float('nan'); at=float(hit[q].mean()*100)
                P(f'{name} [{col}] {oname:12s} sign {sign:+d} | {len(reads)} rec ({reads[0][0]}-{reads[-1][0]}) | line {line:9.3f} | at the line {at:5.1f}%  confirmed inside the window {expo:5.1f}%')
log.close()
