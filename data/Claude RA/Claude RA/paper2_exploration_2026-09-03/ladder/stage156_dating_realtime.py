"""Stage 156: when is the date knowable?  The dating step reads a window that extends 180 days
past the alarm, so the date it gives on the day of the alarm is not the date it gives six months
later.  This stage runs the same step at a sequence of dates after the alarm, allowing each
series only the months that had actually been published by then, and reports how the answer
converges."""
exec(open("stage124_datemonth.py").read().split("def report(")[0])
import numpy as np, pandas as pd
FOUR={"payrolls":7,"real income less transfers":30,"industrial production":17,
      "real manufacturing and trade sales":47}   # days after the month ends before it is published
FOUR={k:v for k,v in FOUR.items() if k in M}
def known_by(nm,asof):
    s=M[nm]
    lag=FOUR[nm]
    pub=pd.Series(s.index,index=s.index).apply(lambda d:(d+pd.offsets.MonthEnd(1))+pd.Timedelta(days=lag))
    return s[pub<=asof]
def peak_asof(alarm,asof,back=180,fwd=180):
    o=[]
    for nm in FOUR:
        s=known_by(nm,asof)
        w=s[(s.index>=alarm-pd.Timedelta(days=back))&(s.index<=min(asof,alarm+pd.Timedelta(days=fwd)))].dropna()
        if len(w)>=6: o.append(w.idxmax().to_period("M").ordinal)
    if not o: return None
    return pd.Period(ordinal=int(round(float(np.median(o)))),freq="M")
def trough_asof(endc,asof,back=365,fwd=180):
    o=[]
    for nm in FOUR:
        s=known_by(nm,asof)
        w=s[(s.index>=endc-pd.Timedelta(days=back))&(s.index<=min(asof,endc+pd.Timedelta(days=fwd)))].dropna()
        if len(w)>=6: o.append(w.idxmin().to_period("M").ordinal)
    if not o: return None
    return pd.Period(ordinal=int(round(float(np.median(o)))),freq="M")
ENDC2=[pd.Timestamp(x) for x in ["1970-12-17","1975-05-08","1980-07-24","1982-11-18","1991-05-09",
                                 "2001-12-13","2009-05-14","2020-05-28","2024-09-26"]]
KS=[0,1,2,3,4,6,9,12]
print("PEAK: months from the NBER peak, at each number of months after the alarm")
print("%-9s %s"%("peak"," ".join("%+4d mo"%k for k in KS)))
for i,a in enumerate(ALARM):
    row=[]
    for k in KS:
        pm=peak_asof(a,a+pd.DateOffset(months=k))
        row.append("  -  " if pm is None else "%+5d"%((pm-pd.Period(PKM[i],"M")).n))
    print("%-9s %s"%(PKM[i]," ".join("%6s"%c for c in row)))
print("\nTROUGH: months from the NBER trough, at each number of months after the end call")
print("%-9s %s"%("trough"," ".join("%+4d mo"%k for k in KS)))
for i,a in enumerate(ENDC2):
    row=[]
    for k in KS:
        tm=trough_asof(a,a+pd.DateOffset(months=k))
        row.append("  -  " if tm is None else "%+5d"%((tm-pd.Period(TRM[i],"M")).n))
    print("%-9s %s"%(TRM[i]," ".join("%6s"%c for c in row)))
print("\nhow many of the nine are exact at each horizon")
for lab,anch,ref,fn in [("peak",ALARM,PKM,peak_asof),("trough",ENDC2,TRM,trough_asof)]:
    line=[]
    for k in KS:
        n=0
        for i,a in enumerate(anch):
            d=fn(a,a+pd.DateOffset(months=k))
            if d is not None and (d-pd.Period(ref[i],"M")).n==0: n+=1
        line.append("%d"%n)
    print("  %-7s %s"%(lab," ".join("%6s"%c for c in line)))
