#!/usr/bin/env python3
"""CH-R47 addendum: smoothing/debounce noise reduction + daily-vs-monthly lead. read-only."""
import csv,json,math
import numpy as np
from datetime import date,timedelta
from collections import defaultdict
rows=list(csv.DictReader(open("research/daily_edge_sim_v1.csv")))
dts=[date.fromisoformat(r["date"]) for r in rows]
def col(name):
    return np.array([float(r[name]) if r[name] else np.nan for r in rows])
EW=col("ew_composite"); ERC=col("erc_composite")
N=len(dts)
RECWIN={'2001':(date(2001,3,1),date(2001,11,30)),'2008':(date(2007,12,1),date(2009,6,30)),
        '2020':(date(2020,2,1),date(2020,4,30))}
ONSET={'2001':date(2001,3,1),'2008':date(2007,12,1),'2020':date(2020,2,1)}
def in_rec(dt):
    return any(a<=dt<=b for a,b in RECWIN.values())

def trail_ma(a,win):
    out=np.full(N,np.nan)
    for i in range(N):
        seg=a[max(0,i-win+1):i+1]; seg=seg[~np.isnan(seg)]
        if len(seg)>=max(5,win//2): out[i]=seg.mean()
    return out

def edges_and_fp(comp,thr):
    prev=False; edges=[]
    for i in range(N):
        if np.isnan(comp[i]): continue
        cur=comp[i]>=thr
        if cur and not prev: edges.append(dts[i])
        prev=cur
    fp=sum(1 for e in edges if not in_rec(e) and not any(0<=(a-e).days<=548 for a,b in RECWIN.values()))
    return len(edges),fp

def first_cross(comp,thr,lo,hi):
    for i in range(N):
        if lo<=dts[i]<=hi and not np.isnan(comp[i]) and comp[i]>=thr: return dts[i]
    return None

out=open("research/ch_r47_smooth.txt","w")
for win in (21,63):
    EWs=trail_ma(EW,win); ERCs=trail_ma(ERC,win)
    out.write(f"\n===== TRAILING {win}-DAY MEAN =====\n")
    for comp,lab in ((EWs,f"EW.ma{win}"),(ERCs,f"ERC.ma{win}")):
        for thr in (1.0,1.5):
            ne,fp=edges_and_fp(comp,thr)
            out.write(f"  {lab} thr={thr}: rising_edges={ne} false_pos={fp}\n")
    # per-episode lead on smoothed EW
    for thr in (1.0,1.5):
        for ep,onset in ONSET.items():
            xd=first_cross(EWs,thr,onset-timedelta(days=730),onset)
            out.write(f"  EW.ma{win} thr={thr} {ep}: cross={xd} lead_days={ (onset-xd).days if xd else None}\n")

# daily vs monthly-resampled lead (smoothed 21d EW) — does daily cross earlier than month-end?
EWs=trail_ma(EW,21)
# month-end series: last obs each month
bym=defaultdict(list)
for i in range(N):
    if not np.isnan(EWs[i]): bym[(dts[i].year,dts[i].month)].append((dts[i],EWs[i]))
mend={k:sorted(v)[-1] for k,v in bym.items()}   # (date,val)
def monthly_first_cross(thr,lo,hi):
    for k in sorted(mend):
        d,v=mend[k]
        if lo<=d<=hi and v>=thr: return d
    return None
out.write("\n===== DAILY vs MONTHLY-RESAMPLED lead (EW.ma21, thr=1.0) =====\n")
for ep,onset in ONSET.items():
    lo=onset-timedelta(days=730)
    dd=first_cross(EWs,1.0,lo,onset); mm=monthly_first_cross(1.0,lo,onset)
    gap=(mm-dd).days if (dd and mm) else None
    out.write(f"  {ep}: daily_cross={dd} monthly_cross={mm} daily_edge_days={gap}\n")
out.close()
print(open("research/ch_r47_smooth.txt").read())
