"""Stage 124: dating by the coincident series the dating committee itself watches.  The alarm
and the date are separated: the alarm is whatever the machine fired on, and the date is then
placed by taking the turning point of a monthly coincident aggregate inside a window anchored
on that alarm.  If the aggregate names the right month, the day error is zero by convention:
the recession's first day is the first day of the month after the peak month."""
exec(open("stage106_v11.py").read().split('eps,l,e,t,f,n,arm,lv,co,cco=machine()')[0])
import numpy as np, pandas as pd
PKM=[p for p,t in T_P1]; TRM=[t for p,t in T_P1]
FIRST=[(pd.Period(p,"M")+1).to_timestamp() for p in PKM]
LAST =[(pd.Period(t,"M")+1).to_timestamp() for t in TRM]
ALARM=[pd.Timestamp(x) for x in ["1969-10-06","1973-10-25","1980-01-03","1981-08-18","1990-08-03",
                                 "2001-02-02","2008-01-04","2020-02-28","2024-05-03"]]
ENDC =[pd.Timestamp(x) for x in ["1971-01-01","1975-06-13","1980-08-01","1982-12-10","1991-06-07",
                                 "2002-01-04","2009-06-05","2020-06-05","2024-09-27"]]
M={}
def L(rel,nm):
    p=ODD+rel
    try: M[nm]=load(p)
    except Exception as e: pass
L("03_payroll_employment/monthly/PAYEMS.csv","payrolls")
L("03_payroll_employment/monthly/CE16OV.csv","household employment")
L("03_payroll_employment/monthly/MANEMP.csv","manufacturing employment")
L("03_payroll_employment/monthly/TEMPHELPS.csv","temporary help")
L("03_payroll_employment/monthly/AWHAETP.csv","average weekly hours")
L("04_hours_earnings/monthly/AWHMAN.csv","factory hours")
L("09_output_production/monthly/INDPRO.csv","industrial production")
L("09_output_production/monthly/IPMAN.csv","manufacturing output")
L("09_output_production/monthly/TCU.csv","capacity use")
L("10_consumption_retail/monthly/W875RX1.csv","real income less transfers")
L("10_consumption_retail/monthly/PCEC96.csv","real consumption")
L("10_consumption_retail/monthly/RSAFS.csv","retail sales")
L("21_other_macro/monthly/CMRMTSPL.csv","real manufacturing and trade sales")
L("01_labor_unemployment/monthly/EMRATIO.csv","employment-population ratio")
ads=pd.read_csv(ODD+"25_fred_daily_weekly/other_daily/ads_index_current.csv",parse_dates=["date"]).set_index("date")["ads"]
M["ADS (monthly mean)"]=ads.resample("MS").mean()
print("monthly coincident objects loaded:", len(M))
def month_of(s, lo, hi, kind):
    w=s[(s.index>=lo)&(s.index<=hi)].dropna()
    if len(w)<6: return None
    return (w.idxmax() if kind=="max" else w.idxmin())
def report(title, objs, anchors, targets, kind, back, fwd):
    rows=[]
    for nm,s in objs.items():
        ds=[]; mo=[]
        for i,a in enumerate(anchors):
            d=month_of(s,a-pd.Timedelta(days=back),a+pd.Timedelta(days=fwd),kind)
            if d is None: ds.append(np.nan); mo.append(np.nan); continue
            bnd=(d.to_period("M")+1).to_timestamp()
            ds.append((bnd-targets[i]).days); mo.append((d.to_period("M")-pd.Period(PKM[i] if kind=="max" else TRM[i],"M")).n)
        v=[x for x in ds if x==x]
        if len(v)<9: continue
        rows.append((float(np.mean(np.abs(v))),sum(1 for x in v if abs(x)<=7),nm,[int(x) for x in ds],[int(x) for x in mo]))
    rows.sort()
    print("\n%s  (window: %d days back, %d forward from the machine's own call)"%(title,back,fwd))
    print("%-36s %-8s %-7s %s"%("object","mean|d|","<=7d","months from the reference turning point"))
    for a,c,nm,ds,mo in rows[:16]: print("%-36s %-8.1f %-7d %s"%(nm,a,c,mo))
    return rows
for back,fwd in [(365,90),(540,120),(270,60),(180,180)]:
    report("PEAK month",M,ALARM,FIRST,"max",back,fwd)
for back,fwd in [(365,180),(540,240),(270,120)]:
    report("TROUGH month",M,ENDC,LAST,"min",back,fwd)
