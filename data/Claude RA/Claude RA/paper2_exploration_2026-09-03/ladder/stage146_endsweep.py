"""Stage 146: the end call, measured against the calendar.  Earlier rounds scored the end in
months against the NBER trough; this one measures the DAY the end is called against the first
day of the expansion, and sweeps the smoothing window, the size of the fall and the series."""
exec(open("stage106_v11.py").read().split('eps,l,e,t,f,n,arm,lv,co,cco=machine()')[0])
import numpy as np, pandas as pd
LAST=[pd.Timestamp(x) for x in ["1970-12-01","1975-04-01","1980-08-01","1982-12-01","1991-04-01",
                                "2001-12-01","2009-07-01","2020-05-01","2024-09-01"]]
ONS=[pd.Timestamp(x) for x in ["1969-10-06","1973-10-25","1980-01-03","1981-08-18","1990-08-03",
                               "2001-02-02","2007-12-18","2020-02-28","2024-05-03"]]
cc=load(ODD+"01_labor_unemployment/weekly/CCSA.csv")
SER={"initial claims":ic,"continued claims":cc,"insured rate":iur}
def endcalls(s,w,pct,lag=5,withdraw=True):
    m=s.rolling(w).mean()
    x=m.copy(); x.index=x.index+pd.Timedelta(days=lag)
    v=x.reindex(cal).ffill().values.astype(float)
    out=[]
    for k,o in enumerate(ONS):
        i0=int(np.searchsorted(cal,o)); runmax=-1; pk=None; call=None
        lim=int(np.searchsorted(cal,o+pd.Timedelta(days=1500)))
        for i in range(i0,min(lim,N)):
            y=v[i]
            if np.isnan(y): continue
            if y>runmax:
                runmax=y; pk=i
                if withdraw: call=None
            if pk is not None and y<=runmax*(1-pct) and call is None: call=i
        out.append(None if call is None else cal[call])
    return out
rows=[]
for nm,s in SER.items():
  for w in [4,6,8,10,13,17]:
    for pct in [0.01,0.02,0.03,0.04,0.05,0.06,0.08,0.10]:
      for wd in [True,False]:
        d=endcalls(s,w,pct,withdraw=wd)
        if any(x is None for x in d): continue
        dd=[(d[i]-LAST[i]).days for i in range(9)]
        rows.append((float(np.mean(np.abs(dd))),sum(1 for x in dd if abs(x)<=7),sum(1 for x in dd if abs(x)<=31),
                     nm,w,pct,wd,dd))
rows.sort()
print("END CALL: day of the call versus the first day of the expansion")
print("%-18s %-4s %-6s %-6s %-8s %-6s %-6s %s"%("series","wk","fall","withdr","mean|d|","<=7d","<=31d","days"))
for a,c7,c31,nm,w,pct,wd,dd in rows[:16]:
    print("%-18s %-4d %-6.0f%% %-6s %-8.1f %-6d %-6d %s"%(nm,w,100*pct,"yes" if wd else "no",a,c7,c31,dd))
print("\nv11 and v14's own end rule (initial claims, 8 weeks, 3%, withdrawn on a new high):")
d=endcalls(ic,8,0.03,withdraw=True); dd=[(d[i]-LAST[i]).days for i in range(9)]
print("  days %s  mean|d| %.1f  within a week %d  within a month %d"%(dd,float(np.mean(np.abs(dd))),sum(1 for x in dd if abs(x)<=7),sum(1 for x in dd if abs(x)<=31)))
