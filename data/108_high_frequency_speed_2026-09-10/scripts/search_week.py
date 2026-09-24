# search_week.py - THE SEARCH WEEK: a daily labour datum for the sudden stop (collection 108, 10 September 2026). Google
# searches in the United States (Google Trends, daily from 2004), stitched from the daily half-year windows onto the weekly
# four-year windows (each normalized on its own; chained onto the window that holds March 2020). The datum is the seven-day
# mean of the daily index - one week, as the sudden stop reads one week of claims - over the same base as claims (the 28-day
# mean's 365-day low, or 0.85 of its five-year median where higher), 35 per cent over it; a day's index is known the next
# morning; the market gate is the S&P 500 at THAT day's close, 20 per cent under its 20-day high (a datum published
# overnight is read at the close of the day it is known). The sudden stop's labour datum is the earlier of the claims week
# and the search week. The series is a reconstruction (Google re-normalizes each download; the ratios within a window are
# scale-free) and is declared a bound, as the vacancy rate before 2010 is.
# FROM v3.29 (walk55, the evening of 10 September 2026) THE SEARCH WEEK READS SEVERAL LABOUR TERMS, each over its own base,
# and the sudden stop fires on the earliest of them: "unemployment" (tag unemp), "layoffs" (layoffs) and "laid off"
# (laidoff). The terms are named by SEARCH_TERMS (a global set by the walk before this file runs, or the environment
# variable BHS_SEARCH_TERMS, comma-separated); with neither, the v3.27 object - "unemployment" alone - is read. The first
# term's series keep the names GT_DAY, GT7 and GT_REL (the site's readings row); GT_TERMS holds every term's reading.
import os,glob
import pandas as pd, numpy as np
_C108=os.path.expanduser('~/Projects/Onset Detector Data/108_high_frequency_speed_2026-09-10')
SEARCH_TERMS=list(globals().get('SEARCH_TERMS') or [t for t in os.environ.get('BHS_SEARCH_TERMS','').split(',') if t] or ['unemp'])
def _stitch(tag='unemp'):
    W={}
    for f in sorted(glob.glob(os.path.join(_C108,'google_trends',f'{tag}_weekly_*.csv'))): W[f]=pd.read_csv(f,index_col=0,parse_dates=True).iloc[:,0].astype(float)
    keys=sorted(W); base=[k for k in keys if W[k].index.min()<=pd.Timestamp('2020-03-01')<=W[k].index.max()][0]; S={base:1.0}
    for k in keys[keys.index(base)+1:]:
        prev=[p for p in keys if p<k][-1]; o=W[k].index.intersection(W[prev].index); S[k]=S[prev]*(W[prev].loc[o].mean()/max(W[k].loc[o].mean(),1e-9)) if len(o) else S[prev]
    for k in reversed(keys[:keys.index(base)]):
        nxt=[p for p in keys if p>k][0]; o=W[k].index.intersection(W[nxt].index); S[k]=S[nxt]*(W[nxt].loc[o].mean()/max(W[k].loc[o].mean(),1e-9)) if len(o) else S[nxt]
    wk=pd.concat([W[k]*S[k] for k in keys]); wk=wk[~wk.index.duplicated(keep='last')].sort_index()
    D=[]
    for f in sorted(glob.glob(os.path.join(_C108,'google_trends',f'{tag}_daily_*.csv'))):
        d=pd.read_csv(f,index_col=0,parse_dates=True).iloc[:,0].astype(float); ws=d.resample('W-SAT').mean(); ws.index=ws.index-pd.Timedelta(days=6); o=ws.index.intersection(wk.index)
        fac=(wk.loc[o].mean()/max(ws.loc[o].mean(),1e-9)) if len(o) and ws.loc[o].mean()>0 else np.nan; D.append(d*fac)
    day=pd.concat(D); return day[~day.index.duplicated(keep='last')].sort_index().dropna()
def _base_daily(s):
    m=s.rolling(28,min_periods=20).mean(); lo=m.rolling(365,min_periods=300).min().shift(1); med=m.rolling(5*365,min_periods=3*365).median().shift(1); return np.fmax(lo,ALPHA*med)
def _load(tag):
    live=os.path.join(_C108,'google_trends','live',f'{tag}_stitched_daily.csv')
    if os.path.exists(live): day=pd.read_csv(live,index_col=0,parse_dates=True).iloc[:,0].astype(float).sort_index()   # the stitched history, extended daily by 108/scripts/trends_live.py
    else:
        day=_stitch(tag); os.makedirs(os.path.dirname(live),exist_ok=True); day.to_csv(live,header=[tag])
    g7=day.rolling(7,min_periods=7).mean(); return day,g7,((g7/_base_daily(g7)-1)*100).dropna()
GT_TERMS={}
for _tag in SEARCH_TERMS: GT_TERMS[_tag]=_load(_tag)
GT_DAY,GT7,GT_REL=GT_TERMS[SEARCH_TERMS[0]]
_SPXd2=_SPX.copy(); _crash2=(1-_SPXd2/_SPXd2.rolling(20,min_periods=10).max())*100
def leg_K_search_one(rel,pct,cl):
    """one term: the search week pct per cent over its base, known the next morning, with the S&P at that day's close cl under its 20-day high"""
    c=[]; armed=True
    for t,v in rel.items():
        day=t+pd.Timedelta(days=1)
        if armed and v>=pct-EPS:
            cs=_crash2[_crash2.index<=day]
            if len(cs) and cs.index[-1]==day and float(cs.iloc[-1])>=cl-EPS: c.append((day,pd.Timestamp(day.year,day.month,1))); armed=False
        elif not armed and v<=EPS: armed=True
    return c
def leg_K_search(pct,cl):
    """every term, each armed on its own; the earliest proposal per month"""
    out={}
    for tag,(_d,_g,rel) in GT_TERMS.items():
        for d,m in leg_K_search_one(rel,pct,cl):
            if m not in out or d<out[m]: out[m]=d
    return sorted((d,m) for m,d in out.items())
_leg_K_claims=leg_K_x
def leg_K_x(s,pct,cl,look=52):
    """the sudden stop on the earlier of the claims week and the search weeks (one proposal per month)"""
    out={}
    for d,m in _leg_K_claims(s,pct,cl,look)+leg_K_search(pct,cl):
        if m not in out or d<out[m]: out[m]=d
    return sorted((d,m) for m,d in out.items())
