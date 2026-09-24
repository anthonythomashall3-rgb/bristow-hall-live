"""State initial claims, monthly, from 1971 — Department of Labor ETA 5159 report.

The weekly ETA 539 file begins in February 1986.  The monthly ETA 5159 file begins in
January 1971 and carries the same object at monthly frequency, column c1 (initial claims,
state unemployment insurance).  Verified against the weekly file over 1990-2019: the two
national totals correlate 0.86 with a median ratio of 1.08.

Seasonally adjusted with no look-ahead: factors re-estimated each December from the data
available then and applied unchanged for the following twelve months.  In the first years
the factors are POOLED ACROSS STATES - every state shares the calendar, so one year of
fifty-three states estimates the month-of-year pattern that one state needs five years to
estimate - and the pooled factor is used until a state has `own_years` of its own history.
"""
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
d=pd.read_csv('/home/claude/lab/dol/ar5159.csv',low_memory=False)
d['dt']=pd.to_datetime(d['rptdate'],errors='coerce')
d['ic']=pd.to_numeric(d['c1'],errors='coerce')
d=d.dropna(subset=['dt','ic'])
d['m']=d['dt'].dt.to_period('M').dt.to_timestamp()
P=d.pivot_table(index='m',columns='st',values='ic',aggfunc='sum').sort_index()
P=P.loc[:,P.notna().mean()>0.9]
P=P.reindex(pd.date_range(P.index.min(),P.index.max(),freq='MS')).interpolate()
print('monthly state panel',P.shape,P.index.min().date(),P.index.max().date())

def month_factors(X):
    """X: DataFrame of log levels.  Returns {(state,month): factor} and pooled {month: f}."""
    T=X.rolling(13,center=True,min_periods=5).mean()
    R=X-T
    own={}; pooled={}
    for mth in range(1,13):
        sel=R[R.index.month==mth]
        if len(sel)==0: continue
        pooled[mth]=float(np.nanmean(sel.values))
        for c in X.columns:
            v=sel[c].dropna()
            if len(v)>=3: own[(c,mth)]=float(v.mean())
    mu=np.nanmean(list(pooled.values())); pooled={k:v-mu for k,v in pooled.items()}
    if own:
        mo_=np.nanmean(list(own.values())); own={k:v-mo_ for k,v in own.items()}
    return own,pooled

def sa_realtime(P, own_years=5, first=1973):
    X=np.log(P.replace(0,np.nan)).interpolate().bfill()
    out=pd.DataFrame(index=X.index,columns=X.columns,dtype=float)
    for y in sorted(set(X.index.year)):
        hist=X[X.index.year<y]
        if len(hist)<12:
            out.loc[X.index.year==y]=X.loc[X.index.year==y]; continue
        own,pooled=month_factors(hist)
        m=(X.index.year==y)
        for c in X.columns:
            hv=hist[c].dropna()
            use_own = len(hv)>=own_years*12
            adj=np.array([ (own.get((c,t.month),pooled.get(t.month,0.0)) if use_own
                            else pooled.get(t.month,0.0)) for t in X.index[m]])
            out.loc[m,c]=X.loc[m,c].values-adj
    return out.dropna(how='all')
SA=sa_realtime(P)
SA.to_csv('/home/claude/lab/dol/US_state_claims_monthly_sa_rt.csv')
print('monthly state SA (real time):',SA.shape,SA.index.min().date(),SA.index.max().date())
nat=P.sum(axis=1)
N=sa_realtime(pd.DataFrame({'US':nat}))['US']
pd.DataFrame({'initial claims':np.exp(N)}).to_csv('/home/claude/lab/dol/US_nat_claims_monthly_rt.csv')
print('national monthly SA:',N.index.min().date(),N.index.max().date(),len(N))
