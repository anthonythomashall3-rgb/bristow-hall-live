"""Stage 138: one hazard estimator for every rule.  Summing each channel's own tail treats the
channels as independent, which stage 118 showed they are not; the union is therefore
overstated.  For any OR-rule the trigger is the single statistic E = max over channels of
(reading minus that channel's line) in robust standard deviations, and the rule fires exactly
when E >= 0.  Extreme value theory on the quiet annual maxima of E is a direct estimate."""
exec(open("stage128_ztwolane.py").read().split("def machine(c,c2")[0])
import numpy as np, pandas as pd
from scipy import stats as sst
CORE=["Sahm","IUR","payrolls","housing","bill"]
MADg={n:SC[n][1] for n in NAMES}; MADn={n:SCU[n][1] for n in NAMES}
ZMAXg={n:float(np.nanmax(np.where(QC&G&CO,np.where(np.isfinite(Zz[n]),Zz[n],-99),-99))) for n in NAMES}
ZMAXn={n:float(np.nanmax(np.where(QC&NG&CCO,np.where(np.isfinite(ZU[n]),ZU[n],-99),-99))) for n in NAMES}
def excess(thr_raw, gated=True):
    """thr_raw: dict channel -> threshold in the channel's own raw units"""
    out=np.full(N,-99.0)
    for n,t in thr_raw.items():
        z=(np.asarray(CH[n],float)-t)/(MADg[n] if gated else MADn[n])
        z=np.where(np.isfinite(z),z,-99.0)
        out=np.maximum(out,z)
    return out
def gev_haz(E, mask, at=0.0):
    s=pd.Series(E[mask],index=cal[mask]).replace(-99.0,np.nan).dropna()
    am=s.groupby(s.index.year).max(); am=am[s.groupby(s.index.year).size()>=30]
    if len(am)<8: return None
    c,loc,sc=sst.genextreme.fit(am.values)
    return float(sst.genextreme.sf(at,c,loc,sc)), float(am.max()), len(am), c
RULES={}
RULES["v11 (max-margin)"]=({"Sahm":0.36,"IUR":0.40,"payrolls":0.18,"housing":0.19,"bill":1.45},0.55)
RULES["v11-A (calm max x1.05)"]=({"Sahm":0.350,"IUR":0.236,"payrolls":0.086,"housing":0.128,"bill":1.407},0.525)
zc={n:SC[n][0]+4.25*SC[n][1] for n in CORE}
RULES["scale-free c=4.25"]=(zc,SCU["Sahm"][0]+8.0*SCU["Sahm"][1])
zc5={n:SC[n][0]+5.0*SC[n][1] for n in CORE}
RULES["scale-free c=5.00"]=(zc5,SCU["Sahm"][0]+10.0*SCU["Sahm"][1])
for d in [0.5,1.0]:
    RULES["equal margin delta=%.1f"%d]=({n:SC[n][0]+(ZMAXg[n]+d)*SC[n][1] for n in CORE},
                                        SCU["Sahm"][0]+(ZMAXn["Sahm"]+2.0)*SCU["Sahm"][1])
print("%-26s %-9s %-9s %-7s %-11s %-8s %s"%("rule","E quiet","E worst","GEV","hazard/yr","1 in","6.5-year risk"))
for lab,(thr,cl) in RULES.items():
    Eg=excess(thr,True); En=(np.asarray(CH["Sahm"],float)-cl)/MADn["Sahm"]
    En=np.where(np.isfinite(En),En,-99.0)
    rg=gev_haz(Eg,QC&G&CO); rn=gev_haz(En,QC&NG&CCO)
    pg=rg[0]*(float((QC&G&CO).sum())/float(QC.sum())) if rg else 0.0
    pn=rn[0]*(float((QC&NG&CCO).sum())/float(QC.sum())) if rn else 0.0
    u=1-(1-pg)*(1-pn)
    print("%-26s %-9.2f %-9s %-7.2f %-11.5f %-8.0f %.1f%%"%(lab,rg[1],"%.2f"%rn[1] if rn else "-",rg[3],u,1/u if u>0 else 9e9,100*(1-(1-u)**6.5)))
print("\n(E quiet = the highest the trigger statistic ever reached on a quiet gated day; the rule")
print(" fires at 0, so a more negative number is a wider margin.  GEV shape below zero means a")
print(" bounded tail, above zero a heavy one.)")
