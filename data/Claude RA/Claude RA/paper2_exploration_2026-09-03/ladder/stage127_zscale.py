"""Stage 127: normalise by SPREAD rather than by the record.  A calm maximum is the harshest
possible yardstick and it travels badly: a country whose expansions are noisy sets a bar no
mild recession can clear.  A robust scale -- the median and the median absolute deviation of
the channel's own quiet distribution -- is scale-free, so one number can be carried abroad."""
exec(open("stage118_agree.py").read().split('FIRST=[pd.Timestamp')[0])
import numpy as np, pandas as pd
from scipy import stats as sst
CORE=["Sahm","IUR","payrolls","housing","bill"]
FIRST=[pd.Timestamp(x) for x in ["1970-01-01","1973-12-01","1980-02-01","1981-08-01","1990-08-01",
                                 "2001-04-01","2008-01-01","2020-03-01","2024-05-01"]]
QG=QC&G&CO
SC={}
for n in NAMES:
    x=np.asarray(CH[n],float)[QG]; x=x[np.isfinite(x)]
    med=float(np.median(x)); mad=float(np.median(np.abs(x-med)))*1.4826
    SC[n]=(med,mad if mad>0 else np.nan)
print("%-11s %-9s %-9s %-9s %-9s"%("channel","quiet med","quiet MAD","calm max","calm max in z"))
for n in NAMES:
    med,mad=SC[n]; x=np.asarray(CH[n],float)[QG]; x=x[np.isfinite(x)]
    print("%-11s %-9.4f %-9.4f %-9.4f %-9.2f"%(n,med,mad,np.max(x),(np.max(x)-med)/mad))
Zz={n:(np.asarray(CH[n],float)-SC[n][0])/SC[n][1] for n in NAMES}
def machine(names,c,lane=True,clause=None):
    Zs=np.vstack([np.where(np.isfinite(Zz[n]),Zz[n],-99.0) for n in names]); Mx=Zs.max(axis=0)
    fr=fresh(np.asarray(Mx>=c,bool)&CO,120)&G
    if clause is not None: fr=fr|fresh(np.asarray(Zz["Sahm"]>=clause,bool)&CCO&NG,120)
    if lane:
        la=fresh(np.asarray(lane_arr(vix-vix.shift(20),1,22.0),bool),120); valid=la.copy()
        for i in np.flatnonzero(np.diff(la.astype(np.int8))==1)+1:
            if not fr[i:i+121].any():
                j=i
                while j<N and la[j]: valid[j]=False; j+=1
        fr=fr|valid
    eps=replay(fr); res,f=score_eps(eps,T_P1)
    det=sum(1 for x in res if x["lag"] is not None)
    return eps,res,f,det,Mx
Zs=np.vstack([np.where(np.isfinite(Zz[n]),Zz[n],-99.0) for n in CORE]); MX=Zs.max(axis=0)
qmax=float(np.nanmax(np.where(QG,MX,-99)))
epmin=[]
for (p,t) in T_P1:
    a=(pd.Period(p,"M")-2).to_timestamp(); b=(pd.Period(p,"M")+4).to_timestamp(how="end")
    sel=(cal>=a)&(cal<=b); epmin.append(float(np.max(MX[sel])))
print("\nquiet maximum of the largest z across the five channels: %.2f"%qmax)
print("weakest recession peak of the same object: %.2f (%s)"%(min(epmin),[p for p,t in T_P1][int(np.argmin(epmin))]))
print("per-recession peaks: %s"%[round(x,1) for x in epmin])
print("\n%-6s %-6s %-6s %-6s %s"%("c","det","false","inwk","days from the first day"))
ok=[]
for c in [4,5,6,7,8,9,10,11,12,13,14,15,16,18,20]:
    eps,res,f,det,_=machine(CORE,c,lane=False)
    dd=None
    if det==9:
        call={r["peak"]:r["onset"] for r in res}
        dd=[(pd.Timestamp(call[p])-FIRST[j]).days for j,(p,t) in enumerate(T_P1)]
    print("%-6d %-6s %-6d %-6s %s"%(c,"%d/9"%det,len(f) if f else 0,(sum(1 for x in dd if abs(x)<=7) if dd else "-"),dd if dd else ""))
    if det==9 and not f: ok.append(c)
if ok: print("\nthe US admits a single scale-free threshold anywhere in z = %d .. %d"%(min(ok),max(ok)))
else:  print("\nno single scale-free threshold works on the US alone")
