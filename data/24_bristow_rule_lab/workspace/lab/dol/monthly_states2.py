"""State initial claims, monthly, from 1971 - Department of Labor ETA 5159, column c1.

Seasonally adjusted with no look-ahead: the month-of-year factors are re-estimated each
December from the data available then and applied unchanged for the following twelve
months.  Two things differ from the first build.  The factors are estimated on a MOVING
SEVEN-YEAR WINDOW rather than on the whole history to date, which is the span of the
default 3x5 seasonal filter in X-13ARIMA-SEATS; and they are medians rather than means
across the years in the window, so a recession inside the window does not tilt them.  The
whole-history version left 10.4 log points of month-of-year pattern in the adjusted
national series, and 18.8 log points over 2015-2026, because the seasonal calendar of
state claims has moved since the 1970s and one fixed average fits neither end.  The moving
window leaves 4.5 and 6.9.

In a state's first years the factors are POOLED ACROSS STATES - every state shares the
calendar - and become state-specific once the state has five years of its own history.
"""
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
WIN=7; OWN_YEARS=5
d=pd.read_csv('/home/claude/lab/dol/ar5159.csv',low_memory=False)
d['dt']=pd.to_datetime(d['rptdate'],errors='coerce'); d['ic']=pd.to_numeric(d['c1'],errors='coerce')
d=d.dropna(subset=['dt','ic']); d['m']=d['dt'].dt.to_period('M').dt.to_timestamp()
P=d.pivot_table(index='m',columns='st',values='ic',aggfunc='sum').sort_index()
P=P.loc[:,P.notna().mean()>0.9]
P=P.reindex(pd.date_range(P.index.min(),P.index.max(),freq='MS')).interpolate()
print('monthly state panel',P.shape,P.index.min().date(),P.index.max().date())

def month_factors(X):
    R=X-X.rolling(13,center=True,min_periods=7).mean()
    own={}; pooled={}
    for mth in range(1,13):
        sel=R[R.index.month==mth]
        if len(sel)==0: continue
        v=sel.values[~np.isnan(sel.values)]
        if len(v): pooled[mth]=float(np.median(v))
        for c in X.columns:
            q=sel[c].dropna()
            if len(q)>=3: own[(c,mth)]=float(np.median(q))
    if pooled:
        mu=np.median(list(pooled.values())); pooled={k:v-mu for k,v in pooled.items()}
    if own:
        mo_=np.median(list(own.values())); own={k:v-mo_ for k,v in own.items()}
    return own,pooled

def sa_realtime(P,own_years=OWN_YEARS,win=WIN):
    X=np.log(P.replace(0,np.nan)).interpolate().bfill()
    out=pd.DataFrame(index=X.index,columns=X.columns,dtype=float)
    for y in sorted(set(X.index.year)):
        hist=X[(X.index.year<y)&(X.index.year>=y-win)]
        if len(hist)<24:
            out.loc[X.index.year==y]=X.loc[X.index.year==y]; continue
        own,pooled=month_factors(hist)
        m=(X.index.year==y)
        for c in X.columns:
            use_own=len(X[X.index.year<y][c].dropna())>=own_years*12
            adj=np.array([(own.get((c,t.month),pooled.get(t.month,0.0)) if use_own
                           else pooled.get(t.month,0.0)) for t in X.index[m]])
            out.loc[m,c]=X.loc[m,c].values-adj
    return out.dropna(how='all')

SA=sa_realtime(P)
SA.to_csv('/home/claude/lab/dol/US_state_claims_monthly_sa_rt.csv')
print('monthly state SA (real time, 7-year moving factors):',SA.shape,SA.index.min().date(),SA.index.max().date())
N=sa_realtime(pd.DataFrame({'US':P.sum(axis=1)}))['US']
pd.DataFrame({'initial claims':np.exp(N)}).to_csv('/home/claude/lab/dol/US_nat_claims_monthly_rt.csv')
def resid(X,lo,hi):
    s=X[lo:hi]; t=s.rolling(13,center=True,min_periods=7).mean(); r=(s-t).dropna()
    f=r.groupby(r.index.month).median(); return float(f.max()-f.min())
X=N*100.0
print(f'residual month-of-year in the adjusted national series: whole {resid(X,"1973-01","2026-07"):.1f}, '
      f'1973-1990 {resid(X,"1973-01","1990-12"):.1f}, 2015-2026 {resid(X,"2015-01","2026-07"):.1f} log points')
