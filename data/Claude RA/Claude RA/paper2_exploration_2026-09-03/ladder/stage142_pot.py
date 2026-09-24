"""Stage 142: hazard by peaks over threshold.  Fitting a generalised extreme value law to
seventeen annual maxima is unstable, and for the widest-margin rules it returns a bounded tail
that assigns the line zero probability -- which is not a defensible answer.  The standard
alternative is a generalised Pareto fit to the exceedances of a lower threshold, which uses
hundreds of observations rather than seventeen and extrapolates smoothly."""
exec(open("stage128_ztwolane.py").read().split("def machine(c,c2")[0])
import numpy as np, pandas as pd
from scipy import stats as sst
ALL=["Sahm","IUR","payrolls","housing","bill","claims","contclaims","IP"]
ZMAXg={n:float(np.nanmax(np.where(QC&G&CO,np.where(np.isfinite(Zz[n]),Zz[n],-99),-99))) for n in ALL}
ZMAXn=float(np.nanmax(np.where(QC&NG&CCO,np.where(np.isfinite(ZU["Sahm"]),ZU["Sahm"],-99),-99)))
Zarr={n:np.where(np.isfinite(Zz[n]),Zz[n],-99.0) for n in ALL}
def E_lines(lines):
    out=np.full(N,-99.0)
    for n,t in lines.items():
        out=np.maximum(out,(np.asarray(CH[n],float)-t)/SC[n][1])
    return np.where(np.isfinite(out),out,-99.0)
def pot(E, mask, q=0.90, decluster=45):
    s=pd.Series(E[mask],index=cal[mask]).replace(-99.0,np.nan).dropna()
    u=float(np.quantile(s.values,q))
    ex=s[s>u]
    keep=[]; last=None
    for d,v in ex.items():
        if last is None or (d-last).days>decluster: keep.append((d,v)); last=d
        elif v>keep[-1][1]: keep[-1]=(d,v); last=d
    y=np.array([v for d,v in keep])-u
    if len(y)<10: return None
    c,loc,sc=sst.genpareto.fit(y,floc=0.0)
    years=pd.Series(s.index).dt.year.nunique()
    rate=len(y)/years                       # independent exceedances per year
    p=float(sst.genpareto.sf(0.0-u,c,loc=0.0,scale=sc))
    return rate*p, u, c, sc, len(y), float(s.max())
RULES={
 "v11 (max-margin)":{"Sahm":0.36,"IUR":0.40,"payrolls":0.18,"housing":0.19,"bill":1.45},
 "v11-A (calm max x1.05)":{"Sahm":0.350,"IUR":0.236,"payrolls":0.086,"housing":0.128,"bill":1.407},
 "v13 (record + 0.25 sd)":{n:SC[n][0]+(ZMAXg[n]+0.25)*SC[n][1] for n in ["Sahm","payrolls","housing","contclaims"]},
 "v13 + production":{n:SC[n][0]+(ZMAXg[n]+0.25)*SC[n][1] for n in ["Sahm","payrolls","housing","contclaims","IP"]},
 "scale-free c=4.25":{n:SC[n][0]+4.25*SC[n][1] for n in ["Sahm","IUR","payrolls","housing","bill"]},
 "equal margin d=1.0":{n:SC[n][0]+(ZMAXg[n]+1.0)*SC[n][1] for n in ["Sahm","IUR","payrolls","housing","bill"]},
}
share=float((QC&G&CO).sum())/float(QC.sum())
print("gated lane, peaks over the 90th percentile of the quiet trigger statistic, declustered at 60 days")
print("%-26s %-8s %-8s %-7s %-6s %-11s %-8s %s"%("rule","quiet u","quiet max","GPD xi","n exc","hazard/yr","1 in","6.5-yr"))
for lab,lines in RULES.items():
    E=E_lines(lines); r=pot(E,QC&G&CO)
    if r is None: print("%-26s (too few exceedances)"%lab); continue
    p,u,c,sc,n_,mx=r; h=p*share
    print("%-26s %-8.2f %-8.2f %-7.2f %-6d %-11.5f %-8s %.1f%%"%(lab,u,mx,c,n_,h,("%.0f"%(1/h)) if h>0 else "inf",100*(1-(1-h)**6.5)))
print("\nsame, with the threshold at the 80th percentile (a check that the answer is not an artefact of u)")
for lab,lines in RULES.items():
    E=E_lines(lines); r=pot(E,QC&G&CO,q=0.80)
    if r is None: continue
    p,u,c,sc,n_,mx=r; h=p*share
    print("%-26s u %-7.2f xi %-6.2f n %-5d hazard %.5f/yr (one in %s)"%(lab,u,c,n_,h,("%.0f"%(1/h)) if h>0 else "inf"))
