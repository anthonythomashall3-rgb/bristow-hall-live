"""The month-of-year factors were estimated on the whole history to date.  The seasonal
pattern in state claims has moved a great deal since the 1970s, so factors estimated that
way are an average of two different calendars and leave a large residual: 30.7 log points
of month-of-year pattern in the seasonally adjusted national series over 2015-2026 against
5.5 over 1973-1990.

Fixed by estimating the factors on a MOVING WINDOW of the most recent `win` years, which
is what a statistical agency's moving seasonal filter does, and by taking the median rather
than the mean across years so a recession inside the window does not tilt the factor.  The
estimate still ends at the December before the year being adjusted; no observation is
adjusted with information that did not exist when it was published.
"""
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
d=pd.read_csv('/home/claude/lab/dol/ar5159.csv',low_memory=False)
d['dt']=pd.to_datetime(d['rptdate'],errors='coerce'); d['ic']=pd.to_numeric(d['c1'],errors='coerce')
d=d.dropna(subset=['dt','ic']); d['m']=d['dt'].dt.to_period('M').dt.to_timestamp()
P=d.pivot_table(index='m',columns='st',values='ic',aggfunc='sum').sort_index()
P=P.loc[:,P.notna().mean()>0.9]
P=P.reindex(pd.date_range(P.index.min(),P.index.max(),freq='MS')).interpolate()

def month_factors(X):
    T=X.rolling(13,center=True,min_periods=7).mean()
    R=X-T
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

def sa_realtime(P, own_years=5, win=None):
    X=np.log(P.replace(0,np.nan)).interpolate().bfill()
    out=pd.DataFrame(index=X.index,columns=X.columns,dtype=float)
    for y in sorted(set(X.index.year)):
        hist=X[X.index.year<y]
        if win is not None: hist=hist[hist.index.year>=y-win]
        if len(hist)<24:
            out.loc[X.index.year==y]=X.loc[X.index.year==y]; continue
        own,pooled=month_factors(hist)
        m=(X.index.year==y)
        for c in X.columns:
            hv=hist[c].dropna()
            use_own=len(hv)>=own_years*12
            adj=np.array([(own.get((c,t.month),pooled.get(t.month,0.0)) if use_own
                           else pooled.get(t.month,0.0)) for t in X.index[m]])
            out.loc[m,c]=X.loc[m,c].values-adj
    return out.dropna(how='all')

def resid(X,lo,hi):
    s=X[lo:hi]; t=s.rolling(13,center=True,min_periods=7).mean(); r=(s-t).dropna()
    f=r.groupby(r.index.month).median(); return float(f.max()-f.min())
nat=pd.DataFrame({'US':P.sum(axis=1)})
print(' win   whole   1973-90   1991-2010   2015-26')
for win in [None,5,6,7,8]:
    N=sa_realtime(nat,win=win)['US']*100.0
    print(f'{str(win):>5}  {resid(N,"1973-01","2026-07"):6.1f}  {resid(N,"1973-01","1990-12"):8.1f}'
          f'  {resid(N,"1991-01","2010-12"):10.1f}  {resid(N,"2015-01","2026-07"):8.1f}')
