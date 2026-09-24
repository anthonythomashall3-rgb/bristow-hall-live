"""National weekly claims from the Department of Labor's ETA 539 report (no key).
Layout: c2 = week ending, c3 = state initial claims, c8 = continued weeks claimed.
National = sum over the 53 reporting jurisdictions.  Seasonally adjusted here by
ratio to a centered 52-week moving average, by week of year, since the published
national seasonal factors are not in this file."""
import pandas as pd, numpy as np
d=pd.read_csv('/home/claude/lab/dol/ar539.csv',low_memory=False)
d['wk']=pd.to_datetime(d['c2'],errors='coerce')
d=d.dropna(subset=['wk'])
for c in ('c3','c8'):
    d[c]=pd.to_numeric(d[c],errors='coerce')
g=d.groupby('wk')[['c3','c8']].sum().sort_index()
g=g[g.index>=pd.Timestamp('1986-01-01')]
n=d.groupby('wk')['st'].nunique()
g=g[n.reindex(g.index)>=50]                      # drop weeks with missing states
print('weeks',len(g), g.index.min().date(), g.index.max().date())

def sa_weekly(s):
    """Ratio to a centered 52-week moving average, averaged by week of year."""
    x=np.log(s.astype(float).replace(0,np.nan)).dropna()
    tr=x.rolling(53,center=True,min_periods=27).mean()
    r=(x-tr).dropna()
    woy=r.index.isocalendar().week.values
    fac={}
    for w in range(1,54):
        v=r.values[woy==w]
        if len(v): fac[w]=float(np.mean(v))
    m=np.mean(list(fac.values()))
    fac={k:v-m for k,v in fac.items()}
    w_all=x.index.isocalendar().week.values
    adj=np.array([fac.get(int(w),0.0) for w in w_all])
    return np.exp(x.values-adj)

out=pd.DataFrame(index=g.index)
out['initial_claims']=sa_weekly(g['c3'])
out['continued_claims']=sa_weekly(g['c8'])
out.to_csv('/home/claude/lab/dol/US_weekly_claims_sa.csv')
print(out.tail(3).round(0).to_string())
print('4-week MA of initial claims, 2020:')
print(out['initial_claims'].rolling(4).mean()['2020-01':'2020-08'].round(0).to_string())
