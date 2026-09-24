"""Seasonal adjustment with no look-ahead.

The factors are re-estimated once a year, at the end of December, from the data available
up to that point only, and applied unchanged for the following twelve months - which is
what a statistical agency does.  Every observation is therefore adjusted with information
that existed when it was published.
"""
import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
def woy(idx): return np.array([min(53,(t.dayofyear-1)//7+1) for t in idx])
def factors(x, passes=3):
    """seasonal factors in logs, by week of year, from the series x (log level)"""
    w=woy(x.index); seas=np.zeros(len(x))
    for p in range(passes):
        de=pd.Series(x.values-seas,index=x.index)
        span=53 if p==0 else 27
        tr=de.rolling(span,center=True,min_periods=max(6,span//3)).mean().bfill().ffill()
        r=x.values-tr.values; ns=np.zeros(len(x)); fac={}
        for k in range(1,54):
            m=(w==k)
            if m.sum(): fac[k]=float(np.mean(r[m])); ns[m]=fac[k]
        mu=np.mean(list(fac.values())); fac={k:v-mu for k,v in fac.items()}
        ns-=mu; seas=ns
    return fac
def sa_realtime(s, first_year=1991, minobs=260):
    """Returns the log level, seasonally adjusted with factors known at the time."""
    x=np.log(s.astype(float).replace(0,np.nan)).interpolate().bfill().ffill()
    out=pd.Series(index=x.index,dtype=float)
    years=sorted(set(x.index.year))
    fac=None
    for y in years:
        m=(x.index.year==y)
        if fac is None or y<first_year:
            hist=x[x.index.year<y]
            if len(hist)>=minobs: fac=factors(hist)
        else:
            hist=x[x.index.year<y]
            fac=factors(hist)
        w=woy(x.index[m])
        adj=np.array([fac.get(int(k),0.0) for k in w]) if fac else np.zeros(m.sum())
        out[m]=x.values[m]-adj
    return out.dropna()
if __name__=='__main__':
    import sys
    d=pd.read_csv('/home/claude/lab/dol/ar539.csv',low_memory=False)
    d['wk']=pd.to_datetime(d['c2'],errors='coerce'); d=d.dropna(subset=['wk'])
    d['ic']=pd.to_numeric(d['c3'],errors='coerce')
    P=d.pivot_table(index='wk',columns='st',values='ic',aggfunc='sum').sort_index()
    P=P[P.index>=pd.Timestamp('1986-02-01')]
    P=P.loc[:,P.notna().mean()>0.95]
    grid=pd.date_range(P.index.min(),P.index.max(),freq='W-SAT')
    P=P.reindex(P.index.union(grid)).interpolate(method='time').reindex(grid)
    SA=pd.DataFrame({c:sa_realtime(P[c]) for c in P.columns}).dropna(how='all')
    SA.to_csv('/home/claude/lab/dol/US_state_claims_sa_rt.csv')
    print('states, real-time SA:',SA.shape,SA.index.min().date(),SA.index.max().date())
    nat=P.sum(axis=1)
    N=sa_realtime(nat)
    pd.DataFrame({'initial claims':np.exp(N)}).to_csv('/home/claude/lab/weekly/US_nat_claims_rt.csv')
    print('national, real-time SA:',N.index.min().date(),N.index.max().date(),len(N))
