"""Stage 95: apply round 22's method to the two remaining weak/underused channels.
(a) the Sahm channel -- thinnest margin left (0.027 on 0.36) and 3/4 of the residual risk;
(b) the insured-unemployment channel -- 2.37 sd of UNUSED margin, which can be spent on speed.
Sweep windows, lookbacks, confirming prints and lines.  Keep only forms that never arm on
the canonical quiet set with the 3% claims floor, and report the call date each would give."""
exec(open("stage46_v7.py").read().split("t6,l6=build")[0])
exec(open("stage44_evt.py").read().split("print(\"\\n=== (B) EXTREME")[0])
import numpy as np, pandas as pd, itertools
G=np.asarray(GATE[12],bool)
QC=(~allowed)&(~openmask)&(cal>=pd.Timestamp("1968-06-01"))
def sd(s,lag=0):
    x=s.copy(); x.index=x.index+pd.Timedelta(days=lag); return x.reindex(cal).ffill().values.astype(float)
CL=np.nan_to_num(sd(r8,5),nan=-9); CO=CL>=0.03
PK=[(pd.Timestamp(a),pd.Timestamp(b)) for a,b in T_P1]
CUR={"1969-12":"1969-10-06","1973-11":"1973-10-25","1980-01":"1980-01-03","1981-07":"1981-08-18",
     "1990-07":"1990-08-03","2001-03":"2001-02-02","2007-12":"2008-01-04","2020-02":"2020-02-28","2024-04":"2024-05-03"}
def score_form(arr, name):
    a=np.asarray(arr,bool)&CO&G
    if (a&QC).any(): return None
    out={}
    for (p,t) in PK:
        m=a&(cal>=p-pd.DateOffset(months=6))&(cal<=t)
        if m.any(): out[str(p.date())[:7]]=cal[m][0]
    return out
def gain(out):
    g=[]
    for k,v in out.items():
        cur=pd.Timestamp(CUR[k]); d=(v-cur).days
        if d<0: g.append((k,d,str(v.date())))
    return g
# ---------- (a) Sahm forms ----------
u=load(ODD+"01_labor_unemployment/monthly/UNRATE.csv") if False else None
print("=== Sahm-family forms (first prints) ===")
res=[]
S=Srel   # the standard 3-month mean less the min of the prior 12 monthly 3-month means
# rebuild variants directly from the first-print unemployment series behind Srel
fp=Srel.copy()
for th in [0.30,0.33,0.36,0.40,0.45,0.50]:
    for k in (1,2):
        a=(fp>=th-1e-9)
        for j in range(1,k): a=a & fp.shift(j).ge(th-1e-9)
        o=score_form(D(a.fillna(False)), "sahm")
        if o is None: continue
        res.append((th,k,o))
for th,k,o in res:
    q=pd.Series(Srel.reindex(cal).ffill().values.astype(float)[QC&CO&G]).dropna()
    print("  Sahm >= %.2f x%d : carries %s | earlier than v10: %s" %
          (th,k,sorted(o),gain(o) if gain(o) else "none"))
# ---------- (b) insured-unemployment forms ----------
print("\n=== insured-unemployment forms (weekly, known +12 days) ===")
best=[]
for wk_avg in (2,4,8,13):
    ma=iur.rolling(wk_avg).mean()
    for look in (26,52,78):
        gapser=ma-ma.rolling(look).min()
        v=sd(gapser,12)
        q=v[QC&CO&G]; q=q[np.isfinite(q)]
        if len(q)<300: continue
        qm=float(np.max(q))
        for th in [round(qm+x,3) for x in (0.02,0.05,0.10,0.15,0.20)]:
            a=np.asarray(v>=th,bool)
            o=score_form(a,"iur")
            if o is None or not o: continue
            gg=gain(o)
            best.append((sum(-d for _,d,_ in gg), wk_avg, look, th, qm, sorted(o), gg))
best.sort(reverse=True)
for tot,w,lk,th,qm,carried,gg in best[:12]:
    print("  %2d-wk avg over %2d-wk min, line %.3f (quiet max %.3f) : carries %s" % (w,lk,th,qm,carried))
    if gg: print("       EARLIER: %s   (total %d days)" % (gg,tot))
