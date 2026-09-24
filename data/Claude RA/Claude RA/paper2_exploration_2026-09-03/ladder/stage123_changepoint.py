"""Stage 123: dating a turning point as a BREAK IN SLOPE rather than as a high or a low.
Claims fall for a year before a recession and rise for a year after one, so the extremum of
a claims series is a poor estimate of the day the cycle turned; the day the slope changes
sign is the natural object.  A continuous two-segment fit is run over a window anchored on
the machine's own alarm, and the break day is compared with the calendar boundary."""
exec(open("stage106_v11.py").read().split('eps,l,e,t,f,n,arm,lv,co,cco=machine()')[0])
import numpy as np, pandas as pd
FIRST=[pd.Timestamp(x) for x in ["1970-01-01","1973-12-01","1980-02-01","1981-08-01","1990-08-01",
                                 "2001-04-01","2008-01-01","2020-03-01","2024-05-01"]]
LAST =[pd.Timestamp(x) for x in ["1970-12-01","1975-04-01","1980-08-01","1982-12-01","1991-04-01",
                                 "2001-12-01","2009-07-01","2020-05-01","2024-09-01"]]
ALARM=[pd.Timestamp(x) for x in ["1969-10-06","1973-10-25","1980-01-03","1981-08-18","1990-08-03",
                                 "2001-02-02","2008-01-04","2020-02-28","2024-05-03"]]
cc=load(ODD+"01_labor_unemployment/weekly/CCSA.csv")
def brk(y, minseg=6):
    """continuous two-segment least squares; returns index of the break"""
    n=len(y); t=np.arange(n,dtype=float); best=(np.inf,None)
    for k in range(minseg,n-minseg):
        X=np.column_stack([np.ones(n),t,np.maximum(t-k,0.0)])
        b,res,rk,sv=np.linalg.lstsq(X,y,rcond=None)
        r=y-X@b; ssr=float(r@r)
        if ssr<best[0]: best=(ssr,k)
    return best[1]
SER={"initial claims":ic,"continued claims":cc,"insured rate":iur}
print("PEAK: break in the slope of log claims, window anchored on the alarm")
print("%-22s %-4s %-6s %-6s %-7s %-6s %s"%("series","sm","back","fwd","mean|d|","<=7d","days from the first day"))
best=[]
for nm,s in SER.items():
  for sm in [4,8,13]:
    z=np.log(s.rolling(sm).mean().dropna())
    for back in [360,450,540,720]:
      for fwd in [0,30,60,90]:
        ds=[]
        for i,a in enumerate(ALARM):
            w=z[(z.index>=a-pd.Timedelta(days=back))&(z.index<=a+pd.Timedelta(days=fwd))]
            if len(w)<25: ds.append(np.nan); continue
            k=brk(w.values); ds.append(np.nan if k is None else (w.index[k]-FIRST[i]).days)
        v=[x for x in ds if x==x]
        if len(v)<9: continue
        best.append((float(np.mean(np.abs(v))),sum(1 for x in v if abs(x)<=7),nm,sm,back,fwd,[int(x) for x in ds]))
best.sort()
for a,c,nm,sm,back,fwd,ds in best[:12]:
    print("%-22s %-4d %-6d %-6d %-7.1f %-6d %s"%(nm,sm,back,fwd,a,c,ds))
print("\nTROUGH: same break, window anchored on the machine's own end call")
ENDC=[pd.Timestamp(x) for x in ["1971-01-01","1975-06-13","1980-08-01","1982-12-10","1991-06-07",
                                "2002-01-04","2009-06-05","2020-06-05","2024-09-27"]]
best2=[]
for nm,s in SER.items():
  for sm in [4,8,13]:
    z=np.log(s.rolling(sm).mean().dropna())
    for back in [360,450,540,720]:
      for fwd in [0,60,120,180]:
        ds=[]
        for i,a in enumerate(ENDC):
            w=z[(z.index>=a-pd.Timedelta(days=back))&(z.index<=a+pd.Timedelta(days=fwd))]
            if len(w)<25: ds.append(np.nan); continue
            k=brk(w.values); ds.append(np.nan if k is None else (w.index[k]-LAST[i]).days)
        v=[x for x in ds if x==x]
        if len(v)<9: continue
        best2.append((float(np.mean(np.abs(v))),sum(1 for x in v if abs(x)<=7),nm,sm,back,fwd,[int(x) for x in ds]))
best2.sort()
print("%-22s %-4s %-6s %-6s %-7s %-6s %s"%("series","sm","back","fwd","mean|d|","<=7d","days from the first day"))
for a,c,nm,sm,back,fwd,ds in best2[:12]:
    print("%-22s %-4d %-6d %-6d %-7.1f %-6d %s"%(nm,sm,back,fwd,a,c,ds))
