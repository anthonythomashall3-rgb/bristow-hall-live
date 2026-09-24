import pandas as pd, numpy as np
f=pd.read_csv('FEDFUNDS.csv',parse_dates=['observation_date']); f.columns=['date','v']; f['v']=pd.to_numeric(f.v,errors='coerce')
f=f.dropna().reset_index(drop=True)
f['d17']=f.v-f.v.shift(17)
big=f[f.d17>=5.25]
print("Months where the 17-month rise in the effective funds rate was >= 5.25 pp:")
print(big[['date','v','d17']].to_string(index=False))
print("\nMax 17-month rise ever:", f.d17.max(), "ending", f.loc[f.d17.idxmax(),'date'].date())
print("\nAug 2023 value:",float(f[f.date=='2023-08-01'].v), " Mar 2022:",float(f[f.date=='2022-03-01'].v)," Feb 2022:",float(f[f.date=='2022-02-01'].v))
print("17-month change Mar2022->Aug2023:", float(f[f.date=='2023-08-01'].v)-float(f[f.date=='2022-03-01'].v))
