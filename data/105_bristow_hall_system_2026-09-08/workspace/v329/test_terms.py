# The search week on labour terms beside "unemployment": the stitched history 2004-2026 (search_week.py's method), the
# sudden stop's own numbers (7-day mean 35 per cent over the base - the 28-day mean's 365-day low or 0.85 x its five-year
# median; the S&P 500 20 per cent under its 20-day high at the close of the day the datum is known), every fire with and
# without the gate, and the readings of 6-17 March 2020. Run: python3 test_terms.py <tag> [<tag> ...]
import os,sys,glob
import pandas as pd, numpy as np
os.chdir(os.path.dirname(os.path.abspath(__file__)))
ALPHA=0.85; EPS=1e-9
SPX=pd.read_csv('../spx_daily_2004_2026.csv',index_col=0,parse_dates=True).iloc[:,0].astype(float)
crash=(1-SPX/SPX.rolling(20,min_periods=10).max())*100
REC=[('2007-12','2009-06'),('2020-02','2020-04'),('2024-05','2024-09')]   # NBER peaks/troughs; 2024 the rule's own
def inwin(d):
    return any(pd.Timestamp(a+'-01')-pd.DateOffset(months=6)<=d<=pd.Timestamp(b+'-01')+pd.offsets.MonthEnd(0) for a,b in REC)
def stitch(tag):
    W={}
    for f in sorted(glob.glob(f'{tag}/{tag}_weekly_*.csv')): W[f]=pd.read_csv(f,index_col=0,parse_dates=True).iloc[:,0].astype(float)
    keys=sorted(W); base=[k for k in keys if W[k].index.min()<=pd.Timestamp('2020-03-01')<=W[k].index.max()][0]; S={base:1.0}
    for k in keys[keys.index(base)+1:]:
        prev=[p for p in keys if p<k][-1]; o=W[k].index.intersection(W[prev].index); S[k]=S[prev]*(W[prev].loc[o].mean()/max(W[k].loc[o].mean(),1e-9)) if len(o) else S[prev]
    for k in reversed(keys[:keys.index(base)]):
        nxt=[p for p in keys if p>k][0]; o=W[k].index.intersection(W[nxt].index); S[k]=S[nxt]*(W[nxt].loc[o].mean()/max(W[k].loc[o].mean(),1e-9)) if len(o) else S[nxt]
    wk=pd.concat([W[k]*S[k] for k in keys]); wk=wk[~wk.index.duplicated(keep='last')].sort_index()
    D=[]
    for f in sorted(glob.glob(f'{tag}/{tag}_daily_*.csv')):
        d=pd.read_csv(f,index_col=0,parse_dates=True).iloc[:,0].astype(float); ws=d.resample('W-SAT').mean(); ws.index=ws.index-pd.Timedelta(days=6); o=ws.index.intersection(wk.index)
        fac=(wk.loc[o].mean()/max(ws.loc[o].mean(),1e-9)) if len(o) and ws.loc[o].mean()>0 else np.nan; D.append(d*fac)
    day=pd.concat(D); return day[~day.index.duplicated(keep='last')].sort_index().dropna()
def base_daily(s):
    m=s.rolling(28,min_periods=20).mean(); lo=m.rolling(365,min_periods=300).min().shift(1); med=m.rolling(5*365,min_periods=3*365).median().shift(1); return np.fmax(lo,ALPHA*med)
for tag in sys.argv[1:]:
    day=stitch(tag); g7=day.rolling(7,min_periods=7).mean(); rel=((g7/base_daily(g7)-1)*100).dropna()
    day.to_csv(f'{tag}/{tag}_stitched_daily.csv',header=[tag])
    alone=[]; gated=[]; armed=True; armed2=True
    for t,v in rel.items():
        d=t+pd.Timedelta(days=1)
        if armed and v>=35-EPS: alone.append(d); armed=False
        elif not armed and v<=EPS: armed=True
        if armed2 and v>=35-EPS:
            c=crash[crash.index<=d]
            if len(c) and c.index[-1]==d and float(c.iloc[-1])>=20-EPS: gated.append(d); armed2=False
        elif not armed2 and v<=EPS: armed2=True
    print(f'== {tag}: stitched {day.index.min().date()}..{day.index.max().date()}, {len(day)} days; readings from {rel.index.min().date()}')
    print('   alone (35, no gate): fires',len(alone),'| outside a recession window:',[d.date().isoformat() for d in alone if not inwin(d)])
    print('   with the gate (35/20): fires',[d.date().isoformat() for d in gated],'| outside a window:',[d.date().isoformat() for d in gated if not inwin(d)])
    print('   March 2020, datum day -> reading (known next morning):',{t.strftime('%m-%d'):round(float(v),1) for t,v in rel['2020-03-05':'2020-03-17'].items()})
    print('   base on 2020-03-11:',round(float(base_daily(g7)['2020-03-11']),2),'7-day mean:',round(float(g7['2020-03-11']),2))
