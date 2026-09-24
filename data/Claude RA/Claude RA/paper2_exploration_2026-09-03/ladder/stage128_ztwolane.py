"""Stage 128: the scale-free rule with the two lanes v11 already needs.  Channels are measured
in robust standard deviations of their own quiet distribution; the gated lane uses the gated
quiet scale, the no-inversion lane the ungated one.  Two numbers, both pure z, both portable."""
exec(open("stage127_zscale.py").read().split('def machine(')[0])
import numpy as np, pandas as pd
CORE=["Sahm","IUR","payrolls","housing","bill"]
QU=QC&CCO
SCU={}
for n in NAMES:
    x=np.asarray(CH[n],float)[QU]; x=x[np.isfinite(x)]
    med=float(np.median(x)); mad=float(np.median(np.abs(x-med)))*1.4826
    SCU[n]=(med,mad if mad>0 else np.nan)
ZU={n:(np.asarray(CH[n],float)-SCU[n][0])/SCU[n][1] for n in NAMES}
ZG=np.vstack([np.where(np.isfinite(Zz[n]),Zz[n],-99.0) for n in CORE]).max(axis=0)
ZN=np.vstack([np.where(np.isfinite(ZU[n]),ZU[n],-99.0) for n in CORE]).max(axis=0)
print("gated lane : quiet max %.2f"%float(np.nanmax(np.where(QC&G&CO,ZG,-99))))
print("open  lane : quiet max %.2f"%float(np.nanmax(np.where(QC&NG&CCO,ZN,-99))))
def machine(c,c2,lane=True):
    fr=fresh(np.asarray(ZG>=c,bool)&CO,120)&G
    fr=fr|fresh(np.asarray(ZN>=c2,bool)&CCO&NG,120)
    if lane:
        la=fresh(np.asarray(lane_arr(vix-vix.shift(20),1,22.0),bool),120); valid=la.copy()
        for i in np.flatnonzero(np.diff(la.astype(np.int8))==1)+1:
            if not fr[i:i+121].any():
                j=i
                while j<N and la[j]: valid[j]=False; j+=1
        fr=fr|valid
    eps=replay(fr); res,f=score_eps(eps,T_P1)
    det=sum(1 for x in res if x["lag"] is not None)
    armed=int((((np.asarray(ZG>=c,bool)&CO&G)|(np.asarray(ZN>=c2,bool)&CCO&NG))&QC).sum())
    return eps,res,f,det,armed
print("\n%-5s %-5s %-6s %-6s %-7s %-6s %s"%("c","c2","det","false","armedQ","inwk","days from the first day"))
best=[]
for c in [3.5,4,4.5,5,5.5,6,7,8,9,10,12]:
  for c2 in [3.5,4,4.5,5,5.5,6,7,8,9,10,12,15]:
    eps,res,f,det,armed=machine(c,c2,lane=False)
    dd=None
    if det==9:
        call={r["peak"]:r["onset"] for r in res}
        dd=[(pd.Timestamp(call[p])-FIRST[j]).days for j,(p,t) in enumerate(T_P1)]
    if det==9 and not f:
        best.append((c,c2,armed,sum(1 for x in dd if abs(x)<=7),float(np.mean([abs(x) for x in dd])),dd))
        print("%-5.1f %-5.1f %-6s %-6d %-7d %-6d %s"%(c,c2,"9/9",0,armed,sum(1 for x in dd if abs(x)<=7),dd))
if best:
    print("\nwidest scale-free window that keeps 9/9 with no false alarm: c in [%.1f,%.1f], c2 in [%.1f,%.1f]"%(
        min(b[0] for b in best),max(b[0] for b in best),min(b[1] for b in best),max(b[1] for b in best)))
    b=sorted(best,key=lambda t:t[4])[0]
    print("closest calls: c=%.1f c2=%.1f mean |days| %.1f  %s"%(b[0],b[1],b[4],b[5]))
else:
    print("\nno pair of scale-free thresholds gives 9/9 with zero false alarms")
