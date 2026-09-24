"""Stage 118: a completely different shape of rule.  Instead of six independently
calibrated lines OR-ed together, normalise every channel by its OWN calm maximum, take a
running window maximum of each, and trigger on the k-th LARGEST normalised reading.  The
whole instrument then has three numbers -- a multiplier m, a window W and an agreement
count k -- instead of six fitted thresholds.  The agreement statistic M is a single
continuous object, so the hazard can be read straight off its quiet distribution."""
exec(open("stage106_v11.py").read().split('eps,l,e,t,f,n,arm,lv,co,cco=machine()')[0])
import numpy as np, pandas as pd
from scipy import stats as sst

m8=ic.rolling(8).mean(); rr8=(m8/m8.shift(1).rolling(52).min()-1)
CLx=np.nan_to_num(sd(rr8,5),nan=-9)
CO=pd.Series(CLx>=0.03).rolling(56,min_periods=1).max().fillna(0).astype(bool).values
CCO=pd.Series(CLx>=0.12).rolling(56,min_periods=1).max().fillna(0).astype(bool).values

cc=load(ODD+"01_labor_unemployment/weekly/CCSA.csv")
c8=cc.rolling(8).mean(); rc8=(c8/c8.shift(1).rolling(52).min()-1)

S   = Srel.reindex(cal).ffill().values.astype(float)
IURg= sd(iur4-iur4.rolling(52).min(),12)
PAY1= sd(pd.Series(pay.d1.astype(float).values,index=pd.to_datetime(pay.rel.values)),0)
H6  = np.minimum.reduce([sd(-h6.shift(j)) for j in range(3)])
BILL= sd(-(tb6-tb6.shift(60)),1)
CLA8= sd(rr8,5)
CC8 = sd(rc8,5)
IP3 = sd(-ip3,0)

CH={"Sahm":S,"IUR":IURg,"payrolls":-PAY1,"housing":H6,"bill":BILL,"claims":CLA8,"contclaims":CC8,"IP":IP3}
NAMES=list(CH)

def calmmax(v, mask):
    x=v[mask]; x=x[np.isfinite(x)]
    return float(np.max(x)) if len(x) else np.inf

QG=QC&G&CO                       # the quiet days a gated channel is actually exposed on
CMAX={k:calmmax(np.asarray(CH[k],float),QG) for k in NAMES}
print("channel calm maxima on the gated quiet set (%d days):"%QG.sum())
for k in NAMES: print("  %-11s %8.4f"%(k,CMAX[k]))

Z={k:np.asarray(CH[k],float)/CMAX[k] for k in NAMES}          # 1.0 = that channel's own calm record

def runmax(z, W):
    s=pd.Series(np.where(np.isfinite(z),z,-9.0),index=cal)
    return s.rolling(W,min_periods=1).max().values

def Mstat(names, W, k):
    Zs=np.vstack([runmax(Z[n],W) for n in names])
    Zs=np.sort(Zs,axis=0)[::-1]
    return Zs[k-1]                                            # k-th largest window-max

def run(names, W, k, m, clause_m=None, clause_k=1, lane=True):
    M=Mstat(names,W,k)
    fr=fresh(np.asarray(M>=m,bool)&CO,120)&G
    if clause_m is not None:
        MC=Mstat(names,W,clause_k)
        fr=fr|fresh(np.asarray(MC>=clause_m,bool)&CCO&NG,120)
    if lane:
        la=fresh(np.asarray(lane_arr(vix-vix.shift(20),1,22.0),bool),120); valid=la.copy()
        for i in np.flatnonzero(np.diff(la.astype(np.int8))==1)+1:
            if not fr[i:i+121].any():
                j=i
                while j<N and la[j]: valid[j]=False; j+=1
        fr=fr|valid
    eps=replay(fr)  if not lane else replay(fr)
    res,f=score_eps(eps,T_P1)
    det=sum(1 for x in res if x["lag"] is not None)
    return eps,res,f,det,M

def hazM(M, gated=True, mask=None):
    mm=QC&(G if gated else np.ones(N,bool))&(mask if mask is not None else np.ones(N,bool))
    s=pd.Series(M[mm],index=cal[mm]).replace(-9.0,np.nan).dropna()
    am=s.groupby(s.index.year).max(); am=am[s.groupby(s.index.year).size()>=30]
    if len(am)<8: return None
    c,loc,sc=sst.genextreme.fit(am.values)
    ya=pd.Series(cal[QC&(G if gated else np.ones(N,bool))]).dt.year.nunique()
    return (c,loc,sc,len(am),ya)

FIRST=[pd.Timestamp(x) for x in ["1970-01-01","1973-12-01","1980-02-01","1981-08-01","1990-08-01",
                                 "2001-04-01","2008-01-01","2020-03-01","2024-05-01"]]
print("\n%-34s %-6s %-6s %-9s %s"%("names/W/k/m","det","false","quietmax","days from the first day"))
rows=[]
CORE=["Sahm","IUR","payrolls","housing","bill"]
SETS={"core5":CORE,"core5+claims":CORE+["claims"],"core5+cc":CORE+["contclaims"],
      "all8":NAMES,"core5+claims+cc":CORE+["claims","contclaims"]}
for sname,names in SETS.items():
  for W in [30,60,90,120,180]:
    for k in [1,2,3]:
      if k>len(names): continue
      M=Mstat(names,W,k)
      qmax=float(np.nanmax(np.where(QC&G&CO,M,-9)))
      for m in [0.60,0.70,0.80,0.90,1.00,1.05,1.10,1.20,1.35,1.50]:
        eps,res,f,det,_=run(names,W,k,m,clause_m=None,lane=False)
        if det<9 or f: continue
        d=[e["onset"] for e in eps]; dd=[(d[i]-FIRST[i]).days for i in range(min(9,len(d)))]
        rows.append(dict(set=sname,W=W,k=k,m=m,qmax=round(qmax,3),det=det,nfalse=0,
                         inwk=sum(1 for x in dd if abs(x)<=7),mad=int(np.mean([abs(x) for x in dd])),
                         mx=int(max(dd)),dd=dd))
df=pd.DataFrame(rows)
if len(df):
    df=df.sort_values(["k","qmax","mad"],ascending=[False,True,True])
    print(df.head(40).to_string(index=False))
    df.to_csv("/root/out/stage118_agree.csv",index=False)
    print("\nrows with 9/9 and zero false: %d"%len(df))
    print("\nbest by margin (m - quiet max of M), k>=2 only:")
    d2=df[df.k>=2].copy(); d2["margin"]=d2.m-d2.qmax
    print(d2.sort_values("margin",ascending=False).head(15).to_string(index=False))
else:
    print("no configuration reached 9/9 with zero false alarms")
