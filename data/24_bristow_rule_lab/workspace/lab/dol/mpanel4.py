"""Four monthly state channels from Department of Labor ETA 5159, 1971 on.

Column meanings taken from the Department's own data map for TABLE ar5159
(oui.doleta.gov/dmstree/handbooks/402/402_4/4024c6/4024c6.pdf, page 58), not inferred:

    line 101, State UI, column (1)   c1   Initial Claims, total
    line 201, State UI, column (10)  c21  Continued Weeks Claimed, intrastate
    line 301, State UI, column (14)  c38  Weeks Compensated, all weeks compensated
    line 303, State UI, column (21)  c51  First Payments, total

Initial claims and first payments are flows into unemployment; continued weeks claimed and
weeks compensated are the stock.  All four are counter-cyclical, all four are reported by
every jurisdiction every month since January 1971, and none needs a registered key.

Each channel is seasonally adjusted separately, in real time: month-of-year factors are
re-estimated each December from the data available then, on a moving seven-year window -
the span of the default 3x5 seasonal filter in X-13ARIMA-SEATS - as medians across the
years in the window, and applied unchanged for the following twelve months.  Factors are
pooled across jurisdictions until a jurisdiction has five years of its own history.
"""
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
WIN=7; OWN_YEARS=5
CH={'initial claims':'c1','continued weeks claimed':'c21',
    'weeks compensated':'c38','first payments':'c51'}
d=pd.read_csv('/home/claude/lab/dol/ar5159.csv',low_memory=False)
d['dt']=pd.to_datetime(d['rptdate'],errors='coerce'); d=d.dropna(subset=['dt'])
d['m']=d['dt'].dt.to_period('M').dt.to_timestamp()
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
        m=(X.index.year==y)
        if len(hist)<24: out.loc[m]=X.loc[m]; continue
        own,pooled=month_factors(hist)
        for c in X.columns:
            use_own=len(X[X.index.year<y][c].dropna())>=own_years*12
            adj=np.array([(own.get((c,t.month),pooled.get(t.month,0.0)) if use_own
                           else pooled.get(t.month,0.0)) for t in X.index[m]])
            out.loc[m,c]=X.loc[m,c].values-adj
    return out.dropna(how='all')
def resid(X,lo,hi):
    s=X[lo:hi]; t=s.rolling(13,center=True,min_periods=7).mean(); r=(s-t).dropna()
    f=r.groupby(r.index.month).median(); return float(f.max()-f.min())
parts=[]; nats={}
for name,col in CH.items():
    d[col]=pd.to_numeric(d[col],errors='coerce')
    P=d.dropna(subset=[col]).pivot_table(index='m',columns='st',values=col,aggfunc='sum').sort_index()
    P=P.loc[:,P.notna().mean()>0.9]
    P=P.reindex(pd.date_range(P.index.min(),P.index.max(),freq='MS')).interpolate()
    SA=sa_realtime(P); parts.append(SA.add_suffix(' | '+name))
    N=sa_realtime(pd.DataFrame({'US':P.sum(axis=1)}))['US']; nats[name]=np.exp(N)
    print(f'{name:26s} {col:4s} {SA.shape}  {SA.index.min().date()}..{SA.index.max().date()}  '
          f'residual seasonality whole {resid(N*100,"1973-01","2026-07"):4.1f}  2015-26 {resid(N*100,"2015-01","2026-07"):4.1f}')
PAN=pd.concat(parts,axis=1)
PAN.to_csv('/home/claude/lab/dol/US_state_monthly_4ch_sa.csv')
pd.DataFrame(nats).to_csv('/home/claude/lab/dol/US_nat_monthly_4ch_sa.csv')
print('panel',PAN.shape,PAN.index.min().date(),PAN.index.max().date())
