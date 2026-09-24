import pandas as pd, numpy as np
t = pd.read_csv('T10Y2Y.csv', parse_dates=['observation_date'])
t.columns=['date','v']
t['v']=pd.to_numeric(t['v'],errors='coerce')
t=t.dropna().reset_index(drop=True)
print("T10Y2Y span:", t.date.min().date(), "->", t.date.max().date(), "obs:", len(t))
# find runs below zero
t['neg']=t.v<0
runs=[]
start=None
for i,r in t.iterrows():
    if r.neg and start is None: start=i
    if not r.neg and start is not None:
        runs.append((t.date[start].date(), t.date[i-1].date(), i-start, t.v[start:i].min()))
        start=None
if start is not None:
    runs.append((t.date[start].date(), t.date[len(t)-1].date(), len(t)-start, t.v[start:].min()))
runs=sorted(runs,key=lambda x:-x[2])
print("\nLongest consecutive-trading-day runs below zero:")
for r in runs[:10]: print(f"  {r[0]} -> {r[1]}  {r[2]} trading days  min={r[3]:.2f}")
print("\nDeepest trough overall:", t.loc[t.v.idxmin(),'date'].date(), t.v.min())
# 2022 detail
sub=t[(t.date>='2022-03-25')&(t.date<='2022-07-15')]
print("\n2022 spring detail:")
print(sub.to_string(index=False))
