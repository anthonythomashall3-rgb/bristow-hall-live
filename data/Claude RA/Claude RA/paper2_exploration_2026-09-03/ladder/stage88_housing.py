"""Stage 88: the housing channel is now v9's largest single exposure (0.0101/yr of a
0.0167 union).  Three questions: is that fitted number stable; can building permits do
the job with a wider margin than starts; and will a channel-specific claims floor help."""
exec(open("stage44_evt.py").read().split(chr(39)+chr(39)+chr(39))[0] if False else open("stage46_v7.py").read().split("t6,l6=build")[0])
exec(open("stage44_evt.py").read().split("print(\"\\n=== (B) EXTREME")[0])
import numpy as np, pandas as pd
from scipy import stats as sst
G=np.asarray(GATE[12],bool); NG=~G
WINS=[(pd.Timestamp(p),pd.Timestamp(t)) for p,t in T_P1]
def sd(s,lag=0):
    x=s.copy(); x.index=x.index+pd.Timedelta(days=lag); return x.reindex(cal).ffill().values.astype(float)
CL=np.nan_to_num(sd(r8,5),nan=-9)
p3=fpch("PERMIT_all_vintages.csv",3)
H=sd(-h3); P=sd(-p3)
def twice(v):  # the reading and the one before it both over the line
    return np.minimum(v, np.r_[np.nan, v[:-1]])
QUIET=(~allowed)&(~openmask)&(cal>=pd.Timestamp("1968-06-01"))
def report(nm, stat, gated=True, floor=None):
    m=QUIET&(GATE[12] if gated else np.ones(N,bool))
    if floor is not None: m=m&(CL>=floor)
    v=pd.Series(stat[m],index=cal[m]).dropna()
    qm=float(v.max()) if len(v) else float("nan")
    pk={}
    for (a,b) in WINS:
        w=(cal>=a-pd.DateOffset(months=6))&(cal<=b)&(GATE[12] if gated else np.ones(N,bool))
        if floor is not None: w=w&(CL>=floor)
        x=pd.Series(stat[w],index=cal[w]).dropna()
        if len(x): pk[str(a.date())[:7]]=float(x.max())
    carried={k:val for k,val in pk.items() if val>qm}
    return qm, pk, carried, len(v)
for nm,stat in [("starts, 3m fall x2",twice(H)),("permits, 3m fall x2",twice(P)),
                ("starts, 3m fall x1",H),("permits, 3m fall x1",P)]:
    for fl,lab in [(None,"no floor"),(0.03,"claims>=3%"),(0.05,"claims>=5%")]:
        qm,pk,carr,nq=report(nm,stat,True,fl)
        print("%-22s %-11s gated quiet max %6.3f | carries %s" % (nm,lab,qm,sorted(carr)))
    print()
print("what each series reads in the 1981 window (gated):")
for nm,stat in [("starts x2",twice(H)),("permits x2",twice(P))]:
    w=(cal>=pd.Timestamp("1981-01-01"))&(cal<=pd.Timestamp("1982-11-01"))&G
    x=pd.Series(stat[w],index=cal[w]).dropna()
    print("  %-10s %s" % (nm, ("max %.3f on %s"%(x.max(),x.idxmax().date())) if len(x) else "no gated observations in that window"))
