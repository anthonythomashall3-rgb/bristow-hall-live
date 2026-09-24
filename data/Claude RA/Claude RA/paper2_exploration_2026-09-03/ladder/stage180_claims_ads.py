"""Stage 180: two fast objects as dating inputs.  The machine already produces a claims-peak week
the moment it calls the end -- weekly, no publication lag -- and it dates the trough within a
month five times in nine on its own.  The ADS index is daily back to 1960.  Both are faster than
any monthly series, so if either sharpens the coincident panel the date arrives sooner or better."""
exec(open("stage124_datemonth.py").read().split("def report(")[0])
import numpy as np, pandas as pd, os
ODD2=os.path.expanduser("~/mnt/Onset Detector Data/")
ads=pd.read_csv(ODD2+"25_fred_daily_weekly/other_daily/ads_index_current.csv",parse_dates=["date"]).set_index("date")["ads"]
ADSm=ads.resample("MS").mean()
CLAIMS_PEAK=[pd.Period(x,"M") for x in ["1970-11","1975-03","1980-07","1982-10","1991-04","2001-11","2009-04","2020-05","2024-08"]]
ALL4=[n for n in ["payrolls","real income less transfers","industrial production","real manufacturing and trade sales"] if n in M]
FAST=[n for n in ALL4 if n!="real manufacturing and trade sales"]
ENDC2=[pd.Timestamp(x) for x in ["1970-12-17","1975-05-08","1980-07-24","1982-11-18","1991-05-09",
                                 "2001-12-13","2009-05-14","2020-05-28","2024-09-26"]]
def months(names,a,back,fwd,kind,extra=None):
    o=[]
    for nm in names:
        s=M.get(nm)
        if s is None: continue
        w=s[(s.index>=a-pd.Timedelta(days=back))&(s.index<=a+pd.Timedelta(days=fwd))].dropna()
        if len(w)>=6: o.append((w.idxmax() if kind=="max" else w.idxmin()).to_period("M").ordinal)
    if extra is not None: o+=extra
    return o
def agg(o,how="nearest"):
    if not o: return None
    x=float(np.median(o))
    return pd.Period(ordinal=(int(np.floor(x)) if how=="earlier" else int(round(x))),freq="M")
def adsmonth(a,back,fwd,kind):
    w=ADSm[(ADSm.index>=a-pd.Timedelta(days=back))&(ADSm.index<=a+pd.Timedelta(days=fwd))].dropna()
    return None if len(w)<6 else (w.idxmax() if kind=="max" else w.idxmin()).to_period("M").ordinal
print("TROUGH")
print("%-52s %-9s %-9s %s"%("panel","exact","<=1 mo","months from the NBER trough"))
CASES=[("the four coincident series",ALL4,False,False),
       ("the four, plus the claims peak",ALL4,True,False),
       ("the four, plus the claims peak twice",ALL4,"twice",False),
       ("the four, plus the ADS index",ALL4,False,True),
       ("the four, plus claims peak and ADS",ALL4,True,True),
       ("the fast three",FAST,False,False),
       ("the fast three, plus the claims peak",FAST,True,False),
       ("the fast three, plus claims peak and ADS",FAST,True,True),
       ("the claims peak alone",[],True,False)]
for lab,names,cl,useads in CASES:
    mo=[]
    for i,a in enumerate(ENDC2):
        extra=[]
        if cl: extra+= [CLAIMS_PEAK[i].ordinal]*(2 if cl=="twice" else 1)
        if useads:
            v=adsmonth(a,300,30,"min")
            if v is not None: extra.append(v)
        d=agg(months(names,a,300,30,"min",extra if extra else None))
        mo.append(None if d is None else (d-pd.Period(TRM[i],"M")).n)
    ok=[x for x in mo if x is not None]
    print("%-52s %-9s %-9d %s"%(lab,"%d of 9"%sum(1 for x in ok if x==0),sum(1 for x in ok if abs(x)<=1),mo))
print("\nPEAK (the claims peak is not defined for a peak; ADS only)")
print("%-52s %-9s %-9s %s"%("panel","exact","<=1 mo","months from the NBER peak"))
for lab,names,useads,how in [("the four coincident series",ALL4,False,"earlier"),
                             ("the four, plus the ADS index",ALL4,True,"earlier"),
                             ("the fast three",FAST,False,"nearest"),
                             ("the fast three, plus the ADS index",FAST,True,"nearest")]:
    mo=[]
    for i,a in enumerate(ALARM):
        extra=[]
        if useads:
            v=adsmonth(a,180,180,"max")
            if v is not None: extra.append(v)
        d=agg(months(names,a,180,180,"max",extra if extra else None),how)
        mo.append(None if d is None else (d-pd.Period(PKM[i],"M")).n)
    ok=[x for x in mo if x is not None]
    print("%-52s %-9s %-9d %s"%(lab,"%d of 9"%sum(1 for x in ok if x==0),sum(1 for x in ok if abs(x)<=1),mo))
