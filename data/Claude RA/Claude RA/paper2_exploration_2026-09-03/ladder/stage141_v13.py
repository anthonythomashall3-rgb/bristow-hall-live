"""Stage 141: v13.  The channel set that survives leave-one-out selection, with every line a
quarter of a robust standard deviation above that channel's own quiet record.  Full
verification against v11: onsets, ends, troughs, false alarms, armed quiet days and hazard."""
exec(open("stage128_ztwolane.py").read().split("def machine(c,c2")[0])
import numpy as np, pandas as pd
from scipy import stats as sst
ALL=["Sahm","IUR","payrolls","housing","bill","claims","contclaims","IP"]
ZMAXg={n:float(np.nanmax(np.where(QC&G&CO,np.where(np.isfinite(Zz[n]),Zz[n],-99),-99))) for n in ALL}
ZMAXn=float(np.nanmax(np.where(QC&NG&CCO,np.where(np.isfinite(ZU["Sahm"]),ZU["Sahm"],-99),-99)))
Zarr={n:np.where(np.isfinite(Zz[n]),Zz[n],-99.0) for n in ALL}
Zc=np.where(np.isfinite(ZU["Sahm"]),ZU["Sahm"],-99.0)
V13=["Sahm","payrolls","housing","contclaims"]; DEL=0.25; D2=2.0
print("v13 lines, in the channels' own units")
for n in V13:
    raw=SC[n][0]+(ZMAXg[n]+DEL)*SC[n][1]
    print("  %-11s quiet record %7.4f  line %7.4f  (record + %.2f robust sd)"%(n,SC[n][0]+ZMAXg[n]*SC[n][1],raw,DEL))
print("  %-11s quiet record %7.4f  line %7.4f  (open lane, record + %.2f robust sd)"%(
    "Sahm clause",SCU["Sahm"][0]+ZMAXn*SCU["Sahm"][1],SCU["Sahm"][0]+(ZMAXn+D2)*SCU["Sahm"][1],D2))
def machine(names,d,d2,lane=True):
    hits=np.zeros(N,bool)
    for n in names: hits|=(Zarr[n]>=ZMAXg[n]+d)
    fr=fresh(hits&CO,120)&G
    CLA=(Zc>=ZMAXn+d2)&CCO&NG
    fr=fr|fresh(CLA,120)
    lv=[]
    if lane:
        la=fresh(np.asarray(lane_arr(vix-vix.shift(20),1,22.0),bool),120); valid=la.copy()
        for i in np.flatnonzero(np.diff(la.astype(np.int8))==1)+1:
            if not fr[i:i+121].any():
                j=i
                while j<N and la[j]: valid[j]=False; j+=1
                if cal[i]>=pd.Timestamp("1968-06-01"): lv.append(str(cal[i].date()))
        fr=fr|valid
    eps=replay(fr); res,f=score_eps(eps,T_P1)
    armed=int(((hits&CO&G)|CLA)[QC].sum())
    rN,_=score_eps(replay(fresh((Zc>=ZMAXn+d2)&CCO,120)),T_P1)
    return eps,res,f,armed,lv,sum(1 for x in rN if x["lag"] is not None)
eps,res,f,armed,lv,nclause=machine(V13,DEL,D2)
print("\nv13 record")
print("  onsets      %s"%[str(e["onset"].date()) for e in eps])
print("  lags        %s"%[r["lag"] for r in res])
print("  end calls   %s"%[r["end_lag"] for r in res])
print("  troughs     %s"%[r["tr_err"] for r in res])
print("  false       %s | armed quiet days %d of %d | lane voided %s | no-inversion clause %d/9"%(f if f else 0,armed,int(QC.sum()),lv,nclause))
print("  days from the recession's first day %s"%[(e["onset"]-FIRST[i]).days for i,e in enumerate(eps)][:9])
def E_of(names,d):
    out=np.full(N,-99.0)
    for n in names: out=np.maximum(out,Zarr[n]-(ZMAXg[n]+d))
    return out
def gevp(E,mask):
    s=pd.Series(E[mask],index=cal[mask]).replace(-99.0,np.nan).dropna()
    am=s.groupby(s.index.year).max(); am=am[s.groupby(s.index.year).size()>=30]
    c,loc,sc=sst.genextreme.fit(am.values)
    return float(sst.genextreme.sf(0.0,c,loc,sc)),float(am.max()),c,len(am)
share=float((QC&G&CO).sum())/float(QC.sum())
for lab,names,dd_ in [("v13",V13,DEL),("v13 + industrial production",V13+["IP"],DEL),("v11 five channels",["Sahm","IUR","payrolls","housing","bill"],DEL)]:
    p,mx,shape,ny=gevp(E_of(names,dd_),QC&G&CO)
    print("  %-28s trigger statistic: quiet record %+.2f (fires at 0), GEV shape %+.2f on %d years -> hazard %.5f/yr"%(lab,mx,shape,ny,p*share))
print("\nv11 for comparison")
print("  lags [-2,-1,0,1,1,-1,1,0,1] | ends [1,2,0,0,2,1,-1,1,1] | troughs [0,0,0,-1,1,0,-2,1,0]")
print("  days from the first day [-87,-37,-29,17,2,-58,3,-2,2] | hazard 0.0063/yr by the same estimator")
