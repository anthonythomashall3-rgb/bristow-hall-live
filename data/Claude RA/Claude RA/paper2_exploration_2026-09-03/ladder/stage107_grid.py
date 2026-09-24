"""Stage 107: the floor window trades fitted hazard against revision robustness.
Sweep the two windows separately and score BOTH: the extreme-value hazard (which assumes
the claims data are exact) and the empirical false-episode rate under resampled revisions
(which does not)."""
exec(open("stage106_v11.py").read().split('eps,l,e,t,f,n,arm,lv,co,cco=machine()')[0])
import numpy as np, pandas as pd, os
from scipy import stats as sst
share=0.40
S=Srel.reindex(cal).ffill().values.astype(float)
IURg=sd(iur4-iur4.rolling(52).min(),12)
PAY1=sd(pd.Series(pay.d1.astype(float).values,index=pd.to_datetime(pay.rel.values)),0)
H6=np.minimum.reduce([sd(-h6.shift(j)) for j in range(3)]); BILL=sd(-(tb6-tb6.shift(60)),1)
def masks(Wf,Wc,gf=0.03,cf=0.12,claims=None):
    c=ic if claims is None else claims
    m8=c.rolling(8).mean(); rr=(m8/m8.shift(1).rolling(52).min()-1)
    CLx=np.nan_to_num(sd(rr,5),nan=-9)
    co=pd.Series(CLx>=gf).rolling(max(Wf,1)*7,min_periods=1).max().fillna(0).astype(bool).values
    cc=pd.Series(CLx>=cf).rolling(max(Wc,1)*7,min_periods=1).max().fillna(0).astype(bool).values
    return co,cc
def run(co,cc):
    F=[np.asarray(D(Srel>=0.36-1e-9),bool),np.asarray(gapch(iur4,0.40),bool),
       np.asarray(D(pd.Series((pay.d1.astype(float)<=-0.18).values,index=pd.to_datetime(pay.rel.values))),bool),
       HOU,np.asarray(fall(tb6,60,1.45),bool)]
    fr=np.zeros(N,bool)
    for c in F: fr|=fresh(c&co,120)&G
    CLA=np.asarray(D(Srel>=0.55-1e-9),bool)&cc
    fr|=fresh(CLA&NG,120)
    la=fresh(np.asarray(lane_arr(vix-vix.shift(20),1,22.0),bool),120); valid=la.copy()
    for i in np.flatnonzero(np.diff(la.astype(np.int8))==1)+1:
        if not fr[i:i+121].any():
            j=i
            while j<N and la[j]: valid[j]=False; j+=1
    eps=replay(fr|valid); res,f=score_eps(eps,T_P1)
    fz=fresh(CLA,120); rN,_=score_eps(replay(fz),T_P1)
    return [str(e["onset"].date()) for e in eps],[str(e["end_call"].date()) for e in eps],f,sum(1 for x in rN if x["lag"] is not None)
def haz(v,thr,gated,mask):
    m=QC&(G if gated else np.ones(N,bool))&mask
    s=pd.Series(v[m],index=cal[m]).dropna()
    am=s.groupby(s.index.year).max(); am=am[s.groupby(s.index.year).size()>=30]
    if len(am)<8: return 0.0
    c,loc,sc=sst.genextreme.fit(am.values)
    ya=pd.Series(cal[QC&(G if gated else np.ones(N,bool))]).dt.year.nunique()
    return float(sst.genextreme.sf(thr,c,loc,sc))*(len(am)/max(ya,1))*(share if gated else 1-share)
df=pd.read_csv(os.path.expanduser("~/mnt/Recession Papers/Claude RA/paper2_exploration_2026-09-03/data_fetched/other/icsa_first_vs_current.csv"),parse_dates=["week"])
df["fv"]=pd.to_datetime(df.first_vintage.astype(str),format="%Y%m%d")
g=df[df.fv>pd.Timestamp("2009-05-28")]; rev=((g.first_print/g.current)-1).values; rev=rev[np.isfinite(rev)]
print("%-14s %-9s %-11s %-13s %s" % ("floor windows","record","EVT hazard","1 in N yrs","false episodes under revision noise (of 150)"))
R=150
for Wf,Wc in [(1,1),(4,4),(8,8),(8,1),(1,8),(4,8),(8,4),(13,13)]:
    co,cc=masks(Wf,Wc)
    d,e,f,n=run(co,cc)
    okrec=(d==REF and e==REFe and not f and n==9)
    H={"a":haz(S,0.36,True,co),"b":haz(IURg,0.40,True,co),"c":haz(-PAY1,0.18,True,co),
       "d":haz(H6,0.19,True,co),"e":haz(BILL,1.45,True,co),"f":haz(S,0.55,False,cc)}
    u=1-np.prod([1-p for p in H.values()])
    rng=np.random.default_rng(21); fa=0
    for b in range(R):
        e_=rng.choice(rev,size=len(ic),replace=True)
        co2,cc2=masks(Wf,Wc,claims=pd.Series(ic.values*(1+e_),index=ic.index))
        d2,e2,f2,_=run(co2,cc2)
        if f2: fa+=1
    print("%-14s %-9s %-11.4f %-13.0f %d (%.0f%%)" % ("fast %2d / clause %2d"%(Wf,Wc),
          "ok" if okrec else "CHANGED", u, 1/u, fa, 100*fa/R))
