import pandas as pd, numpy as np
sc=pd.read_csv('SAHMCURRENT.csv',parse_dates=['observation_date']); sc.columns=['date','v']
sc['v']=pd.to_numeric(sc['v'],errors='coerce'); sc=sc.dropna().reset_index(drop=True)
sc['d3']=sc.v-sc.v.shift(3)
s=sc.set_index('date')
rec=[("1948-11","1949-10"),("1953-07","1954-05"),("1957-08","1958-04"),("1960-04","1961-02"),
     ("1969-12","1970-11"),("1973-11","1975-03"),("1980-01","1980-07"),("1981-07","1982-11"),
     ("1990-07","1991-03"),("2001-03","2001-11"),("2007-12","2009-06"),("2020-02","2020-04")]
print("SECOND-DERIVATIVE (fastest 3-month climb) month vs NBER trough:")
g2=[]
for p,t in rec:
    p=pd.Timestamp(p);t=pd.Timestamp(t)
    w=s.loc[p:t+pd.DateOffset(months=12)].dropna(subset=['d3'])
    if not len(w): print(p,"nodata"); continue
    mx=w.d3.max(); pk=w[w.d3==mx].index[0]
    gap=(pk.year-t.year)*12+(pk.month-t.month); g2.append(gap)
    print(f"  {p:%Y-%m}->{t:%Y-%m}: fastest climb ends {pk:%Y-%m} ({mx:.2f} pp) gap {gap:+d}")
print("  gaps:",g2,"exact-on-trough:",sum(g==0 for g in g2),"max:",max(g2),"min:",min(g2))

# Standalone crossings screen
usrec=pd.read_csv('USREC.csv',parse_dates=['observation_date']); usrec.columns=['date','r']
m=pd.merge(sc,usrec,on='date',how='left')
m=m[m.date>='1949-01-01']
out=m[(m.v>=0.50)&(m.r==0)]
print("\nMonths with current-vintage Sahm >= 0.50 while NBER dates no recession, 1949-2026:")
# group into runs
out=out.reset_index(drop=True)
runs=[];cur=[out.date[0]]
for i in range(1,len(out)):
    if (out.date[i]-out.date[i-1]).days<=32: cur.append(out.date[i])
    else: runs.append(cur); cur=[out.date[i]]
runs.append(cur)
for r in runs:
    vals=m[(m.date>=r[0])&(m.date<=r[-1])].v.tolist()
    print(f"  {r[0]:%Y-%m} -> {r[-1]:%Y-%m}  ({len(r)} months) max={max(vals):.2f}")
