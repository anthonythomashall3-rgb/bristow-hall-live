"""Stage 190: the same engine, three domains.  The American instrument of 2026, the American
instrument of 1893 and the Japanese instrument of 1994 are now literally the same code with
different inputs, which is the only way the international record is evidence about the national
one.  Every missed episode is then diagnosed: did the country have usable channels at the time,
or did it have them and not fire?"""
import os, sys, glob, json
import numpy as np, pandas as pd
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import recession_engine as E
ODD=os.path.expanduser("~/mnt/Onset Detector Data/")
FE="/root/fetch/"
def rd(p,dcol="date"):
    d=pd.read_csv(p); d.columns=[c.lower() for c in d.columns]
    c0=d.columns[0]; v=d.columns[1]
    s=pd.Series(pd.to_numeric(d[v],errors="coerce").values,index=pd.to_datetime(d[c0],errors="coerce"))
    return s[s.index.notna()].dropna().sort_index()
DELTA=0.10
# ---------- domain 1: the United States, monthly, 1948-2026 ----------
LEVELS={"UNRATE","U6RATE","EMRATIO","CIVPART","UEMPMEAN","UEMPMED","TCU","MCUMFN","MSACSR",
        "ISRATIO","AISRSA","NAPM","NAPMNOI","IURSA","UMCSENT","USSLIND"}
US={}
for p_ in sorted(glob.glob(FE+"usmod/*.csv")):
    sid=os.path.basename(p_)[:-4]
    s_=rd(p_)
    if len(s_)<200: continue
    if len(s_)>2000: s_=s_.resample("MS").mean()      # weekly claims to monthly
    US[sid]=(s_,"level" if sid in LEVELS else "activity")
print("modern American series loaded: %d"%len(US))
g1=rd(ODD+"06_interest_rates_yield_curve/monthly/GS1.csv"); g10=rd(ODD+"06_interest_rates_yield_curve/monthly/GS10.csv")
NBER_MOD=[("1948-11","1949-10"),("1953-07","1954-05"),("1957-08","1958-04"),("1960-04","1961-02"),
          ("1969-12","1970-11"),("1973-11","1975-03"),("1980-01","1980-07"),("1981-07","1982-11"),
          ("1990-07","1991-03"),("2001-03","2001-11"),("2007-12","2009-06"),("2020-02","2020-04"),("2024-04","2024-08")]
EPm=[(pd.Timestamp(a+"-01"),pd.Timestamp(b+"-01")) for a,b in NBER_MOD]
idx=pd.DatetimeIndex(pd.date_range("1948-01-01","2026-08-01",freq="MS"))
r1=E.run(US,EPm,idx,delta=DELTA,labour_names=["UNRATE","U6RATE","IURSA"],short_rate=g1,long_rate=g10)
print("UNITED STATES, monthly, 1948-2026: %d of %d detected, %d false in %.0f quiet years, %d channels"%(
    sum(r1["detected"]),len(EPm),len(r1["false"]),r1["quiet_years"],r1["channels"]))
print("   lags %s"%r1["lags"])
if r1["false"]: print("   false: %s"%r1["false"])
# ---------- domain 2: the United States, monthly, 1873-1948 ----------
SEL=json.load(open(FE+"nber/selected.json"))
US2={}
for p in sorted(glob.glob(FE+"nber/*.csv")):
    sid=os.path.basename(p)[:-4]
    if sid=="selected": continue
    s=rd(p)
    if len(s)<240 or s.index.min()>pd.Timestamp("1940-01-01"): continue
    US2[sid]=(s,"activity")
NB2=[("1873-10","1879-03"),("1882-03","1885-05"),("1887-03","1888-04"),("1890-07","1891-05"),
     ("1893-01","1894-06"),("1895-12","1897-06"),("1899-06","1900-12"),("1902-09","1904-08"),
     ("1907-05","1908-06"),("1910-01","1912-01"),("1913-01","1914-12"),("1918-08","1919-03"),
     ("1920-01","1921-07"),("1923-05","1924-07"),("1926-10","1927-11"),("1929-08","1933-03"),
     ("1937-05","1938-06"),("1945-02","1945-10")]
EP2=[(pd.Timestamp(a+"-01"),pd.Timestamp(b+"-01")) for a,b in NB2]
idx2=pd.DatetimeIndex(pd.date_range("1860-01-01","1948-12-01",freq="MS"))
r2=E.run(US2,EP2,idx2,delta=DELTA,labour_names=[])
print("\nUNITED STATES, monthly, 1873-1948: %d of %d detected, %d false in %.0f quiet years, %d channels"%(
    sum(r2["detected"]),len(EP2),len(r2["false"]),r2["quiet_years"],r2["channels"]))
print("   lags %s"%r2["lags"])
if r2["false"]: print("   false: %s"%r2["false"][:8])
