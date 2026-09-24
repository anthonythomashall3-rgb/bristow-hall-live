"""Stage 82: v9 = v8 + a global claims floor (3%) + a stronger floor on the no-inversion
clause (10%).  Then the EVT hazard, the perturbation map, and the first-print check."""
exec(open("stage46_v7.py").read().split("t6,l6=build")[0])
import numpy as np, pandas as pd
from scipy import stats as sst
G=np.asarray(GATE[12],bool); NG=~G
WINS=[(pd.Timestamp(p),pd.Timestamp(t)) for p,t in T_P1]
QUIET=np.ones(N,bool)&(cal>=pd.Timestamp("1968-06-01"))
for p,t in WINS: QUIET &= ~((cal>=p-pd.DateOffset(months=6))&(cal<=t+pd.DateOffset(months=12)))
def sd(s,lag):
    x=s.copy(); x.index=x.index+pd.Timedelta(days=lag); return x.reindex(cal).ffill().values.astype(float)
CL=np.nan_to_num(sd(r8,5),nan=-9)
REF=['1969-10-06','1973-10-25','1980-01-03','1981-08-18','1990-08-03','2001-02-02','2008-01-04','2020-02-28','2024-05-03']
def mk(sahm=0.36,iur=0.40,payx=0.18,hou=20,bill=1.45,clause=0.55,vixx=22.0,gfloor=0.03,cfloor=0.10):
    co=CL>=gfloor; cco=CL>=cfloor
    F=[np.asarray(D(Srel>=sahm-1e-9),bool),np.asarray(gapch(iur4,iur),bool),
       np.asarray(D(pd.Series((pay.d1.astype(float)<=-payx).values,index=pd.to_datetime(pay.rel.values))),bool),
       np.asarray(persist2(h3,hou),bool),np.asarray(fall(tb6,60,bill),bool)]
    fr=np.zeros(N,bool)
    for c in F: fr|=fresh(c&co,120)&G
    CLA=np.asarray(D(Srel>=clause-1e-9),bool)&cco
    fr|=fresh(CLA&NG,120)
    la=fresh(np.asarray(lane_arr(vix-vix.shift(20),1,vixx),bool),120); valid=la.copy(); lv=[]
    for i in np.flatnonzero(np.diff(la.astype(np.int8))==1)+1:
        if not fr[i:i+121].any():
            j=i
            while j<N and la[j]: valid[j]=False; j+=1
            if cal[i]>=pd.Timestamp("1968-06-01"): lv.append(str(cal[i].date()))
    eps=replay(fr|valid); r,f=score_eps(eps,T_P1)
    fz=fresh(CLA,120); rN,_=score_eps(replay(fz),T_P1)
    armed=np.zeros(N,bool)
    for c in F: armed|=(c&co&G)
    armed|=(CLA&NG)
    return dict(dates=[str(e["onset"].date()) for e in eps],ends=[str(e["end_call"].date()) for e in eps],
                lags=[x["lag"] for x in r],endlags=[x["end_lag"] for x in r],tr=[x["tr_err"] for x in r],
                false=f,noinv=sum(1 for x in rN if x["lag"] is not None),lane=lv,
                exp=100*(armed&QUIET).sum()/QUIET.sum())
v8=mk(gfloor=-9,cfloor=-9); v9=mk()
for nm,z in [("v8",v8),("v9",v9)]:
    print("%s dates %s | lags %s | ends %s | trough %s | false %s | no-inv %d/9 | lane %s | quiet exposure %.3f%%" %
          (nm, "identical" if z["dates"]==REF else z["dates"], z["lags"], z["endlags"], z["tr"],
           z["false"] if z["false"] else 0, z["noinv"], z["lane"], z["exp"]))
print("\nends identical:", v9["ends"]==v8["ends"])
print("\n=== EVT hazard, joint conditions ===")
S=Srel.reindex(cal).ffill().values.astype(float)
def evt_joint(stat, thr, co, gated):
    m=QUIET & co & (GATE[12] if gated else np.ones(N,bool))
    v=pd.Series(stat[m],index=cal[m]).dropna()
    if len(v)<300: return 0.0,len(v)
    am=v.groupby(v.index.year).max(); am=am[v.groupby(v.index.year).size()>=30]
    if len(am)<12: return 0.0,len(v)
    c,loc,sc=sst.genextreme.fit(am.values)
    return float(sst.genextreme.sf(thr,c,loc,sc)),len(v)
IURg=sd(iur4-iur4.rolling(52).min(),12)
PAY1=sd(pd.Series(pay.d1.astype(float).values,index=pd.to_datetime(pay.rel.values)),0)
H3=sd(-h3,0); BILL=sd(-(tb6-tb6.shift(60)),1)
share=0.40
rows=[("Sahm fast",S,0.36,CL>=0.03,True),("IUR fast",IURg,0.40,CL>=0.03,True),
      ("payrolls fast",-PAY1,0.18,CL>=0.03,True),("housing fast",H3,0.20,CL>=0.03,True),
      ("bill fast",BILL,1.45,CL>=0.03,True),("Sahm clause",S,0.55,CL>=0.10,False)]
tot={}
for nm,st,thr,co,gated in rows:
    p,nq=evt_joint(st,thr,co,gated)
    if gated: p*=share
    else: p*=(1-share)
    tot[nm]=p
    print("  %-14s quiet days meeting the floor %6d   hazard %.5f/yr %s" % (nm,nq,p,("1 in %.0f"%(1/p)) if p>0 else "(no quiet year reaches it)"))
u=1-np.prod([1-p for p in tot.values()])
print("\n  v9 union %.4f/yr -> 1 in %.0f years | 6.5-yr risk %.0f%% | 10-yr %.0f%%" % (u,1/u,100*(1-(1-u)**6.5),100*(1-(1-u)**10)))
for det in (0.867,0.955): print("  detection %.3f x no false alarm over 6.5 yr = %.0f%%" % (det,100*det*(1-u)**6.5))
