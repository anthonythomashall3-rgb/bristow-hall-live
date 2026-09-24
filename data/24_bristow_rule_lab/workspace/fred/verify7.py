import pandas as pd, numpy as np
sc=pd.read_csv('SAHMCURRENT.csv',parse_dates=['observation_date']); sc.columns=['date','v']
sc['v']=pd.to_numeric(sc['v'],errors='coerce'); sc=sc.dropna().set_index('date')
u=pd.read_csv('UNRATE.csv',parse_dates=['observation_date']); u.columns=['date','u']; u=u.set_index('date')
print("1959 crossing:",sc.loc['1959-09':'1960-04'].T.to_string())
print("\n1966-67 soft patch: Sahm max", sc.loc['1966-01':'1968-06'].v.max(), "at", sc.loc['1966-01':'1968-06'].v.idxmax().date())
print("  unrate 1966-10..1967-12:"); print(u.loc['1966-09':'1967-12'].T.to_string())
print("\n1985-86: Sahm max", sc.loc['1985-01':'1987-06'].v.max(), "at", sc.loc['1985-01':'1987-06'].v.idxmax().date())
print("  unrate 1985-11..1986-12:"); print(u.loc['1985-11':'1986-12'].T.to_string())
print("\n1962-63: Sahm max", sc.loc['1962-01':'1964-06'].v.max(),"at",sc.loc['1962-01':'1964-06'].v.idxmax().date())
print("  unrate 1962-01..1963-12 min/max:", u.loc['1962-01':'1963-12'].u.min(), u.loc['1962-01':'1963-12'].u.max())
print(u.loc['1962-01':'1963-12'].T.to_string())
print("\n2001-2003 unemployment:"); print(u.loc['2001-11':'2003-12'].T.to_string())
print("\n2023-2026 unemployment:"); print(u.loc['2023-01':'2026-07'].T.to_string())
