"""Stage 92: the 1981 call rests on one channel with the rule's thinnest margin.
Measure it exactly, then look for a FORM of the housing statistic that keeps the call
and widens the margin: other horizons, permits, starts-and-permits together."""
exec(open("stage46_v7.py").read().split("t6,l6=build")[0])
exec(open("stage44_evt.py").read().split("print(\"\\n=== (B) EXTREME")[0])
import numpy as np, pandas as pd
G=np.asarray(GATE[12],bool)
QC=(~allowed)&(~openmask)&(cal>=pd.Timestamp("1968-06-01"))
def sd(s,lag=0):
    x=s.copy(); x.index=x.index+pd.Timedelta(days=lag); return x.reindex(cal).ffill().values.astype(float)
CL=np.nan_to_num(sd(r8,5),nan=-9); CO=CL>=0.03
PK=[(pd.Timestamp(a),pd.Timestamp(b)) for a,b in T_P1]
def firstprint_ch(fn,h): return fpch(fn,h)
FORMS={}
for h in (2,3,4,5,6):
    FORMS["starts %dm"%h]=firstprint_ch("HOUST_all_vintages.csv",h)
    FORMS["permits %dm"%h]=firstprint_ch("PERMIT_all_vintages.csv",h)
def arr(series,k,th):
    return np.asarray(persist2(series,th*100) if False else None,bool) if False else None
def build_channel(series, th, k):
    """series is a first-print monthly change (as a fraction, negative = fall)."""
    a=(series<=-th)
    if k>1:
        for j in range(1,k): a = a & series.shift(j).le(-th)
    return np.asarray(D(a.fillna(False)),bool)
print("%-16s %-3s %8s %8s %8s %8s %s" % ("form","k","quietmax","1981 pk","line","margin","other recessions carried"))
best=[]
for nm,s in FORMS.items():
    for k in (1,2,3):
        # max-margin line from the quiet set and the 1981 window
        v=sd(-s)                                  # bigger = bigger fall
        if k>1:
            v=np.minimum.reduce([sd(-s.shift(j)) for j in range(k)])
        q=v[QC&CO&G]; q=q[np.isfinite(q)]
        w=v[(cal>=pd.Timestamp("1981-05-01"))&(cal<=pd.Timestamp("1981-09-30"))&G&CO]; w=w[np.isfinite(w)]
        if len(q)<300 or len(w)<5: continue
        qm=float(np.max(q)); pk=float(np.max(w))
        if pk<=qm: continue
        line=(qm+pk)/2; sdv=float(np.nanstd(q))
        ch=build_channel(s, line, k)&CO&G
        if (ch&QC).any(): continue
        got=[]
        for (p,t) in PK:
            m=ch&(cal>=p-pd.DateOffset(months=6))&(cal<=t)
            if m.any():
                d=cal[m][0]; got.append((str(p.date())[:7],(d.year-p.year)*12+(d.month-p.month)))
        if not any(g[0]=="1981-07" and abs(g[1])<=1 for g in got): continue
        best.append(((pk-qm)/sdv,nm,k,qm,pk,line,got))
best.sort(reverse=True)
for m,nm,k,qm,pk,line,got in best[:14]:
    print("%-16s %-3d %8.3f %8.3f %8.3f %8.3f %s" % (nm,k,qm,pk,line,pk-qm,got))
print("\ncurrent v9 channel: starts 3m, k=2, line 0.200 -> margin 0.006 (0.08 sd)")
