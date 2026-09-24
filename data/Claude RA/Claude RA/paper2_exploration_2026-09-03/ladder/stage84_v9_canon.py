"""Stage 84: v9 hazard under the CANONICAL quiet set (the one the machine sees:
no episode open), so the number is comparable with v7, v7.1, v7.2 and v8."""
exec(open("stage44_evt.py").read().split('print("\\n=== (B) EXTREME')[0])
from scipy import stats as sst
import numpy as np, pandas as pd
QUIET=(~allowed)&(~openmask)&(cal>=pd.Timestamp("1968-06-01"))
qy=pd.Series(cal[QUIET]).dt.year; NYR=qy.nunique()
share=pd.Series(cal[QUIET&GATE[12]]).dt.year.nunique()/NYR
def sd(s,lag):
    x=s.copy(); x.index=x.index+pd.Timedelta(days=lag); return x.reindex(cal).ffill().values.astype(float)
CL=np.nan_to_num(sd(r8,5),nan=-9)
def price(nm,thr,gated,floor=None):
    row=[c for c in CH if c[0]==nm][0]; _,st,lag,_,_,k0=row
    x=dl(st,lag)
    if k0>1: x=pd.Series(np.minimum(x.values,np.r_[np.nan,x.values[:-1]]),index=x.index)
    v0=x.reindex(cal).ffill().values.astype(float)
    base=QUIET&(GATE[12] if gated else np.ones(N,bool))
    s0=pd.Series(v0[base],index=cal[base]).dropna()
    a0=s0.groupby(s0.index.year).max(); a0=a0[s0.groupby(s0.index.year).size()>=60]
    c,loc,sc=sst.genextreme.fit(a0.values); p_unc=float(sst.genextreme.sf(thr,c,loc,sc))
    if floor is None: return p_unc,1.0
    m=base&(CL>=floor)
    yrs_with=pd.Series(cal[m]).dt.year.nunique() if m.sum() else 0
    fy=yrs_with/max(len(a0),1)
    # conditional exceedance: among qualifying days, how far does the statistic get?
    if m.sum()>200:
        s1=pd.Series(v0[m],index=cal[m]).dropna()
        a1=s1.groupby(s1.index.year).max(); a1=a1[s1.groupby(s1.index.year).size()>=10]
        if len(a1)>=10:
            c1,l1,sc1=sst.genextreme.fit(a1.values)
            return float(sst.genextreme.sf(thr,c1,l1,sc1))*min(fy,1.0), min(fy,1.0)
    return p_unc*min(fy,1.0), min(fy,1.0)
SPEC=[("Sahm fast",0.36,True,0.03),("IUR gap fast",0.40,True,0.03),("payrolls fast",0.18,True,0.03),
      ("housing fast",0.20,True,0.03),("bill fast",1.45,True,0.03),("Sahm backstop",0.55,False,0.12)]
print("canonical quiet years %d; gate armed in %.0f%%\n" % (NYR,100*share))
print("%-16s %-12s %-12s %-10s %s" % ("channel","v8 hazard","v9 hazard","yr-frac","cut"))
v8={}; v9={}
for nm,thr,g,fl in SPEC:
    p8,_=price(nm,thr,g,None); p9,fy=price(nm,thr,g,fl)
    m=share if g else (1-share); p8*=m; p9*=m
    v8[nm]=p8; v9[nm]=p9
    print("%-16s %-12.5f %-12.5f %-10.2f %s" % (nm,p8,p9,fy,("%.0f%%"%(100*(1-p9/p8))) if p8>0 else "-"))
u=lambda d: 1-np.prod([1-p for p in d.values()])
print("\n%-44s %-11s %-13s %-12s %s" % ("rule","union/yr","one every","6.5-yr","10-yr"))
for lab,val in [("v6",0.1239),("v7 (round 18)",0.0664),("v7.1",0.0459),("v7.2 (round 19)",0.0347),
                ("v8 (round 20)",u(v8)),("v9 (+ claims floor)",u(v9))]:
    print("%-44s %-11.4f 1 in %-9.0f %-12.0f%% %.0f%%" % (lab,val,1/val,100*(1-(1-val)**6.5),100*(1-(1-val)**10)))
for det in (0.867,0.955): print("detection %.3f x no false alarm over 6.5 yr = %.0f%%" % (det,100*det*(1-u(v9))**6.5))
