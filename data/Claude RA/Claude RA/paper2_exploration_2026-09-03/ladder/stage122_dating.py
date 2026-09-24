"""Stage 122: separate the ALARM from the DATE.  The alarm is a warning and should be as
early as the data allow; the date is a measurement and should be as accurate as the data
allow.  This stage asks a different question from every earlier one: once an episode is
open, which weekly or daily object places the turning DAY closest to the calendar boundary
the NBER's monthly peak and trough imply?"""
exec(open("stage106_v11.py").read().split('eps,l,e,t,f,n,arm,lv,co,cco=machine()')[0])
import numpy as np, pandas as pd
FIRST=[pd.Timestamp(x) for x in ["1970-01-01","1973-12-01","1980-02-01","1981-08-01","1990-08-01",
                                 "2001-04-01","2008-01-01","2020-03-01","2024-05-01"]]
LAST =[pd.Timestamp(x) for x in ["1970-12-01","1975-04-01","1980-08-01","1982-12-01","1991-04-01",
                                 "2001-12-01","2009-07-01","2020-05-01","2024-09-01"]]
cc=load(ODD+"01_labor_unemployment/weekly/CCSA.csv")
ccn=load(ODD+"01_labor_unemployment/weekly/CCNSA.csv")
icn_=load(ODD+"01_labor_unemployment/weekly/ICNSA.csv")
OBJ={}
for lab,s in [("initial claims",ic),("continued claims",cc),("insured rate",iur)]:
    for w in [4,6,8,10,13,17,26]:
        OBJ["%s %dwk"%(lab,w)]=s.rolling(w,center=False).mean()
        OBJ["%s %dwk centred"%(lab,w)]=s.rolling(w,center=True).mean()
def argmin_day(s, lo, hi):
    w=s[(s.index>=lo)&(s.index<=hi)].dropna()
    return w.idxmin() if len(w) else None
def argmax_day(s, lo, hi):
    w=s[(s.index>=lo)&(s.index<=hi)].dropna()
    return w.idxmax() if len(w) else None
print("PEAK DAY: the week each object bottoms in the 18 months before the recession began")
print("%-28s %-7s %-6s %-6s %s"%("object","mean|d|","med|d|","<=7d","days from the first day"))
rows=[]
for name,s in OBJ.items():
    ds=[]
    for i,f0 in enumerate(FIRST):
        d=argmin_day(s,f0-pd.Timedelta(days=550),f0+pd.Timedelta(days=60))
        ds.append(np.nan if d is None else (d-f0).days)
    v=[x for x in ds if x==x]
    if len(v)<9: continue
    rows.append((float(np.mean(np.abs(v))),float(np.median(np.abs(v))),sum(1 for x in v if abs(x)<=7),name,[int(x) for x in ds]))
rows.sort()
for a,b,c,name,ds in rows[:14]: print("%-28s %-7.1f %-6.0f %-6d %s"%(name,a,b,c,ds))
print("\nTROUGH DAY: the week each object peaks in the 18 months around the recession's end")
rows2=[]
for name,s in OBJ.items():
    ds=[]
    for i,l0 in enumerate(LAST):
        d=argmax_day(s,l0-pd.Timedelta(days=550),l0+pd.Timedelta(days=120))
        ds.append(np.nan if d is None else (d-l0).days)
    v=[x for x in ds if x==x]
    if len(v)<9: continue
    rows2.append((float(np.mean(np.abs(v))),float(np.median(np.abs(v))),sum(1 for x in v if abs(x)<=7),name,[int(x) for x in ds]))
rows2.sort()
for a,b,c,name,ds in rows2[:14]: print("%-28s %-7.1f %-6.0f %-6d %s"%(name,a,b,c,ds))
