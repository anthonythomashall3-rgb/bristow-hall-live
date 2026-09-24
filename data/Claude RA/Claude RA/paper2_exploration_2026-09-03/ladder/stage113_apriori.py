"""Stage 113: how fitted is the rule?  Every threshold is currently a max-margin midpoint
between the quiet maximum and the smallest recession reading -- which uses the recessions.
Replace all of them at once with an A-PRIORI rule that never looks at a recession: set each
line at a fixed quantile of that channel's own QUIET distribution.  Then see what is lost."""
exec(open("stage112_cusum.py").read().split('d0,l0,e0,f0,n0,a0=machine_with()')[0])
import numpy as np, pandas as pd
REFd=[pd.Timestamp(x) for x in REF]
S=Srel.reindex(cal).ffill().values.astype(float)
IURg=sd(iur4-iur4.rolling(52).min(),12)
PAY1=sd(pd.Series(pay.d1.astype(float).values,index=pd.to_datetime(pay.rel.values)),0)
H6=np.minimum.reduce([sd(-h6.shift(j)) for j in range(3)])
BILL=sd(-(tb6-tb6.shift(60)),1)
V11={"Sahm":0.36,"IUR":0.40,"payrolls":0.18,"housing":0.19,"bill":1.45,"clause":0.55}
STAT={"Sahm":(S,True),"IUR":(IURg,True),"payrolls":(-PAY1,True),"housing":(H6,True),"bill":(BILL,True),"clause":(S,False)}
def qline(v,gated,Q,mult=1.0):
    m=QC&(G if gated else np.ones(N,bool))&(CO if gated else CCO)
    x=v[m]; x=x[np.isfinite(x)]
    return float(np.quantile(x,Q))*mult
def build(th):
    F=[np.asarray(D(Srel>=th["Sahm"]-1e-9),bool), np.asarray(gapch(iur4,th["IUR"]),bool),
       np.asarray(D(pd.Series((pay.d1.astype(float)<=-th["payrolls"]).values,index=pd.to_datetime(pay.rel.values))),bool),
       persist_k(h6,th["housing"],3), np.asarray(fall(tb6,60,th["bill"]),bool)]
    fr=np.zeros(N,bool)
    for c in F: fr|=fresh(c&CO,120)&G
    CLA=np.asarray(D(Srel>=th["clause"]-1e-9),bool)&CCO
    fr|=fresh(CLA&NG,120)
    la=fresh(np.asarray(lane_arr(vix-vix.shift(20),1,22.0),bool),120); valid=la.copy()
    for i in np.flatnonzero(np.diff(la.astype(np.int8))==1)+1:
        if not fr[i:i+121].any():
            j=i
            while j<N and la[j]: valid[j]=False; j+=1
    eps=replay(fr|valid); res,f=score_eps(eps,T_P1)
    fz=fresh(CLA,120); rN,_=score_eps(replay(fz),T_P1)
    armed=np.zeros(N,bool)
    for c in F: armed|=(c&CO&G)
    armed|=(CLA&NG)
    return ([e["onset"] for e in eps],[x["lag"] for x in res],f,sum(1 for x in rN if x["lag"] is not None),int((armed&QC).sum()))
d,l,f,n,a=build(V11)
print("v11 (max-margin, fitted): lags %s | false %s | no-inv %d/9 | armed %d" % (l,f if f else 0,n,a))
print("\n%-30s %-38s %-9s %-8s %s" % ("a-priori rule","thresholds","detected","false","lags"))
for Q,mult,lab in [(1.00,1.00,"quiet maximum"),(1.00,1.02,"quiet maximum x1.02"),(1.00,1.05,"quiet maximum x1.05"),
                   (1.00,1.10,"quiet maximum x1.10"),(0.9995,1.00,"99.95th percentile"),(0.999,1.00,"99.9th percentile"),
                   (0.995,1.00,"99.5th percentile")]:
    th={k:round(qline(STAT[k][0],STAT[k][1],Q,mult),3) for k in V11}
    d2,l2,f2,n2,a2=build(th)
    det=sum(1 for x in l2 if x is not None)
    print("%-30s %-38s %-9s %-8s %s" % (lab, str(th), "%d/9"%det, len(f2) if f2 else 0, l2))
print("\nv11's own thresholds for comparison:", V11)
