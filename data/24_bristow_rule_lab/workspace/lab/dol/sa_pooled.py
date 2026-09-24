"""Weekly seasonal adjustment with no look-ahead and a pooled warm-up.

Every state shares the calendar, so the week-of-year pattern can be estimated from all
fifty-three at once.  One year of fifty-three states carries as much information about the
calendar as fifty-three years of one state.  The factors are therefore POOLED across
states until a state has `own_years` of its own history, and state-specific after that.
Re-estimated each December from the data available then; applied unchanged for the year.
No observation is adjusted with information that did not exist when it was published.
"""
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
def woy(idx): return np.array([min(53,(t.dayofyear-1)//7+1) for t in idx])
def _fac(X, passes=3):
    """X: DataFrame of log levels, weekly.  Returns (own {(col,week):f}, pooled {week:f})."""
    seas=pd.DataFrame(0.0,index=X.index,columns=X.columns)
    w=woy(X.index)
    for p in range(passes):
        de=X-seas
        span=53 if p==0 else 27
        tr=de.rolling(span,center=True,min_periods=max(6,span//3)).mean().bfill().ffill()
        R=X-tr
        own={}; pooled={}
        NS=np.zeros(X.shape)
        cols=list(X.columns)
        for k in range(1,54):
            m=(w==k)
            if not m.any(): continue
            pooled[k]=float(np.nanmean(R.values[m]))
            row=np.empty(len(cols))
            for ci,c in enumerate(cols):
                v=R[c].values[m]; v=v[np.isfinite(v)]
                if len(v)>=3: own[(c,k)]=float(v.mean())
                row[ci]=own.get((c,k),pooled[k])
            NS[m,:]=row
        mu=np.nanmean(list(pooled.values())); pooled={k:v-mu for k,v in pooled.items()}
        own={k:v-mu for k,v in own.items()}
        seas=pd.DataFrame(NS-mu,index=X.index,columns=X.columns)
    return own,pooled
def sa_pooled(P, own_years=5):
    X=np.log(P.replace(0,np.nan)).interpolate().bfill().ffill()
    out=pd.DataFrame(index=X.index,columns=X.columns,dtype=float)
    for y in sorted(set(X.index.year)):
        hist=X[X.index.year<y]
        m=(X.index.year==y)
        if len(hist)<40:
            out.loc[m]=X.loc[m]; continue
        own,pooled=_fac(hist)
        w=woy(X.index[m])
        for c in X.columns:
            enough=hist[c].notna().sum()>=own_years*52
            adj=np.array([(own.get((c,int(k)),pooled.get(int(k),0.0)) if enough
                           else pooled.get(int(k),0.0)) for k in w])
            out.loc[m,c]=X.loc[m,c].values-adj
    return out.dropna(how='all')
if __name__=='__main__':
    d=pd.read_csv('/home/claude/lab/dol/ar539.csv',low_memory=False)
    d['wk']=pd.to_datetime(d['c2'],errors='coerce'); d=d.dropna(subset=['wk'])
    d['ic']=pd.to_numeric(d['c3'],errors='coerce')
    P=d.pivot_table(index='wk',columns='st',values='ic',aggfunc='sum').sort_index()
    P=P[P.index>=pd.Timestamp('1986-02-01')]
    P=P.loc[:,P.notna().mean()>0.95]
    grid=pd.date_range(P.index.min(),P.index.max(),freq='W-SAT')
    P=P.reindex(P.index.union(grid)).interpolate(method='time').reindex(grid)
    SA=sa_pooled(P)
    SA.to_csv('/home/claude/lab/dol/US_state_claims_sa_pooled.csv')
    print('pooled-warm-up state SA:',SA.shape,SA.index.min().date(),SA.index.max().date())
    N=sa_pooled(pd.DataFrame({'US':P.sum(axis=1)}))['US']
    pd.DataFrame({'initial claims':np.exp(N)}).to_csv('/home/claude/lab/weekly/US_nat_claims_pooled.csv')
    print('national:',N.index.min().date(),N.index.max().date(),len(N))
