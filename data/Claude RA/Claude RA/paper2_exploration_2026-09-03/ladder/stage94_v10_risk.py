"""Stage 94: v10 risk and robustness."""
exec(open("stage93_v10.py").read().split('run(np.asarray(persist2(h3,20),bool)')[0])
import numpy as np, pandas as pd
from scipy import stats as sst
share=0.40
def haz(stat, thr, gated=True, floor=0.03, k=1):
    v=stat if k==1 else np.minimum.reduce([stat]*1)
    m=QC&(G if gated else np.ones(N,bool))&(CL>=floor)
    s=pd.Series(v[m],index=cal[m]).dropna()
    am=s.groupby(s.index.year).max(); am=am[s.groupby(s.index.year).size()>=30]
    if len(am)<8: return 0.0
    c,loc,sc=sst.genextreme.fit(am.values)
    p=float(sst.genextreme.sf(thr,c,loc,sc))
    yrs_all=pd.Series(cal[QC&(G if gated else np.ones(N,bool))]).dt.year.nunique()
    return p*(len(am)/max(yrs_all,1))*(share if gated else (1-share))
S=Srel.reindex(cal).ffill().values.astype(float)
IURg=sd(iur4-iur4.rolling(52).min(),12)
PAY1=sd(pd.Series(pay.d1.astype(float).values,index=pd.to_datetime(pay.rel.values)),0)
H6=np.minimum.reduce([sd(-h6.shift(j)) for j in range(3)])
BILL=sd(-(tb6-tb6.shift(60)),1)
v10={"Sahm fast":haz(S,0.36),"IUR fast":haz(IURg,0.40),"payrolls fast":haz(-PAY1,0.18),
     "housing fast (6m x3)":haz(H6,0.19),"bill fast":haz(BILL,1.45),
     "Sahm clause":haz(S,0.55,gated=False,floor=0.12)}
v9=dict(v10); v9["housing fast (6m x3)"]=0.01009   # the old 3m x2 channel's fitted value
u=lambda d: 1-np.prod([1-p for p in d.values()])
print("%-46s %-11s %-13s %-12s %s" % ("rule","union/yr","one every","6.5-yr","10-yr"))
for lab,val in [("v7 (round 18)",0.0664),("v7.2 (round 19)",0.0347),("v8 (round 20)",0.0282),
                ("v9 (round 21)",u(v9)),("v10 (round 22)",u(v10))]:
    print("%-46s %-11.4f 1 in %-9.0f %-12.0f%% %.0f%%" % (lab,val,1/max(val,1e-9),100*(1-(1-val)**6.5),100*(1-(1-val)**10)))
print("\nv10 hazard by channel:")
for k,vv in sorted(v10.items(), key=lambda kv:-kv[1]): print("   %-22s %.5f/yr%s" % (k,vv,("  1 in %.0f yr"%(1/vv)) if vv>0 else ""))
for det in (0.867,0.955): print("detection %.3f x no false alarm over 6.5 yr = %.0f%%" % (det,100*det*(1-u(v10))**6.5))
print("\n=== perturbation map, v10 ===")
def mk(sahm=0.36,iur=0.40,payx=0.18,hou=0.19,houk=3,bill=1.45,clause=0.55,vixx=22.0,gf=0.03,cf=0.12):
    co=CL>=gf; cco=CL>=cf
    F=[np.asarray(D(Srel>=sahm-1e-9),bool),np.asarray(gapch(iur4,iur),bool),
       np.asarray(D(pd.Series((pay.d1.astype(float)<=-payx).values,index=pd.to_datetime(pay.rel.values))),bool),
       persist_k(h6,hou,houk),np.asarray(fall(tb6,60,bill),bool)]
    fr=np.zeros(N,bool)
    for c in F: fr|=fresh(c&co,120)&G
    CLA=np.asarray(D(Srel>=clause-1e-9),bool)&cco
    fr|=fresh(CLA&NG,120)
    la=fresh(np.asarray(lane_arr(vix-vix.shift(20),1,vixx),bool),120); valid=la.copy()
    for i in np.flatnonzero(np.diff(la.astype(np.int8))==1)+1:
        if not fr[i:i+121].any():
            j=i
            while j<N and la[j]: valid[j]=False; j+=1
    eps=replay(fr|valid); res,f=score_eps(eps,T_P1)
    fz=fresh(CLA,120); rN,_=score_eps(replay(fz),T_P1)
    return [str(e["onset"].date()) for e in eps],[x["lag"] for x in res],f,sum(1 for x in rN if x["lag"] is not None)
nfa=0; tot=0
for lab,kw in [("Sahm 0.36 -> 0.34",dict(sahm=0.34)),("Sahm 0.36 -> 0.38",dict(sahm=0.38)),
 ("IUR 0.40 -> 0.35",dict(iur=0.35)),("IUR 0.40 -> 0.45",dict(iur=0.45)),
 ("payrolls 0.18 -> 0.13",dict(payx=0.13)),("payrolls 0.18 -> 0.23",dict(payx=0.23)),
 ("housing 19% -> 17%",dict(hou=0.17)),("housing 19% -> 21%",dict(hou=0.21)),
 ("housing x3 -> x2",dict(houk=2)),("housing x3 -> x4",dict(houk=4)),
 ("bill 1.45 -> 1.40",dict(bill=1.40)),("bill 1.45 -> 1.50",dict(bill=1.50)),
 ("clause 0.55 -> 0.50",dict(clause=0.50)),("clause 0.55 -> 0.60",dict(clause=0.60)),
 ("VIX 22 -> 20",dict(vixx=20)),("VIX 22 -> 24",dict(vixx=24)),
 ("global floor 3% -> 2%",dict(gf=0.02)),("global floor 3% -> 4%",dict(gf=0.04)),
 ("clause floor 12% -> 10%",dict(cf=0.10)),("clause floor 12% -> 14%",dict(cf=0.14))]:
    d,l,f,n=mk(**kw); tot+=1
    if f: nfa+=1
    print("  %-24s false %-3s miss %-2d outside-month %s%s" % (lab,len(f) if f else 0,sum(1 for x in l if x is None),
          [x for x in l if x is not None and abs(x)>1],"" if n==9 else "  [no-inv %d/9]"%n))
print("  %d of %d one-tick moves create a false alarm" % (nfa,tot))
