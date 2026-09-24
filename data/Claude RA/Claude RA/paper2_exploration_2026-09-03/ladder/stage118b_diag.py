"""Stage 118b: why does agreement (k>=2) fail?  For each recession, and for each channel,
report the largest normalised reading (own calm maximum = 1.00) inside the detection window,
so the k-th largest per episode can be compared with the k-th largest on the quiet set."""
exec(open("stage118_agree.py").read().split("FIRST=[pd.Timestamp")[0])
CORE=["Sahm","IUR","payrolls","housing","bill"]
import numpy as np, pandas as pd
PK=[p for p,t in T_P1]
WIN=[( (pd.Period(p,"M")-2).to_timestamp(), (pd.Period(p,"M")+4).to_timestamp(how="end")) for p,t in T_P1]
print("largest normalised reading per channel inside [peak-2, peak+4]  (1.00 = that channel's own calm record)")
print("%-9s %s"%("peak"," ".join("%-11s"%n for n in NAMES)))
EPmax={}
for (p,t),(a,b) in zip(T_P1,WIN):
    row=[]
    sel=(cal>=a)&(cal<=b)
    for n in NAMES:
        z=Z[n][sel]; z=z[np.isfinite(z)]
        row.append(float(np.max(z)) if len(z) else float("nan"))
    EPmax[p]=row
    print("%-9s %s"%(p," ".join("%-11.2f"%x for x in row)))
print()
for k in [1,2,3]:
    per=[]
    for p in PK:
        r=sorted([x for x in EPmax[p] if np.isfinite(x)],reverse=True)
        per.append(r[k-1] if len(r)>=k else float("nan"))
    print("k=%d  weakest recession reading %.3f at %s   (all: %s)"%(
        k,np.nanmin(per),PK[int(np.nanargmin(per))],["%.2f"%x for x in per]))
print()
for names,lab in [(CORE,"core5"),(NAMES,"all8")]:
    for W in [1,30,60,90]:
        for k in [1,2,3]:
            M=Mstat(names,W,k)
            qm=float(np.nanmax(np.where(QC&G&CO,M,-9)))
            ep=[]
            for (p,t),(a,b) in zip(T_P1,WIN):
                sel=(cal>=a)&(cal<=b); v=M[sel]; v=v[np.isfinite(v)]
                ep.append(float(np.max(v)) if len(v) else np.nan)
            print("%-6s W=%-4d k=%d | quiet max of M %6.3f | weakest recession %6.3f | margin %+6.3f | %s"%(
                lab,W,k,qm,np.nanmin(ep),np.nanmin(ep)-qm,PK[int(np.nanargmin(ep))]))
