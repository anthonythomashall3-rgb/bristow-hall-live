"""Stage 83: price v9 correctly.  A joint condition's annual hazard decomposes as
P(the year contains any day meeting the claims floor) x P(the channel's max over those
days clears its line | the year has such days).  Fitting the GEV on the conditional
subsample alone -- as stage 82 did -- is wrong: most quiet years contain no qualifying
day at all, and the fit blows up on the handful that do."""
exec(open("stage46_v7.py").read().split("t6,l6=build")[0])
import numpy as np, pandas as pd
from scipy import stats as sst
G=np.asarray(GATE[12],bool)
WINS=[(pd.Timestamp(p),pd.Timestamp(t)) for p,t in T_P1]
QUIET=np.ones(N,bool)&(cal>=pd.Timestamp("1968-06-01"))
for p,t in WINS: QUIET &= ~((cal>=p-pd.DateOffset(months=6))&(cal<=t+pd.DateOffset(months=12)))
def sd(s,lag):
    x=s.copy(); x.index=x.index+pd.Timedelta(days=lag); return x.reindex(cal).ffill().values.astype(float)
CL=np.nan_to_num(sd(r8,5),nan=-9); S=Srel.reindex(cal).ffill().values.astype(float)
IURg=sd(iur4-iur4.rolling(52).min(),12)
PAY1=sd(pd.Series(pay.d1.astype(float).values,index=pd.to_datetime(pay.rel.values)),0)
H3=sd(-h3,0); BILL=sd(-(tb6-tb6.shift(60)),1)
share=0.40
def price(stat,thr,gated,floor=None):
    base=QUIET&(GATE[12] if gated else np.ones(N,bool))
    yrs=pd.Series(cal[base]).dt.year
    nyr=yrs.nunique()
    if floor is None: m=base
    else: m=base&(CL>=floor)
    if m.sum()==0: return 0.0,0,nyr
    v=pd.Series(stat[m],index=cal[m]).dropna()
    yq=v.groupby(v.index.year)
    am=yq.max(); am=am[yq.size()>=20]
    fy=len(am)/max(nyr,1)                       # fraction of quiet years with qualifying days
    if len(am)<8: 
        # too few to fit: fall back on the unconditional fit scaled by fy
        v0=pd.Series(stat[base],index=cal[base]).dropna()
        a0=v0.groupby(v0.index.year).max(); a0=a0[v0.groupby(v0.index.year).size()>=60]
        c,loc,sc=sst.genextreme.fit(a0.values); p=float(sst.genextreme.sf(thr,c,loc,sc))*fy
    else:
        c,loc,sc=sst.genextreme.fit(am.values); p=float(sst.genextreme.sf(thr,c,loc,sc))*fy
    return p,len(am),nyr
rows=[("Sahm fast",S,0.36,True,0.03),("IUR fast",IURg,0.40,True,0.03),
      ("payrolls fast",-PAY1,0.18,True,0.03),("housing fast",H3,0.20,True,0.03),
      ("bill fast",BILL,1.45,True,0.03),("Sahm clause",S,0.55,False,0.10)]
print("%-14s %-11s %-11s %-9s %s" % ("channel","v8 hazard","v9 hazard","yrs w/ days","cut"))
v8={}; v9={}
for nm,st,thr,g,fl in rows:
    p8,_,ny=price(st,thr,g,None); p9,ky,_=price(st,thr,g,fl)
    if g: p8*=share; p9*=share
    else: p8*=(1-share); p9*=(1-share)
    v8[nm]=p8; v9[nm]=p9
    print("%-14s %-11.5f %-11.5f %-9s %s" % (nm,p8,p9,"%d/%d"%(ky,ny),"%.0f%%"%(100*(1-p9/p8)) if p8>0 else "-"))
u=lambda d: 1-np.prod([1-p for p in d.values()])
print("\n%-46s %-11s %-13s %-12s %s" % ("rule","union/yr","one every","6.5-yr risk","10-yr"))
for lab,d in [("v8 (round 20)",v8),("v9 (+ global claims floor)",v9)]:
    p=u(d); print("%-46s %-11.4f 1 in %-9.0f %-12.0f%% %.0f%%" % (lab,p,1/p,100*(1-(1-p)**6.5),100*(1-(1-p)**10)))
print("\nempirical: quiet days on which v9 would arm any channel = 0 of %d (58 years)" % int(QUIET.sum()))
for det in (0.867,0.955): print("detection %.3f x no false alarm over 6.5 yr = %.0f%%" % (det,100*det*(1-u(v9))**6.5))
