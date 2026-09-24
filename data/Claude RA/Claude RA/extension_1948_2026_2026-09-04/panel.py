"""Onset-side extension back to 1948. Monthly, release-stamped where vintages exist.
Channels: Sahm (UNRATE), payrolls 1-month fall, housing starts 3-month fall x2, IP 3-month fall x2.
Gate: 10y-1y monthly spread negative in any of the prior 12 months (available from Apr 1953)."""
import csv, glob, os
AL="/sessions/rcw-01xbsq1sgk1kphgfxvqjpnj7/mnt/Onset Detector Data/onset-detector-new-2026-08-23/27_realtime_vintages/alfred_all_vintages/"
P1=glob.glob("/sessions/rcw-01xbsq1sgk1kphgfxvqjpnj7/cmp/p1arch/**/",recursive=True)
def cur(name):
    f=[p+name for p in P1 if os.path.exists(p+name)][0]
    return {a[:7]:float(b) for a,b in list(csv.reader(open(f)))[1:] if b not in ('','.')}
def vintages(series):
    """[(vintage_date, {month: value})] for every ALFRED vintage of `series`."""
    rows=list(csv.reader(open(AL+series+"_all_vintages.csv"))); h=rows[0]
    dates=[r[0][:7] for r in rows[1:]]
    out=[]
    for j in range(1,len(h)):
        v=h[j].split('_')[1]; vd=f"{v[:4]}-{v[4:6]}-{v[6:]}"
        d={}
        for i,m in enumerate(dates):
            x=rows[1+i][j]
            if x not in ('','.'): d[m]=float(x)
        if d: out.append((vd,d))
    return out
def mo(s):
    y,m=map(int,s.split('-')[:2]); return y*12+m
def addm(s,k):
    n=mo(s)+k; return f"{(n-1)//12:04d}-{(n-1)%12+1:02d}"
def sahm(d,m,kc=3,kb=3,L=12):
    ms=[addm(m,-i) for i in range(0,kc)]
    if any(x not in d for x in ms): return None
    curm=sum(d[x] for x in ms)/kc
    base=[]
    for j in range(1,L+1):
        w=[addm(m,-j-i) for i in range(0,kb)]
        if any(x not in d for x in w): return None
        base.append(sum(d[x] for x in w)/kb)
    return curm-min(base)
def pct_fall(d,m,k):
    a,b=addm(m,-k),m
    if a not in d or b not in d or d[a]==0: return None
    return 100*(d[b]/d[a]-1)
