"""National weekly claims, seasonally adjusted by an iterated STL-style decomposition.

log(claims) = trend + seasonal + irregular.  Trend from a centered 53-week mean, seasonal
from the mean of the detrended series by week of year, iterated three times with a shorter
trend smoother on the deseasonalized series.  Residual seasonality is reported.
"""
import pandas as pd, numpy as np
d=pd.read_csv('/home/claude/lab/dol/ar539.csv',low_memory=False)
d['wk']=pd.to_datetime(d['c2'],errors='coerce'); d=d.dropna(subset=['wk'])
for c in ('c3','c8'): d[c]=pd.to_numeric(d[c],errors='coerce')
g=d.groupby('wk')[['c3','c8']].sum().sort_index()
nst=d.groupby('wk')['st'].nunique()
g=g[nst.reindex(g.index)>=50]
g=g[g.index>=pd.Timestamp('1986-01-01')]

def woy(idx):
    """Week of year by position, 1..53, robust to ISO year boundaries."""
    return np.array([min(53,(t.dayofyear-1)//7+1) for t in idx])

def stl(s, passes=3):
    x=np.log(s.astype(float).replace(0,np.nan)).interpolate()
    w=woy(x.index); seas=np.zeros(len(x))
    for p in range(passes):
        de=pd.Series(x.values-seas,index=x.index)
        span=53 if p==0 else 27
        tr=de.rolling(span,center=True,min_periods=span//3).mean()
        tr=tr.bfill().ffill()
        r=x.values-tr.values
        newseas=np.zeros(len(x))
        for k in range(1,54):
            m=(w==k)
            if m.sum(): newseas[m]=np.mean(r[m])
        newseas-=newseas.mean()
        seas=newseas
    sa=np.exp(x.values-seas)
    return pd.Series(sa,index=x.index)

def resid_seas(s):
    x=np.log(s)
    tr=x.rolling(53,center=True,min_periods=18).mean()
    r=(x-tr).dropna()
    w=woy(r.index)
    m=[np.mean(r.values[w==k]) for k in range(1,54) if (w==k).sum()]
    return float(np.std(m))*100

out=pd.DataFrame(index=g.index)
for src,name in (('c3','initial_claims'),('c8','continued_claims')):
    raw=g[src]
    sa=stl(raw)
    out[name]=sa
    print(f'{name}: seasonal amplitude before {resid_seas(raw):.2f} log pts, after {resid_seas(sa):.2f}')
out.to_csv('/home/claude/lab/dol/US_weekly_claims_sa.csv')
K=(np.log(out['initial_claims'].rolling(4).mean())*100).dropna()
S=K-K.rolling(104,min_periods=52).min()
print('S percentiles', np.nanpercentile(S.dropna(),[50,75,90,95,99]).round(1))
print(out.tail(3).round(0).to_string())
