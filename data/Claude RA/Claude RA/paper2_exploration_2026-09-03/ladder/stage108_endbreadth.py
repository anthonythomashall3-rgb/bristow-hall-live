"""Stage 108: a completely different end rule.  The present one finds the argmax of one
noisy weekly series, which is late by construction and moves when claims are revised.
Instead ask how many independent recession-sensitive series have TURNED off their worst
reading -- a breadth count, which no single series' revision can move."""
exec(open("stage46_v7.py").read().split("t6,l6=build")[0])
import numpy as np, pandas as pd, os
def L(p):
    try: return load(os.path.join(ODD,p))
    except Exception: return None
CAND={
 "initial claims 4wk":        (L("01_labor_unemployment/weekly/ICSA.csv"),"w","up"),
 "continued claims 4wk":      (L("01_labor_unemployment/weekly/CCSA.csv"),"w","up"),
 "insured unemployment rate": (L("01_labor_unemployment/weekly/IURSA.csv"),"w","up"),
 "unemployment rate":         (L("01_labor_unemployment/monthly/UNRATE.csv"),"m","up"),
 "U-6":                       (L("01_labor_unemployment/monthly/U6RATE.csv"),"m","up"),
 "mean duration":             (L("01_labor_unemployment/monthly/UEMPMEAN.csv"),"m","up"),
 "payrolls":                  (L("03_payroll_employment/monthly/PAYEMS.csv"),"m","dn"),
 "temp help":                 (L("03_payroll_employment/monthly/TEMPHELPS.csv"),"m","dn"),
 "manufacturing hours":       (L("04_hours_earnings/monthly/AWHMAN.csv"),"m","dn"),
 "aggregate hours":           (L("04_hours_earnings/monthly/AWHAETP.csv"),"m","dn"),
 "industrial production":     (L("09_output_production/monthly/INDPRO.csv"),"m","dn"),
 "housing starts":            (L("11_housing_construction/monthly/HOUST.csv"),"m","dn"),
 "building permits":          (L("11_housing_construction/monthly/PERMIT.csv"),"m","dn"),
 "real retail sales":         (L("10_consumption_retail/monthly/RRSFS.csv"),"m","dn"),
 "job openings":              (L("02_labor_demand_vacancies/monthly/JTSJOL.csv"),"m","dn"),
}
CAND={k:v for k,v in CAND.items() if v[0] is not None and len(v[0])>200}
print("series available for the breadth count:", len(CAND))
for k,(s,f,d) in sorted(CAND.items()): print("   %-26s %s .. %s  (%s, %s)" % (k,s.index[0].date(),s.index[-1].date(),f,d))
TR=[pd.Timestamp(t) for p,t in T_P1]
PKm=[pd.Timestamp(p) for p,t in T_P1]
print("\ncoverage at each NBER trough (how many of these series exist then):")
for t in TR:
    n=sum(1 for k,(s,f,d) in CAND.items() if s.index[0]<=t-pd.DateOffset(months=18) and s.index[-1]>=t)
    print("   %s : %d of %d" % (t.date(),n,len(CAND)))
