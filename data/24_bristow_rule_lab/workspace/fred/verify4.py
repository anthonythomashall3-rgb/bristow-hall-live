import pandas as pd, numpy as np
sc=pd.read_csv('SAHMCURRENT.csv',parse_dates=['observation_date']); sc.columns=['date','v']
sc['v']=pd.to_numeric(sc['v'],errors='coerce'); sc=sc.dropna().reset_index(drop=True)
sc=sc.set_index('date')
rec=[("1948-11","1949-10"),("1953-07","1954-05"),("1957-08","1958-04"),("1960-04","1961-02"),
     ("1969-12","1970-11"),("1973-11","1975-03"),("1980-01","1980-07"),("1981-07","1982-11"),
     ("1990-07","1991-03"),("2001-03","2001-11"),("2007-12","2009-06"),("2020-02","2020-04")]
print("BRISTOW RULE TEST: month of Sahm-indicator peak (current vintage) vs NBER trough")
print(f"{'peak':>8} {'trough':>8} {'indicator peak mo':>18} {'peak val':>9} {'gap (mo)':>9}")
gaps=[]
for p,t in rec:
    p=pd.Timestamp(p); t=pd.Timestamp(t)
    # search window: recession peak through trough+12 months
    w=sc.loc[p:t+pd.DateOffset(months=12)]
    if len(w)==0: print(f"{p:%Y-%m} {t:%Y-%m}  NO DATA"); continue
    mx=w.v.max(); pk=w[w.v==mx].index[0]
    gap=(pk.year-t.year)*12+(pk.month-t.month)
    gaps.append(gap)
    print(f"{p:%Y-%m} {t:%Y-%m} {pk:%Y-%m}"+" "*10+f"{mx:9.2f} {gap:+9d}")
print("\ngaps:",gaps,"  median:",np.median(gaps),"  min:",min(gaps),"max:",max(gaps))
print("within 3 months:",sum(abs(g)<=3 for g in gaps),"of",len(gaps))
print("\nSmallest in-recession peak value:", )
for p,t in rec:
    p=pd.Timestamp(p); t=pd.Timestamp(t)
    w=sc.loc[p:t+pd.DateOffset(months=12)]
    if len(w): print(f"  {p:%Y-%m}: {w.v.max():.2f}")
