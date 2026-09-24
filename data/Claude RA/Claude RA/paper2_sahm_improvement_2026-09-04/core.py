import csv, statistics as st
V="/sessions/rcw-01xbsq1sgk1kphgfxvqjpnj7/mnt/Onset Detector Data/onset-detector-new-2026-08-23/27_realtime_vintages/alfred_all_vintages/UNRATE_all_vintages.csv"
rows=list(csv.reader(open(V))); hdr=rows[0]; dates=[r[0][:7] for r in rows[1:]]
VIN=[h.split('_')[1] for h in hdr[1:]]
VIN=[f"{v[:4]}-{v[4:6]}-{v[6:]}" for v in VIN]
COL=[[ (r[j] if r[j] not in ('','.') else None) for r in rows[1:]] for j in range(1,len(hdr))]
def series(j):
    out=[]
    for i,d in enumerate(dates):
        v=COL[j][i]
        if v is None: continue
        out.append((d,float(v)))
    return out
def mo(s):
    y,m=map(int,s.split('-')[:2]); return y*12+m
REC=[("1960-04","1961-02"),("1969-12","1970-11"),("1973-11","1975-03"),("1980-01","1980-07"),
("1981-07","1982-11"),("1990-07","1991-03"),("2001-03","2001-11"),("2007-12","2009-06"),
("2020-02","2020-04"),("2024-04","2024-08")]
def indicator(s,k,L):
    """S at the last month of vintage series s: k-month MA minus min of the L prior k-month MAs."""
    if len(s)<k+L: return None
    ma=[sum(v for _,v in s[i-k+1:i+1])/k for i in range(k-1,len(s))]
    if len(ma)<L+1: return None
    return ma[-1]-min(ma[-1-L:-1])
def run(k=3,L=12,thr=0.50,strict=False,persist=1):
    """Return list of (vintage_date, latest_month, S) where the rule fires."""
    fires=[];streak=0
    for j in range(len(VIN)):
        s=series(j)
        if not s: continue
        S=indicator(s,k,L)
        if S is None: continue
        hit=(S>thr) if strict else (S>=thr-1e-9)
        streak=streak+1 if hit else 0
        if streak>=persist: fires.append((VIN[j],s[-1][0],round(S,4)))
    return fires
def episodes(fires,gap=1):
    """Group consecutive-vintage fires into episodes; return (first_vintage,first_month,last_month)."""
    eps=[]
    for f in fires:
        if eps and mo(f[1])-mo(eps[-1][2])<=gap: eps[-1][2]=f[1]
        else: eps.append([f[0],f[1],f[1]])
    return eps
def score(eps):
    """Match episodes to recessions; count onsets, lags, and standalone false alarms."""
    lags={};used=set()
    for p,t in REC:
        best=None
        for i,e in enumerate(eps):
            if i in used: continue
            vm=mo(e[0][:7])
            if mo(p)-6<=vm<=mo(t)+6:
                best=(i,vm-mo(p)); break
        if best: used.add(best[0]); lags[p]=best[1]
    false=[]
    for i,e in enumerate(eps):
        if i in used: continue
        vm=mo(e[0][:7])
        if any(mo(p)-6<=vm<=mo(t)+12 for p,t in REC): continue   # tails / early warnings
        false.append(e[0])
    return lags,false
