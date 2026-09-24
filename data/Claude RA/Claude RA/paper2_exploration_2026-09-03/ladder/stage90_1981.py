"""Stage 90: July 1981 is carried by one channel -- housing starts -- whose margin
(0.006 on a 0.200 line, 0.08 sd) is the thinnest in the whole rule.  Search for a second
carrier: any statistic that calls 1981 within a month of the peak, gated, with zero
crossings on the canonical quiet set and a bigger margin than housing's."""
exec(open("stage46_v7.py").read().split("t6,l6=build")[0])
exec(open("stage44_evt.py").read().split("print(\"\\n=== (B) EXTREME")[0])
import numpy as np, pandas as pd, os, glob
G=np.asarray(GATE[12],bool)
QC=(~allowed)&(~openmask)&(cal>=pd.Timestamp("1968-06-01"))
WIN=(cal>=pd.Timestamp("1981-06-01"))&(cal<=pd.Timestamp("1981-08-31"))&G
def sd(s,lag=0):
    x=s.copy(); x.index=x.index+pd.Timedelta(days=lag); return x.reindex(cal).ffill().values.astype(float)
CL=np.nan_to_num(sd(r8,5),nan=-9); CO=CL>=0.03
cands={}
# weekly / monthly labour and rate material already loaded by the harness
def add(nm, arr): 
    a=np.asarray(arr,dtype=float)
    if np.isfinite(a).sum()>2000: cands[nm]=a
add("IUR 4wk gap", sd(iur4-iur4.rolling(52).min(),12))
add("IUR 8wk gap", sd(iur8-iur8.rolling(52).min(),12))
add("claims 8wk ratio", sd(r8,5))
add("claims 4wk ratio", sd(r4,5) if "r4" in dir() else sd(r8,5))
add("Sahm", Srel.reindex(cal).ffill().values.astype(float))
add("bill 60d fall", sd(-(tb6-tb6.shift(60)),1))
add("bill 90d fall", sd(-(tb6-tb6.shift(90)),1))
add("bill 120d fall", sd(-(tb6-tb6.shift(120)),1))
# extra daily/weekly series saved in data_fetched
BASE=os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03/data_fetched")
files=glob.glob(BASE+"/fred_daily/*.csv")+glob.glob(BASE+"/fred_weekly/*.csv")+glob.glob(BASE+"/extra/*.csv")
print("scanning",len(files),"saved daily/weekly series plus the core labour set")
def load1(p):
    try:
        x=pd.read_csv(p); x.columns=["date","v"]; x["date"]=pd.to_datetime(x["date"])
        x=x[pd.to_numeric(x["v"],errors="coerce").notna()]
        s=pd.Series(x["v"].astype(float).values,index=pd.DatetimeIndex(x["date"].values)).sort_index()
        return s[~s.index.duplicated()]
    except Exception: return None
for p in files:
    s=load1(p)
    if s is None or len(s)<3000 or s.index[0]>pd.Timestamp("1980-01-01"): continue
    nm=os.path.basename(p)[:-4]
    for lab,st in [("%s 60d rise"%nm, s-s.shift(60)), ("%s 60d fall"%nm, -(s-s.shift(60))),
                   ("%s 120d rise"%nm, s-s.shift(120)), ("%s 120d fall"%nm, -(s-s.shift(120)))]:
        add(lab, sd(st,1))
print("candidate statistics:",len(cands))
rows=[]
for nm,v in cands.items():
    q=v[QC&CO]; q=q[np.isfinite(q)]
    w=v[WIN&CO]; w=w[np.isfinite(w)]
    if len(q)<500 or len(w)<10: continue
    qm=float(np.max(q)); pk=float(np.max(w))
    if pk<=qm: continue
    sd_=float(np.nanstd(q))
    if sd_<=0: continue
    rows.append(((pk-qm)/sd_, nm, qm, pk, (qm+pk)/2))
rows.sort(reverse=True)
print("\n%-42s %9s %9s %9s %s" % ("statistic","quiet max","1981 peak","line","margin (sd)"))
for m,nm,qm,pk,line in rows[:15]:
    print("%-42s %9.3f %9.3f %9.3f %.2f" % (nm,qm,pk,line,m))
if not rows: print("  nothing clears its own quiet maximum in the 1981 window")
