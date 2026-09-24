"""Stage 152: a line that no single quiet episode can set.  Stage 151 showed the weakness of a
record: the Sahm channel's quiet record is set by the post-pandemic normalisation of 2021, so
calibrating on a sample without it gives a different rule.  A high quantile of the quiet
distribution is the natural repair, and this stage asks which quantile is both high enough to
detect everything and stable across halves of the sample."""
exec(open("stage128_ztwolane.py").read().split("def machine(c,c2")[0])
import numpy as np, pandas as pd
CH4=["Sahm","payrolls","housing","bill"]
def lines_from(mask,q,delta,delta2):
    L={}
    for n in CH4:
        v=np.asarray(CH[n],float)[mask&QC&G&CO]; v=v[np.isfinite(v)]
        if len(v)<500: L[n]=np.inf; continue
        med=np.median(v); mad=np.median(np.abs(v-med))*1.4826
        L[n]=float(np.quantile(v,q)+delta*mad)
    v=np.asarray(CH["Sahm"],float)[mask&QC&NG&CCO]; v=v[np.isfinite(v)]
    med=np.median(v); mad=np.median(np.abs(v-med))*1.4826
    return L,float(np.quantile(v,q)+delta2*mad)
def run(L,LS):
    hits=np.zeros(N,bool)
    for n in CH4:
        x=np.asarray(CH[n],float); hits|=(np.where(np.isfinite(x),x,-9e9)>=L[n])
    hits|=np.asarray(gapch(iur4,0.40),bool)
    fr=fresh(hits&CO,120)&G
    xs=np.asarray(CH["Sahm"],float)
    fr=fr|fresh((np.where(np.isfinite(xs),xs,-9e9)>=LS)&CCO&NG,120)
    la=fresh(np.asarray(lane_arr(vix-vix.shift(20),1,22.0),bool),120); valid=la.copy()
    for i in np.flatnonzero(np.diff(la.astype(np.int8))==1)+1:
        if not fr[i:i+121].any():
            j=i
            while j<N and la[j]: valid[j]=False; j+=1
    eps=replay(fr|valid); res,f=score_eps(eps,T_P1)
    det=sum(1 for x in res if x["lag"] is not None)
    armed=int((hits&CO&G&QC).sum())
    dd=None
    if det==9:
        call={r["peak"]:r["onset"] for r in res}
        dd=[(pd.Timestamp(call[p])-FIRST[j]).days for j,(p,t) in enumerate(T_P1)]
    return det,f,armed,dd,[r["lag"] for r in res]
allm=np.ones(N,bool); CUT=pd.Timestamp("1990-01-01")
early=cal<CUT; late=cal>=CUT
T_EARLY=[t for t in T_P1 if pd.Timestamp(t[0]+"-01")<CUT]; T_LATE=[t for t in T_P1 if pd.Timestamp(t[0]+"-01")>=CUT]
print("%-7s %-7s %-9s %-7s %-8s %-30s %s"%("q","delta","full det","false","armedQ","lines","days"))
GOOD=[]
for q in [0.980,0.990,0.995,0.999,1.0]:
  for delta,delta2 in [(0.25,2.0),(0.5,2.0),(0.75,2.0),(1.0,2.0),(1.5,2.5),(2.0,3.0),(3.0,4.0)]:
    L,LS=lines_from(allm,q,delta,delta2)
    det,f,armed,dd,lags=run(L,LS)
    if det==9 and not f:
        GOOD.append((q,delta,delta2,L,LS,dd,armed))
        print("%-7.3f %-7.2f %-9s %-7d %-8d %-30s %s"%(q,delta,"9/9",0,armed,
              " ".join("%.3f"%L[n] for n in CH4),dd))
print("\nstability of the surviving settings across halves of the sample")
print("%-7s %-6s %-38s %-38s"%("q","delta","calibrated early, tested late","calibrated late, tested early"))
for q,delta,delta2,L,LS,dd,armed in GOOD:
    L1,LS1=lines_from(early,q,delta,delta2); L2,LS2=lines_from(late,q,delta,delta2)
    d1,f1,_,_,lg1=run(L1,LS1); d2,f2,_,_,lg2=run(L2,LS2)
    def part(f,mask,TT):
        eps=[x for x in f]
        return eps
    e1=[x for x in (f1 or []) if pd.Timestamp(x)>=CUT]; e2=[x for x in (f2 or []) if pd.Timestamp(x)<CUT]
    L1res=run(L1,LS1); L2res=run(L2,LS2)
    ndl=sum(1 for j,(p,t) in enumerate(T_P1) if pd.Timestamp(p+"-01")>=CUT and L1res[4][j] is not None)
    nde=sum(1 for j,(p,t) in enumerate(T_P1) if pd.Timestamp(p+"-01")<CUT and L2res[4][j] is not None)
    print("%-7.3f %-6.2f %-38s %-38s"%(q,delta,"%d of %d detected, %d false"%(ndl,len(T_LATE),len(e1)),
                                       "%d of %d detected, %d false"%(nde,len(T_EARLY),len(e2))))
