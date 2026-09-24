"""Stage 175: a faster end call, judged by the date it makes possible.  Earlier sweeps scored the
end call by its own distance from the trough.  That is the wrong objective: the end call's job is
to open the dating window, so what matters is how EARLY it arrives while the trough date it
produces is still right.  This stage sweeps the series, the smoothing and the size of the fall,
and for each scores the advance trough date it yields."""
exec(open("stage171_faster_dating.py").read().split('print("PEAK')[0])
import numpy as np, pandas as pd
FASTP=[n for n in ["payrolls","industrial production","real income less transfers"] if n in M]
ONS=[pd.Timestamp(x) for x in ["1969-10-06","1973-10-25","1980-01-03","1981-08-18","1990-08-03",
                               "2001-02-02","2007-12-18","2020-02-28","2024-05-03"]]
CLOSE=[pd.Timestamp(x) for x in ["1972-02-04","1976-05-07","1981-08-07","1983-10-07","1993-03-05",
                                 "2003-02-07","2010-09-03","2021-07-02","2025-01-10"]]
import os
ODD2=os.path.expanduser("~/mnt/Onset Detector Data/")
def load2(p):
    d=pd.read_csv(p,parse_dates=[0]); d=d.set_index(d.columns[0]).iloc[:,0]
    return pd.to_numeric(d,errors="coerce").dropna()
ic=load2(ODD2+"01_labor_unemployment/weekly/ICSA.csv")
cc=load2(ODD2+"01_labor_unemployment/weekly/CCSA.csv")
iur=load2(ODD2+"01_labor_unemployment/weekly/IURSA.csv")
SER={"initial claims":ic,"continued claims":cc,"insured rate":iur}
def endcalls(s,w,pct,lag=5):
    m=s.rolling(w).mean(); m.index=m.index+pd.Timedelta(days=lag)
    out=[]
    for k,o in enumerate(ONS):
        seg=m[(m.index>=o)&(m.index<=CLOSE[k])].dropna()
        if len(seg)<10: out.append(None); continue
        run=-np.inf; call=None
        for d,v in seg.items():
            if v>run: run=v; call=None
            elif call is None and v<=run*(1-pct): call=d
        out.append(call)
    return out
def med3(anchor,asof,back,fwd):
    o=[]
    for nm in FASTP:
        d=turn(nm,anchor,asof,back,fwd,"min")
        if d is not None: o.append(d.to_period("M").ordinal)
    return None if not o else pd.Period(ordinal=int(round(float(np.median(o)))),freq="M")
CUR=[pd.Timestamp(x) for x in ["1970-12-17","1975-05-08","1980-07-24","1982-11-18","1991-05-09",
                               "2001-12-13","2009-05-14","2020-05-28","2024-09-26"]]
def score(ends,months=1,back=300,fwd=30):
    errs=[];days=[]
    for i,e in enumerate(ends):
        if e is None: errs.append(None); days.append(None); continue
        d=med3(e,e+pd.DateOffset(months=months),back,fwd)
        errs.append(None if d is None else (d-pd.Period(TRM[i],"M")).n)
        days.append((e-pd.Period(TRM[i],"M").to_timestamp(how="end")).days)
    ok=[x for x in errs if x is not None]
    return sum(1 for x in ok if x==0),sum(1 for x in ok if abs(x)<=1),errs,days
base=score(CUR)
print("the end call in use: exact %d of 9, within one month %d | days after the trough month ends %s"%(base[0],base[1],base[3]))
print("   mean %.0f days"%np.mean([abs(x) for x in base[3] if x is not None]))
print("\n%-18s %-4s %-6s %-9s %-8s %-10s %s"%("series","wk","fall","exact","<=1 mo","mean days","days after the trough month ends"))
rows=[]
for nm,s in SER.items():
  for w in [4,6,8,10,13]:
    for pct in [0.01,0.02,0.03,0.04,0.05,0.07,0.10]:
        ends=endcalls(s,w,pct)
        if any(e is None for e in ends): continue
        ex,w1,errs,days=score(ends)
        md=float(np.mean([d for d in days if d is not None]))
        rows.append((ex,-md,nm,w,pct,ex,w1,md,days,errs))
rows.sort(key=lambda r:(-r[0],r[1]))
for ex,negmd,nm,w,pct,e2,w1,md,days,errs in rows[:14]:
    print("%-18s %-4d %-6.0f%% %-9s %-8d %-10.0f %s"%(nm,w,100*pct,"%d of 9"%ex,w1,md,days))
print("\nbest that is FASTER than the current rule and no less accurate:")
for ex,negmd,nm,w,pct,e2,w1,md,days,errs in rows:
    if ex>=base[0] and md<np.mean([d for d in base[3] if d is not None]):
        print("  %s, %d weeks, %.0f%% fall -> exact %d of 9, mean %.0f days after the trough month ends (current %.0f)"%(
            nm,w,100*pct,ex,md,np.mean([d for d in base[3] if d is not None])))
        print("    errors %s"%errs); print("    days   %s"%days); break
else: print("  none")
