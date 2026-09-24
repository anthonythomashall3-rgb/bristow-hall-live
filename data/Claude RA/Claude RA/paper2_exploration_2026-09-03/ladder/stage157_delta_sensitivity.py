"""Stage 157: how much does the answer depend on the one number?  v14 has a single dial -- the
margin, a quarter of a robust standard deviation above each channel's own quiet record.  This
stage moves it and reports what breaks, and also what the machine does with the volatility lane
switched off."""
exec(open("stage128_ztwolane.py").read().split("def machine(c,c2")[0])
import numpy as np, pandas as pd
ZM={n:float(np.nanmax(np.where(QC&G&CO,np.where(np.isfinite(Zz[n]),Zz[n],-99),-99))) for n in NAMES}
ZNn=float(np.nanmax(np.where(QC&NG&CCO,np.where(np.isfinite(ZU["Sahm"]),ZU["Sahm"],-99),-99)))
Zc=np.where(np.isfinite(ZU["Sahm"]),ZU["Sahm"],-99.0)
def build(d,d2=2.0,lane=True):
    hits=np.zeros(N,bool)
    for n in ["Sahm","payrolls","housing","bill"]:
        z=np.where(np.isfinite(Zz[n]),Zz[n],-99.0); hits|=(z>=ZM[n]+d)
    hits|=np.asarray(gapch(iur4,0.40),bool)
    fr=fresh(hits&CO,120)&G
    fr=fr|fresh((Zc>=ZNn+d2)&CCO&NG,120)
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
    dd=None
    if det==9 and len(eps)==9: dd=[(e["onset"]-FIRST[i]).days for i,e in enumerate(eps)]
    return det,f,armed,dd,[r["lag"] for r in res]
print("moving the one dial (the open-lane margin held at 2.0)")
print("%-8s %-7s %-7s %-8s %-30s %s"%("margin","det","false","armedQ","lags","days from the first day"))
for d in [-0.50,-0.25,-0.10,0.00,0.10,0.25,0.50,0.75,1.00,1.50,2.00,3.00]:
    det,f,armed,dd,lags=build(d)
    print("%-8.2f %-7s %-7d %-8d %-30s %s"%(d,"%d/9"%det,len(f) if f else 0,armed,str(lags),dd if dd else ""))
print("\nmoving the open-lane margin (the gated margin held at 0.25)")
print("%-8s %-7s %-7s %s"%("margin","det","false","lags"))
for d2 in [0.0,0.5,1.0,1.5,2.0,3.0,4.0]:
    det,f,armed,dd,lags=build(0.25,d2)
    print("%-8.2f %-7s %-7d %s"%(d2,"%d/9"%det,len(f) if f else 0,lags))
print("\nwith and without the volatility lane, at the frozen margins")
for lane in (True,False):
    det,f,armed,dd,lags=build(0.25,2.0,lane)
    print("  lane %-5s %d/9, %d false, days %s"%(str(lane),det,len(f) if f else 0,dd))
