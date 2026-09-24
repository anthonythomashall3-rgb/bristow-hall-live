"""Stage 136: the hazard of the scale-free rule.  Because the trigger is one continuous
statistic -- the largest z across the channels -- extreme value theory applies to it directly,
and the estimate is not circular in the way a multiple of the sample maximum would be."""
exec(open("stage128_ztwolane.py").read().split("def machine(c,c2")[0])
import numpy as np, pandas as pd
from scipy import stats as sst
def haz(v,mask,c,label):
    s=pd.Series(v[mask],index=cal[mask]).replace(-99.0,np.nan).dropna()
    am=s.groupby(s.index.year).max(); am=am[s.groupby(s.index.year).size()>=30]
    cpar,loc,sc=sst.genextreme.fit(am.values)
    p=float(sst.genextreme.sf(c,cpar,loc,sc))
    yrs=len(am)
    share=float(mask.sum())/float(QC.sum())
    print("%-26s quiet years %-4d annual max: median %.2f max %.2f | GEV shape %+.2f | P(exceed %.2f) %.5f/yr"%(
        label,yrs,float(np.median(am)),float(am.max()),cpar,c,p))
    return p*share, yrs
print("EXPOSURE-WEIGHTED HAZARD OF THE SCALE-FREE RULE")
for c,c2 in [(3.5,8.0),(4.25,8.0),(5.0,10.0),(6.0,12.0)]:
    pg,yg=haz(ZG,QC&G&CO,c,"gated lane c=%.2f"%c)
    pn,yn=haz(ZN,QC&NG&CCO,c2,"open lane c2=%.2f"%c2)
    u=1-(1-pg)*(1-pn)
    print("  union %.5f/yr -> one in %.0f years | over 6.5 years %.1f%% | over 10 years %.1f%%\n"%(u,1/u if u>0 else float('inf'),100*(1-(1-u)**6.5),100*(1-(1-u)**10)))
print("empirical: armed quiet days at each setting")
for c,c2 in [(3.5,8.0),(4.25,8.0),(5.0,10.0),(6.0,12.0)]:
    a=int((((ZG>=c)&G&CO)|((ZN>=c2)&NG&CCO))&QC).sum() if False else int(((((ZG>=c)&G&CO)|((ZN>=c2)&NG&CCO))&QC).sum())
    print("  c=%.2f c2=%.2f -> %d armed quiet days out of %d"%(c,c2,a,int(QC.sum())))
ny=pd.Series(cal[QC]).dt.year.nunique()
print("\nrule of three on %d quiet years with no false alarm: at most %.2f/yr at 95%% confidence (one in %.0f years)"%(ny,3.0/ny,ny/3.0))
print("exact one-sided 95%% upper bound on the per-year rate: %.3f"%(1-0.05**(1.0/ny)))
