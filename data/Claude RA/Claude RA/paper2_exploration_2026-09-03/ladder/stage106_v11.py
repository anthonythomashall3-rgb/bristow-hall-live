"""Stage 106: v11 = v10 with the claims floor made revision-proof ('met at any point in the
prior 8 weeks').  Full verification, the hazard, and how far the END dates move under the
same revision noise."""
exec(open("stage105_robustfloor.py").read().split('print("%-34s %-10s')[0])
import numpy as np, pandas as pd, os
from scipy import stats as sst
def machine(W=8,gf=0.03,cf=0.12):
    m8=ic.rolling(8).mean(); rr=(m8/m8.shift(1).rolling(52).min()-1)
    CLx=np.nan_to_num(sd(rr,5),nan=-9)
    k=W*7
    co=pd.Series(CLx>=gf).rolling(k,min_periods=1).max().fillna(0).astype(bool).values
    cco=pd.Series(CLx>=cf).rolling(k,min_periods=1).max().fillna(0).astype(bool).values
    F=[np.asarray(D(Srel>=0.36-1e-9),bool),np.asarray(gapch(iur4,0.40),bool),
       np.asarray(D(pd.Series((pay.d1.astype(float)<=-0.18).values,index=pd.to_datetime(pay.rel.values))),bool),
       HOU,np.asarray(fall(tb6,60,1.45),bool)]
    fr=np.zeros(N,bool)
    for c in F: fr|=fresh(c&co,120)&G
    CLA=np.asarray(D(Srel>=0.55-1e-9),bool)&cco
    fr|=fresh(CLA&NG,120)
    la=fresh(np.asarray(lane_arr(vix-vix.shift(20),1,22.0),bool),120); valid=la.copy(); lv=[]
    for i in np.flatnonzero(np.diff(la.astype(np.int8))==1)+1:
        if not fr[i:i+121].any():
            j=i
            while j<N and la[j]: valid[j]=False; j+=1
            if cal[i]>=pd.Timestamp("1968-06-01"): lv.append(str(cal[i].date()))
    eps=replay(fr|valid); res,f=score_eps(eps,T_P1)
    fz=fresh(CLA,120); rN,_=score_eps(replay(fz),T_P1)
    armed=np.zeros(N,bool)
    for c in F: armed|=(c&co&G)
    armed|=(CLA&NG)
    return (eps,[x["lag"] for x in res],[x["end_lag"] for x in res],[x["tr_err"] for x in res],f,
            sum(1 for x in rN if x["lag"] is not None),int((armed&QC).sum()),lv,co,cco)
eps,l,e,t,f,n,arm,lv,co,cco=machine()
print("v11: onsets %s" % [str(x["onset"].date()) for x in eps])
print("     lags %s | ends %s | troughs %s | false %s | no-inv %d/9 | lane %s | quiet-armed %d"
      % (l,e,t,f if f else 0,n,lv,arm))
S=Srel.reindex(cal).ffill().values.astype(float)
IURg=sd(iur4-iur4.rolling(52).min(),12)
PAY1=sd(pd.Series(pay.d1.astype(float).values,index=pd.to_datetime(pay.rel.values)),0)
H6=np.minimum.reduce([sd(-h6.shift(j)) for j in range(3)]); BILL=sd(-(tb6-tb6.shift(60)),1)
share=0.40
def haz(v,thr,gated=True,mask=None):
    m=QC&(G if gated else np.ones(N,bool))&(mask if mask is not None else np.ones(N,bool))
    s=pd.Series(v[m],index=cal[m]).dropna()
    am=s.groupby(s.index.year).max(); am=am[s.groupby(s.index.year).size()>=30]
    if len(am)<8: return 0.0
    c,loc,sc=sst.genextreme.fit(am.values)
    ya=pd.Series(cal[QC&(G if gated else np.ones(N,bool))]).dt.year.nunique()
    return float(sst.genextreme.sf(thr,c,loc,sc))*(len(am)/max(ya,1))*(share if gated else 1-share)
H={"Sahm fast":haz(S,0.36,True,co),"IUR fast":haz(IURg,0.40,True,co),"payrolls fast":haz(-PAY1,0.18,True,co),
   "housing fast":haz(H6,0.19,True,co),"bill fast":haz(BILL,1.45,True,co),"Sahm clause":haz(S,0.55,False,cco)}
u=1-np.prod([1-p for p in H.values()])
print("\nv11 hazard by channel:", {k:round(v,5) for k,v in sorted(H.items(),key=lambda kv:-kv[1])})
print("union %.4f/yr -> 1 in %.0f years | 6.5-yr %.0f%% | 10-yr %.0f%%" % (u,1/u,100*(1-(1-u)**6.5),100*(1-(1-u)**10)))
for det in (0.867,0.955): print("  detection %.3f x no false alarm over 6.5 yr = %.0f%%" % (det,100*det*(1-u)**6.5))
# end-date dispersion under revision noise
df=pd.read_csv(os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03/data_fetched/other/icsa_first_vs_current.csv"),parse_dates=["week"])
df["fv"]=pd.to_datetime(df.first_vintage.astype(str),format="%Y%m%d")
g=df[df.fv>pd.Timestamp("2009-05-28")]; rev=((g.first_print/g.current)-1).values; rev=rev[np.isfinite(rev)]
rng=np.random.default_rng(5); R=120
shift=[[] for _ in range(9)]
for b in range(R):
    e_=rng.choice(rev,size=len(ic),replace=True)
    noisy=pd.Series(ic.values*(1+e_),index=ic.index)
    d2,en2,f2,_=build3(ic,noisy,8,0.03,0.12)
    if len(en2)!=9: continue
    for i,(a,bb) in enumerate(zip(en2,REFe)): shift[i].append((pd.Timestamp(a)-pd.Timestamp(bb)).days)
print("\nEND-date movement under the same claims-revision noise (median, and 10th-90th percentile, days):")
for i,nm in enumerate(REFe):
    s=np.array(shift[i])
    if len(s): print("   end %s : median %+.0f d, 10-90%% %+.0f..%+.0f d" % (nm,np.median(s),np.percentile(s,10),np.percentile(s,90)))
