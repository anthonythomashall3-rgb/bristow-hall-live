"""A weekly United States activity panel, all public and keyless.

  initial claims, continued claims   Department of Labor ETA 539, weekly from 1986-02
  petroleum products supplied        EIA weekly supply estimates, from 1990-11
  withheld income and FICA taxes     Daily Treasury Statement, weekly sum, from 2005-10

Claims are counter-cyclical and enter negated, as the unemployment rate does in Paper 1.
Each series is seasonally adjusted by the same iterated decomposition: trend from a
centered 53-week mean, seasonal from the mean of the detrended series by week of year,
three passes.
"""
import pandas as pd, numpy as np, os
OUT='/home/claude/lab/weekly'
def woy(idx): return np.array([min(53,(t.dayofyear-1)//7+1) for t in idx])
def stl(s,passes=3):
    x=np.log(s.astype(float).replace(0,np.nan)).interpolate().dropna()
    w=woy(x.index); seas=np.zeros(len(x))
    for p in range(passes):
        de=pd.Series(x.values-seas,index=x.index)
        span=53 if p==0 else 27
        tr=de.rolling(span,center=True,min_periods=max(6,span//3)).mean().bfill().ffill()
        r=x.values-tr.values; ns=np.zeros(len(x))
        for k in range(1,54):
            m=(w==k)
            if m.sum(): ns[m]=np.mean(r[m])
        ns-=ns.mean(); seas=ns
    return pd.Series(np.exp(x.values-seas),index=x.index)
def resid(s):
    x=np.log(s); tr=x.rolling(53,center=True,min_periods=18).mean(); r=(x-tr).dropna()
    w=woy(r.index)
    return float(np.std([np.mean(r.values[w==k]) for k in range(1,54) if (w==k).sum()]))*100

C=pd.read_csv(f'{OUT}/../dol/US_weekly_claims_sa.csv',index_col=0,parse_dates=True)
P={}
P['initial claims']=C['initial_claims']
P['continued claims']=C['continued_claims']

x=pd.ExcelFile(f'{OUT}/eia_products.xls')
d=x.parse('Data 1',header=2); d.columns=['d','v']
pet=pd.Series(d['v'].values,index=pd.to_datetime(d['d'])).dropna()
P['petroleum products supplied']=stl(pet)
print(f'petroleum: seasonal {resid(pet):.2f} -> {resid(P["petroleum products supplied"]):.2f}')

t=pd.read_csv(f'{OUT}/US_daily_withheld_taxes.csv',index_col=0,parse_dates=True)['value']
wk=t.resample('W-SAT').sum()
wk=wk[wk>0]
P['withheld taxes']=stl(wk)
print(f'withheld taxes: seasonal {resid(wk):.2f} -> {resid(P["withheld taxes"]):.2f}')

# every channel onto one weekly grid, week ending Saturday, so that the composite is
# an average over the same weeks rather than over whichever channels happen to share a
# date stamp
grid=pd.date_range('1986-02-08','2026-08-29',freq='W-SAT')
al={}
for k,v in P.items():
    r=v.reindex(v.index.union(grid)).interpolate(method='time').reindex(grid)
    al[k]=r
df=pd.DataFrame(al)
df.to_csv(f'{OUT}/US_weekly_panel.csv')
for c in df.columns:
    s=df[c].dropna()
    print(f'  {c:30s} {s.index.min().date()} .. {s.index.max().date()} n={len(s)}')
