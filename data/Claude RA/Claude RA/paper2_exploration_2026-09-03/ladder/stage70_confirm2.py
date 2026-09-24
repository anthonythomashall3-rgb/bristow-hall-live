"""Stage 70: confirmation with withdrawal, scored on the real state-machine episodes."""
exec(open("stage65_minimal.py").read().split('P0=dict(')[0])
import numpy as np, pandas as pd
P8=dict(sahm=0.36,iur=0.45,pay=0.003,hou=20,bill=1.45,sahmC=0.55,iurC=0.50,houC=25,
        claims=0.40,ip=0.02,vix=19,baa=1.50)
KEEP=["sahm","iur","pay","hou","bill","sahmC","vix"]
fast,clause,ung,lane=pieces(P8)
SER={"sahm":fresh(fast["sahm"],120)&G,"iur":fresh(fast["iur"],120)&G,
     "pay":fresh(fast["pay"],120)&G,"hou":fresh(fast["hou"],120)&G,
     "bill":fresh(fast["bill"],120)&G,"sahmX":fresh(clause["sahmC"]&NG,120),
     "vix":fresh(lane["vix"],120)}
GRP={"sahm":"unemployment","sahmX":"unemployment","iur":"insured unemp",
     "pay":"payrolls","hou":"housing","bill":"bill rate","vix":"VIX"}
o,l,f,n,lv=run(P8,KEEP); print("v8 base ok=%s lags=%s false=%s no-inv=%d/9 lane-void=%s"%(o,l,f,n,lv))
frozen=np.zeros(N,bool)
for k,c in fast.items():
    if k in KEEP: frozen|=fresh(c,120)&G
frozen|=fresh(clause["sahmC"]&NG,120)
la=fresh(lane["vix"],120); valid=la.copy()
for i in np.flatnonzero(np.diff(la.astype(np.int8))==1)+1:
    if not frozen[i:i+121].any():
        j=i
        while j<N and la[j]: valid[j]=False; j+=1
eps=replay(frozen|valid)
print("\n%-12s %-12s %-14s %-12s %-14s %s" % ("peak","onset call","opened by","confirmed","confirmed by","gap"))
rows=[]
for e,(pk,tr) in zip(eps,T_P1):
    i=int(np.where(cal==e["onset"])[0][0])
    op=[k for k,a in SER.items() if np.asarray(a,bool)[i]]
    g0={GRP[k] for k in op}
    j=i; conf=None
    while j<N and cal[j]<=pd.Timestamp(tr)+pd.DateOffset(months=6):
        hit=[k for k,a in SER.items() if np.asarray(a,bool)[j] and GRP[k] not in g0]
        if hit: conf=(j,hit[0]); break
        j+=1
    P=pd.Timestamp(pk)
    lag0=(e["onset"].year-P.year)*12+(e["onset"].month-P.month)
    if conf:
        jj,c=conf
        lag1=(cal[jj].year-P.year)*12+(cal[jj].month-P.month)
        print("%-12s %-12s %-14s %-12s %-14s %d days  (lag %+d -> %+d)" %
              (str(P.date())[:7],str(e["onset"].date()),GRP[op[0]],str(cal[jj].date()),GRP[c],(cal[jj]-e["onset"]).days,lag0,lag1))
        rows.append(((cal[jj]-e["onset"]).days, lag0, lag1))
    else:
        print("%-12s %-12s %-14s %-12s %-14s %s (lag %+d -> WITHDRAWN)" %
              (str(P.date())[:7],str(e["onset"].date()),GRP[op[0]],"never","-","",lag0))
        rows.append((None,lag0,None))
print("\nwindow  confirmed  lags after confirmation                    outside +-1 month")
for X in [30,45,60,90,120,180]:
    lags=[(l1 if (g is not None and g<=X) else None) for g,l0,l1 in rows]
    okn=sum(1 for x in lags if x is not None)
    bad=sum(1 for x in lags if x is None or abs(x)>1)
    print(" %4dd   %d/9        %-44s %d" % (X,okn,str(lags),bad))
