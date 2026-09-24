"""Stage 139: which channels, and how much margin?  Every subset of the eight candidate
channels is given the same margin -- delta robust standard deviations above each channel's own
quiet record -- and the largest delta that still detects nine of nine with no false alarm is
found for each.  The subset that tolerates the widest margin is the one with the lowest hazard."""
exec(open("stage128_ztwolane.py").read().split("def machine(c,c2")[0])
import numpy as np, pandas as pd, itertools
from scipy import stats as sst
ALL=["Sahm","IUR","payrolls","housing","bill","claims","contclaims","IP"]
ZMAXg={n:float(np.nanmax(np.where(QC&G&CO,np.where(np.isfinite(Zz[n]),Zz[n],-99),-99))) for n in ALL}
ZMAXn=float(np.nanmax(np.where(QC&NG&CCO,np.where(np.isfinite(ZU["Sahm"]),ZU["Sahm"],-99),-99)))
Zarr={n:np.where(np.isfinite(Zz[n]),Zz[n],-99.0) for n in ALL}
Zc=np.where(np.isfinite(ZU["Sahm"]),ZU["Sahm"],-99.0)
def run(names,d,d2=2.0):
    hits=np.zeros(N,bool)
    for n in names: hits|=(Zarr[n]>=ZMAXg[n]+d)
    fr=fresh(hits&CO,120)&G
    fr=fr|fresh((Zc>=ZMAXn+d2)&CCO&NG,120)
    eps=replay(fr); res,f=score_eps(eps,T_P1)
    det=sum(1 for x in res if x["lag"] is not None)
    return eps,res,f,det
def E_of(names,d):
    out=np.full(N,-99.0)
    for n in names: out=np.maximum(out,Zarr[n]-(ZMAXg[n]+d))
    return out
def gev(E,mask):
    s=pd.Series(E[mask],index=cal[mask]).replace(-99.0,np.nan).dropna()
    am=s.groupby(s.index.year).max(); am=am[s.groupby(s.index.year).size()>=30]
    if len(am)<8: return None
    c,loc,sc=sst.genextreme.fit(am.values)
    return float(sst.genextreme.sf(0.0,c,loc,sc))
rows=[]
DS=[0.0,0.25,0.5,0.75,1.0,1.25,1.5,1.75,2.0,2.5,3.0]
share=float((QC&G&CO).sum())/float(QC.sum())
for r in range(2,9):
  for names in itertools.combinations(ALL,r):
    for d in DS:
        eps,res,f,det=run(names,d)
        if det!=9 or f: continue
        call={x["peak"]:x["onset"] for x in res}
        dd=[(pd.Timestamp(call[p])-FIRST[j]).days for j,(pp,t) in enumerate(T_P1) for p in [pp]]
        g=gev(E_of(names,d),QC&G&CO)
        if g is None: continue
        rows.append(dict(k=len(names),delta=d,haz=g*share,names=" + ".join(names),
                         mad=round(float(np.mean(np.abs(dd))),1),inwk=sum(1 for x in dd if abs(x)<=7),
                         mx=max(dd),dd=str(dd)))
df=pd.DataFrame(rows)
df.to_csv("/root/out/stage139_subsets.csv",index=False)
print("SPEED-HAZARD FRONTIER: for each hazard band, the fastest channel set that keeps 9/9 and no false alarm")
print("%-14s %-9s %-7s %-6s %-7s %-6s %-46s %s"%("hazard band","hazard","1 in","delta","mean|d|","in wk","channels","days from the first day"))
bands=[(0.0,0.001),(0.001,0.002),(0.002,0.004),(0.004,0.006),(0.006,0.010),(0.010,0.020),(0.020,1.0)]
for lo,hi in bands:
    d=df[(df.haz>=lo)&(df.haz<hi)]
    if not len(d): continue
    b=d.sort_values("mad").iloc[0]
    print("%-14s %-9.5f %-7s %-6.2f %-7.1f %-6d %-46s %s"%("%.3f-%.3f"%(lo,hi),b.haz,
          ("%.0f"%(1/b.haz)) if b.haz>0 else "inf",b.delta,b.mad,b.inwk,b.names,b.dd))
print()
print("the ten fastest settings overall, whatever the hazard:")
for _,b in df.sort_values("mad").head(10).iterrows():
    print("  hazard %-9.5f 1 in %-7s delta %-5.2f mean|d| %-6.1f %-44s %s"%(b.haz,("%.0f"%(1/b.haz)) if b.haz>0 else "inf",b.delta,b.mad,b.names,b.dd))
