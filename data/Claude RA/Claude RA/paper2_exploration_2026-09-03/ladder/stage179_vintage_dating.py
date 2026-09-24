"""Stage 179: dating on first prints.  The dating step has so far read the current value of each
coincident series while modelling only the publication LAG.  ALFRED holds every vintage of all
four, so the first print of each month can be used instead -- the number the dating committee
itself would have seen.  Memo 29 found the real-time trough better than the revised one; this
tests whether using genuine first prints makes it better still."""
exec(open("stage124_datemonth.py").read().split("def report(")[0])
import numpy as np, pandas as pd, os
V=os.path.expanduser("~/mnt/Onset Detector Data/onset-detector-new-2026-08-23/27_realtime_vintages/alfred_all_vintages/")
SRC={"payrolls":"PAYEMS","industrial production":"INDPRO",
     "real income less transfers":"W875RX1","real manufacturing and trade sales":"CMRMTSPL"}
FP={}
for nm,sid in SRC.items():
    p=V+sid+"_all_vintages.csv"
    if not os.path.exists(p): print("missing",sid); continue
    d=pd.read_csv(p,low_memory=False); d["date"]=pd.to_datetime(d["date"]); d=d.set_index("date")
    cols=[c for c in d.columns if c.startswith(sid+"_")]
    vd=pd.to_datetime([c.split("_")[1] for c in cols],format="%Y%m%d")
    vals=d[cols].values
    out={}
    for i,mo in enumerate(d.index):
        row=vals[i]
        j=int(np.searchsorted(vd,mo))
        while j<len(cols) and not np.isfinite(row[j]): j+=1
        if j<len(cols): out[mo]=(float(row[j]),vd[j])
    FP[nm]=pd.Series({k:v[0] for k,v in out.items()}).sort_index()
    print("%-36s first prints %d months, from %s"%(nm,len(FP[nm]),str(FP[nm].index.min().date())))
ENDC2=[pd.Timestamp(x) for x in ["1970-12-17","1975-05-08","1980-07-24","1982-11-18","1991-05-09",
                                 "2001-12-13","2009-05-14","2020-05-28","2024-09-26"]]
def med(src,names,a,back,fwd,kind,how="nearest"):
    o=[]
    for nm in names:
        s=src.get(nm)
        if s is None: continue
        w=s[(s.index>=a-pd.Timedelta(days=back))&(s.index<=a+pd.Timedelta(days=fwd))].dropna()
        if len(w)<6: continue
        o.append((w.idxmax() if kind=="max" else w.idxmin()).to_period("M").ordinal)
    if not o: return None
    x=float(np.median(o))
    return pd.Period(ordinal=(int(np.floor(x)) if how=="earlier" else int(round(x))),freq="M")
ALL4=list(SRC); FAST=[n for n in ALL4 if n!="real manufacturing and trade sales"]
print()
for lab,src in [("current vintage",M),("first prints",FP)]:
    for pn,names in [("all four",ALL4),("the fast three",FAST)]:
        mo=[]
        for i,a in enumerate(ALARM):
            d=med(src,names,a,180,180,"max","earlier")
            mo.append(None if d is None else (d-pd.Period(PKM[i],"M")).n)
        ok=[x for x in mo if x is not None]
        print("PEAK   %-16s %-16s exact %d of 9, within one month %d  %s"%(lab,pn,sum(1 for x in ok if x==0),sum(1 for x in ok if abs(x)<=1),mo))
    for pn,names in [("all four",ALL4),("the fast three",FAST)]:
        mo=[]
        for i,a in enumerate(ENDC2):
            d=med(src,names,a,300,30,"min","nearest")
            mo.append(None if d is None else (d-pd.Period(TRM[i],"M")).n)
        ok=[x for x in mo if x is not None]
        print("TROUGH %-16s %-16s exact %d of 9, within one month %d  %s"%(lab,pn,sum(1 for x in ok if x==0),sum(1 for x in ok if abs(x)<=1),mo))
    print()
