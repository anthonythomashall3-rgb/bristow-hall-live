import pandas as pd, numpy as np
f=pd.read_csv('FEDFUNDS.csv',parse_dates=['observation_date']); f.columns=['date','v']; f=f.set_index('date')
print("FEDFUNDS 2021-12..2026-07:"); print(f.loc['2021-12':'2026-07'].T.to_string())
w=pd.read_csv('WALCL.csv',parse_dates=['observation_date']); w.columns=['date','v']; w['v']=pd.to_numeric(w.v,errors='coerce')
w2=w[(w.date>='2022-01-01')&(w.date<='2022-08-01')]
print("\nWALCL peak overall:", w.loc[w.v.idxmax(),'date'].date(), w.v.max()/1e6, "trillion")
print("WALCL 2022 weekly (millions):"); print(w2.to_string(index=False))
c=pd.read_csv('CPIAUCNS.csv',parse_dates=['observation_date']); c.columns=['date','v']; c=c.set_index('date')
c['yoy']=(c.v/c.v.shift(12)-1)*100
print("\nCPI NSA YoY 2021-10..2022-09:"); print(c.loc['2021-10':'2022-09','yoy'].round(2).to_string())
print("\nCPI YoY: last month at/above 7.0 before Nov2021:", c[(c.yoy>=7.0)&(c.index<'2021-01-01')].index.max())
print("CPI YoY: last month at/above 9.06 before Jun2022:", c[(c.yoy>=9.06)&(c.index<'2021-01-01')].index.max())
