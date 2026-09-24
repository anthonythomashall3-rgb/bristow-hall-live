import pandas as pd, numpy as np
sr=pd.read_csv('SAHMREALTIME.csv',parse_dates=['observation_date']); sr.columns=['date','rt']
sc=pd.read_csv('SAHMCURRENT.csv',parse_dates=['observation_date']); sc.columns=['date','cur']
m=pd.merge(sr,sc,on='date',how='outer').sort_values('date')
print("SAHMREALTIME span:",sr.date.min().date(),sr.date.max().date())
print("SAHMCURRENT span:",sc.date.min().date(),sc.date.max().date())
print("\n2023-2026 monthly:")
print(m[(m.date>='2023-06-01')].to_string(index=False))
