"""Stage 119: the one-dial rule.  Every channel is expressed as a multiple of its OWN calm
maximum; the machine fires when any channel exceeds m times that maximum.  m is the only
number in the instrument.  This stage traces detection, false alarms, the hazard and the
timing of the calls as m moves, so the whole trade-off is visible in one table."""
exec(open("stage118_agree.py").read().split('FIRST=[pd.Timestamp')[0])
import numpy as np, pandas as pd
from scipy import stats as sst
CORE=["Sahm","IUR","payrolls","housing","bill"]
FIRST=[pd.Timestamp(x) for x in ["1970-01-01","1973-12-01","1980-02-01","1981-08-01","1990-08-01",
                                 "2001-04-01","2008-01-01","2020-03-01","2024-05-01"]]
def evt_haz(v, m, gated=True, mask=None):
    mm=QC&(G if gated else np.ones(N,bool))&(mask if mask is not None else np.ones(N,bool))
    s=pd.Series(np.where(np.isfinite(v[mm]),v[mm],np.nan),index=cal[mm]).dropna()
    if len(s)<200: return np.nan
    am=s.groupby(s.index.year).max(); am=am[s.groupby(s.index.year).size()>=30]
    if len(am)<8: return np.nan
    c,loc,sc=sst.genextreme.fit(am.values)
    ya=pd.Series(cal[QC&(G if gated else np.ones(N,bool))]).dt.year.nunique()
    return float(sst.genextreme.sf(m,c,loc,sc))*(len(am)/max(ya,1))
def machine(names, m, clause=None, lane=True):
    Zs=np.vstack([np.where(np.isfinite(Z[n]),Z[n],-9.0) for n in names])
    M=Zs.max(axis=0)
    fr=fresh(np.asarray(M>=m,bool)&CO,120)&G
    if clause is not None:
        fr=fr|fresh(np.asarray(Z["Sahm"]>=clause,bool)&CCO&NG,120)
    valid=np.zeros(N,bool)
    if lane:
        la=fresh(np.asarray(lane_arr(vix-vix.shift(20),1,22.0),bool),120); valid=la.copy()
        for i in np.flatnonzero(np.diff(la.astype(np.int8))==1)+1:
            if not fr[i:i+121].any():
                j=i
                while j<N and la[j]: valid[j]=False; j+=1
    eps=replay(fr|valid); res,f=score_eps(eps,T_P1)
    det=sum(1 for x in res if x["lag"] is not None)
    armed=int((np.asarray(M>=m,bool)&CO&G&QC).sum())
    return eps,res,f,det,armed,M
ZS=np.vstack([np.where(np.isfinite(Z[n]),Z[n],-9.0) for n in CORE]); MCORE=ZS.max(axis=0)
print("one dial, core five channels, ungated-clause Sahm at 1.65x its calm max")
print("%-6s %-5s %-6s %-7s %-9s %-6s %-5s %s"%("m","det","false","armed","hazard/yr","1-in","inwk","days from the first day"))
best=[]
for m in [1.00,1.05,1.10,1.15,1.20,1.25,1.30,1.35,1.40,1.45,1.50,1.55,1.60]:
    eps,res,f,det,armed,M=machine(CORE,m,clause=1.65)
    h=evt_haz(MCORE,m,True,CO)
    dd=None
    if det==9 and not f and len(eps)==9:
        d=[e["onset"] for e in eps]; dd=[(d[i]-FIRST[i]).days for i in range(9)]
    print("%-6.2f %-5d %-6d %-7d %-9.5f %-6s %-5s %s"%(m,det,len(f) if f else 0,armed,h,
          ("%.0f"%(1/h)) if h and h==h and h>0 else "inf",
          (sum(1 for x in dd if abs(x)<=7) if dd else "-"), dd))
    if dd is not None and not f and det==9: best.append((m,h,dd))
print("\nv11 for comparison: hazard 0.0105/yr (1 in 95), days [-87,-37,-29,17,2,-58,3,-2,2], 4 of 9 inside a week")
print("\nsame table with the ungated Sahm clause removed (gate must be armed for every call):")
print("%-6s %-5s %-6s %-9s %s"%("m","det","false","hazard/yr","days"))
for m in [1.00,1.10,1.20,1.30,1.40,1.50,1.60]:
    eps,res,f,det,armed,M=machine(CORE,m,clause=None)
    dd=None
    if det==9 and not f and len(eps)==9:
        d=[e["onset"] for e in eps]; dd=[(d[i]-FIRST[i]).days for i in range(9)]
    print("%-6.2f %-5d %-6d %-9.5f %s"%(m,det,len(f) if f else 0,evt_haz(MCORE,m,True,CO),dd))
