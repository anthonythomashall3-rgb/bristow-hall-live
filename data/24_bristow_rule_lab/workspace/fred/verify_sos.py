import pandas as pd, numpy as np
d=pd.read_csv('IURSA.csv',parse_dates=['observation_date']); d.columns=['date','iur']
d['iur']=pd.to_numeric(d.iur,errors='coerce'); d=d.dropna().reset_index(drop=True)
print("IURSA span:",d.date.min().date(),"->",d.date.max().date(),len(d),"weeks")
d['ma26']=d.iur.rolling(26).mean()
d['min52']=d.ma26.rolling(52).min()          # min of the 26w MA over the 52 preceding weeks
d['sos']=(d.ma26-d.min52).round(4)
# also the alternative: min of the raw IUR over 52 weeks
d['min52raw']=d.iur.rolling(52).min()
d['sos_alt']=(d.ma26-d.min52raw).round(4)
for y in [2023,2024,2025,2026]:
    s=d[(d.date>=f'{y}-01-01')&(d.date<=f'{y}-12-31')]
    print(f"{y}: max sos={s.sos.max():.4f} on {s.loc[s.sos.idxmax(),'date'].date() if s.sos.notna().any() else '-'}   (alt basis max={s.sos_alt.max():.4f})")
print("\n2023 weeks with sos >= 0.20 (MA-min basis):")
print(d[(d.date>='2023-07-01')&(d.date<='2024-01-31')][['date','iur','ma26','min52','sos']].round(4).to_string(index=False))

print("\nLatest SOS readings:")
print(d.tail(8)[['date','iur','ma26','min52','sos']].round(4).to_string(index=False))
rec=[("1969-12","1970-11"),("1973-11","1975-03"),("1980-01","1980-07"),("1981-07","1982-11"),
     ("1990-07","1991-03"),("2001-03","2001-11"),("2007-12","2009-06"),("2020-02","2020-04")]
print("\nSOS peak inside each recession window (current vintage):")
for p,t in rec:
    p=pd.Timestamp(p); t=pd.Timestamp(t)
    w=d[(d.date>=p)&(d.date<=t+pd.DateOffset(months=6))]
    if w.sos.notna().any():
        print(f"  {p:%Y-%m}: max {w.sos.max():.3f}  first crossing >0.20 on {w[w.sos>0.20].date.min().date() if (w.sos>0.20).any() else 'never'}")
