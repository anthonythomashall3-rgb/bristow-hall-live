import pandas as pd, numpy as np
t = pd.read_csv('T10Y2Y.csv', parse_dates=['observation_date']); t.columns=['date','v']
t['v']=pd.to_numeric(t['v'],errors='coerce'); t=t.dropna().reset_index(drop=True)
# trough of the 2022-24 episode
ep=t[(t.date>='2022-07-06')&(t.date<='2024-08-26')]
print("2022-24 episode trough:", ep.loc[ep.v.idxmin(),'date'].date(), ep.v.min())
print("days at the min:", ep[ep.v==ep.v.min()].to_string(index=False))
# integrals
t['neg']=t.v<0
runs=[];start=None
for i,r in t.iterrows():
    if r.neg and start is None: start=i
    if not r.neg and start is not None:
        seg=t.v[start:i]; runs.append((t.date[start].date(),t.date[i-1].date(),i-start,seg.min(),seg.sum())); start=None
runs=sorted(runs,key=lambda x:x[4])
print("\nMost negative cumulative (sum of daily spread while inverted), top 6:")
for r in runs[:6]: print(f"  {r[0]} -> {r[1]}  n={r[2]:4d}  min={r[3]:.2f}  integral={r[4]:.1f} pp-days")
# post Aug 2024
print("\nAug-Sep 2024 detail:")
print(t[(t.date>='2024-08-20')&(t.date<='2024-09-20')].to_string(index=False))
