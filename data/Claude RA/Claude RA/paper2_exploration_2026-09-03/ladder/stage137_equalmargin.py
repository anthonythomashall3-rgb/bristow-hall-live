"""Stage 137: equal margins.  A multiple of the calm maximum gives each channel a different
amount of room; a common number of robust standard deviations ABOVE each channel's own quiet
record gives every line the same margin in the only currency that matters for the hazard.
One number, delta, then sets the whole instrument."""
exec(open("stage128_ztwolane.py").read().split("def machine(c,c2")[0])
import numpy as np, pandas as pd
from scipy import stats as sst
CORE=["Sahm","IUR","payrolls","housing","bill"]
ZMAXg={n:float(np.nanmax(np.where(QC&G&CO,np.where(np.isfinite(Zz[n]),Zz[n],-99),-99))) for n in NAMES}
ZMAXn={n:float(np.nanmax(np.where(QC&NG&CCO,np.where(np.isfinite(ZU[n]),ZU[n],-99),-99))) for n in NAMES}
print("each channel's quiet record, in robust standard deviations of its own quiet distribution")
print("%-11s %-10s %-10s"%("channel","gated","open"))
for n in NAMES: print("%-11s %-10.2f %-10.2f"%(n,ZMAXg[n],ZMAXn[n]))
def machine(delta,delta2,names=CORE,lane=False):
    hits=np.zeros(N,bool)
    for n in names:
        z=np.where(np.isfinite(Zz[n]),Zz[n],-99.0)
        hits|=(z>=ZMAXg[n]+delta)
    fr=fresh(hits&CO,120)&G
    zc=np.where(np.isfinite(ZU["Sahm"]),ZU["Sahm"],-99.0)
    fr=fr|fresh((zc>=ZMAXn["Sahm"]+delta2)&CCO&NG,120)
    if lane:
        la=fresh(np.asarray(lane_arr(vix-vix.shift(20),1,22.0),bool),120); valid=la.copy()
        for i in np.flatnonzero(np.diff(la.astype(np.int8))==1)+1:
            if not fr[i:i+121].any():
                j=i
                while j<N and la[j]: valid[j]=False; j+=1
        fr=fr|valid
    eps=replay(fr); res,f=score_eps(eps,T_P1)
    det=sum(1 for x in res if x["lag"] is not None)
    armed=int((hits&CO&G&QC).sum())
    return eps,res,f,det,armed
def chaz(n,thr,gated):
    m=QC&(G&CO if gated else NG&CCO)
    v=np.where(np.isfinite(Zz[n] if gated else ZU[n]),(Zz[n] if gated else ZU[n]),np.nan)
    s=pd.Series(v[m],index=cal[m]).dropna()
    am=s.groupby(s.index.year).max(); am=am[s.groupby(s.index.year).size()>=30]
    if len(am)<8: return 0.0
    c,loc,sc=sst.genextreme.fit(am.values)
    ya=pd.Series(cal[QC&(G if gated else NG)]).dt.year.nunique()
    return float(sst.genextreme.sf(thr,c,loc,sc))*(len(am)/max(ya,1))
print("\n%-7s %-7s %-6s %-6s %-7s %-11s %-7s %s"%("delta","delta2","det","false","armedQ","hazard/yr","1 in","days from the first day"))
for d in [0.0,0.25,0.50,0.75,1.00,1.25,1.50,2.00]:
  for d2 in [0.0,0.5,1.0,2.0]:
    eps,res,f,det,armed=machine(d,d2)
    dd=None
    if det==9:
        call={r["peak"]:r["onset"] for r in res}
        dd=[(pd.Timestamp(call[p])-FIRST[j]).days for j,(p,t) in enumerate(T_P1)]
    if det<9 or f: continue
    H=[chaz(n,ZMAXg[n]+d,True) for n in CORE]+[chaz("Sahm",ZMAXn["Sahm"]+d2,False)]
    u=1-np.prod([1-x for x in H])
    print("%-7.2f %-7.2f %-6s %-6d %-7d %-11.5f %-7.0f %s"%(d,d2,"9/9",0,armed,u,1/u if u>0 else 9e9,dd))
