"""Second-condition hunt, stage 1: window exposure of candidate confirming objects.
Exposure is the share of QUIET monthly observations (outside [peak-9m, trough+18m] of the thirteen)
on which a claims call would be confirmed, window six months back to thirty days forward -
the definition in lab/data/window_exposure.py. The gate is the shipped Sahm object's 5.8 per cent."""
import csv, numpy as np, pandas as pd
AL=os.path.expanduser("~/mnt/")+"Onset Detector Data/onset-detector-new-2026-08-23/27_realtime_vintages/alfred_all_vintages/"
PEAKS=['1948-11','1953-07','1957-08','1960-04','1969-12','1973-11','1980-01','1981-07','1990-07','2001-03','2007-12','2020-02','2023-07']
TROUGHS=['1949-10','1954-05','1958-04','1961-02','1970-11','1975-03','1980-07','1982-11','1991-03','2001-11','2009-06','2020-04','2024-08']
M=lambda s: pd.Timestamp(s+'-01')
def first_prints(series):
    """Monthly series of each month's FIRST published value, indexed by reference month."""
    rows=list(csv.reader(open(AL+series+"_all_vintages.csv"))); h=rows[0]
    dates=[pd.Timestamp(r[0]) for r in rows[1:]]
    out={}
    for j in range(1,len(h)):
        col=[rows[1+i][j] for i in range(len(dates))]
        idx=[i for i,v in enumerate(col) if v not in ('','.')]
        if not idx: continue
        m=dates[idx[-1]]
        if m not in out: out[m]=float(col[idx[-1]])
    return pd.Series(out).sort_index()
def quiet(idx):
    q=pd.Series(True,index=idx)
    for p,t in zip(PEAKS,TROUGHS):
        q[(idx>=M(p)-pd.DateOffset(months=9))&(idx<=M(t)+pd.DateOffset(months=18))]=False
    return q
def exposure(o,line):
    o=o.dropna(); q=quiet(o.index); hit=(o>=line)
    fwd=hit[::-1].rolling(1,min_periods=1).max()[::-1].astype(bool)
    back=hit.rolling(7,min_periods=1).max().astype(bool)
    return hit[q].mean()*100,(fwd|back)[q].mean()*100,int(q.sum())
FP={s:first_prints(s) for s in ("AWHMAN","INDPRO","PAYEMS","MANEMP","HOUST")}
for s,v in FP.items(): print(f"{s}: first prints {v.index[0]:%Y-%m} -> {v.index[-1]:%Y-%m}, {len(v)} months")
def forms(s,v):
    yield f"{s}: fall from trailing 12-month max, %", (v.rolling(12).max()/v-1)*100
    yield f"{s}: fall from trailing 6-month max, %", (v.rolling(6).max()/v-1)*100
    yield f"{s}: 3-month fall, %", -(v/v.shift(3)-1)*100
    yield f"{s}: 1-month fall, %", -(v/v.shift(1)-1)*100
print(f"\n{'object':52}{'line':>7}{'at line':>9}{'IN WINDOW':>11}{'quiet n':>9}")
keep=[]
for s,v in FP.items():
    for label,o in forms(s,v):
        for line in (0.2,0.3,0.5,0.75,1.0,1.5,2.0,2.5,3.0,4.0):
            at,win,n=exposure(o,line)
            if win<=5.8 and at>0:
                print(f"{label:52}{line:>7}{at:>8.1f}%{win:>10.1f}%{n:>9}")
                keep.append((label,line,win))
print(f"\ncandidates clearing the 5.8% gate: {len(keep)}")
