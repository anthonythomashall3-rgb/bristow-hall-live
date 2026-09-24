"""Stage 68: re-fit the extreme-value hazard at the tightened thresholds (v8 candidate)."""
exec(open("stage44_evt.py").read().split('print("\\n=== (B) EXTREME')[0])
from scipy import stats
import numpy as np, pandas as pd
def haz(nm, thr, gated, k=1):
    row=[c for c in CH if c[0]==nm]
    if not row: return None
    _,st,lag,_,g0,k0=row[0]
    x=dl(st,lag)
    if k0>1: x=pd.Series(np.minimum(x.values,np.r_[np.nan,x.values[:-1]]), index=x.index)
    v=x.reindex(cal).ffill()
    q=(~allowed)&(~openmask)&(cal>=pd.Timestamp("1968-06-01"))&(GATE[12] if gated else np.ones(N,bool))
    s=pd.Series(v.values[q], index=cal[q]).dropna()
    am=s.groupby(s.index.year).max(); am=am[s.groupby(s.index.year).size()>=60]
    if len(am)<12: return None
    c,loc,sc=stats.genextreme.fit(am.values)
    return float(stats.genextreme.sf(thr,c,loc,sc)), len(am), float(am.max())
print("names available:", [c[0] for c in CH])
qy=pd.Series(cal[(~allowed)&(~openmask)&(cal>=pd.Timestamp("1968-06-01"))]).dt.year
gy=pd.Series(cal[(~allowed)&(~openmask)&GATE[12]&(cal>=pd.Timestamp("1968-06-01"))]).dt.year
share=gy.nunique()/qy.nunique()
print("gate armed share of quiet years: %.2f" % share)

SPEC=[("Sahm fast",0.35,0.36,True),("IUR gap fast",0.40,0.40,True),
      ("payrolls fast",0.10,0.18,True),("housing fast",0.20,0.20,True),
      ("bill fast",1.43,1.45,True),("Sahm backstop",0.55,0.55,False),
      ("VIX lane",17.425,22,False)]
print("\n%-16s %-14s %-14s %-12s %s" % ("channel","v7.2 thresh","v8 thresh","v7.2 hazard","v8 hazard"))
old={}; new={}
for nm,t0,t1,gated in SPEC:
    a=haz(nm,t0,gated); b=haz(nm,t1,gated)
    if a is None: print("%-16s (no quiet fit)"%nm); continue
    p0,p1=a[0],b[0]
    if gated: p0*=share; p1*=share
    if nm=="Sahm backstop": p0*=(1-share); p1*=(1-share)
    if nm=="VIX lane": p0=p1=0.0     # lane cannot open alone; void mechanism
    old[nm]=p0; new[nm]=p1
    print("%-16s %-14s %-14s %-12.5f %.5f" % (nm,t0,t1,p0,p1))
DROPPED={"IUR backstop":0.00029*(1-share),"housing backstop":0.00319*(1-share),
         "claims backstop":0.00133,"IP backstop":0.0,"Baa lane":0.0}
u=lambda d: 1-np.prod([1-p for p in d.values()])
v72=dict(old); v72.update(DROPPED)
print("\n%-46s %-11s %-14s %-13s %s" % ("rule","union/yr","one every","6.5-yr risk","10-yr"))
for lab,d in [("v7.2 (round 19)",v72),("v8: 5 dead channels deleted",old),
              ("v8: + every free tightening",new)]:
    p=u(d); print("%-46s %-11.4f 1 in %-11.0f %-13.0f%% %.0f%%" % (lab,p,1/p,100*(1-(1-p)**6.5),100*(1-(1-p)**10)))
print("\nv8 residual hazard by channel, largest first:")
for k,v in sorted(new.items(), key=lambda kv:-kv[1]):
    print("   %-16s %.5f/yr%s" % (k,v,("  1 in %.0f yr"%(1/v)) if v>0 else ""))
for det in (0.867,0.955):
    print("detection %.3f x no false alarm over 6.5 yr = %.0f%%" % (det,100*det*(1-u(new))**6.5))
