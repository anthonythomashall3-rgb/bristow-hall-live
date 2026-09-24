"""Stage 114: the a-priori rule in detail.  'Every channel fires when it exceeds its own
calm-period maximum by c percent' -- one parameter, no recession ever consulted."""
exec(open("stage113_apriori.py").read().split('d,l,f,n,a=build(V11)')[0])
import numpy as np, pandas as pd
from scipy import stats as sst
FIRST=["1970-01-01","1973-12-01","1980-02-01","1981-08-01","1990-08-01","2001-04-01","2008-01-01","2020-03-01","2024-05-01"]
def full(th):
    F=[np.asarray(D(Srel>=th["Sahm"]-1e-9),bool), np.asarray(gapch(iur4,th["IUR"]),bool),
       np.asarray(D(pd.Series((pay.d1.astype(float)<=-th["payrolls"]).values,index=pd.to_datetime(pay.rel.values))),bool),
       persist_k(h6,th["housing"],3), np.asarray(fall(tb6,60,th["bill"]),bool)]
    fr=np.zeros(N,bool)
    for c in F: fr|=fresh(c&CO,120)&G
    CLA=np.asarray(D(Srel>=th["clause"]-1e-9),bool)&CCO
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
    for c in F: armed|=(c&CO&G)
    armed|=(CLA&NG)
    return (eps,[x["lag"] for x in res],[x["end_lag"] for x in res],[x["tr_err"] for x in res],f,
            sum(1 for x in rN if x["lag"] is not None),int((armed&QC).sum()),lv,CO,CCO)
share=0.40
def haz(v,thr,gated,mask):
    m=QC&(G if gated else np.ones(N,bool))&mask
    s=pd.Series(v[m],index=cal[m]).dropna()
    am=s.groupby(s.index.year).max(); am=am[s.groupby(s.index.year).size()>=30]
    if len(am)<8: return 0.0
    c,loc,sc=sst.genextreme.fit(am.values)
    ya=pd.Series(cal[QC&(G if gated else np.ones(N,bool))]).dt.year.nunique()
    return float(sst.genextreme.sf(thr,c,loc,sc))*(len(am)/max(ya,1))*(share if gated else 1-share)
for mult in (1.00,1.02,1.05):
    th={k:round(qline(STAT[k][0],STAT[k][1],1.00,mult),3) for k in V11}
    eps,l,e,t,f,n,a,lv,co,cco=full(th)
    if len(eps)<9: print("c=%.0f%%: only %d episodes"%(100*(mult-1),len(eps))); continue
    d=[str(x["onset"].date()) for x in eps]
    dd=[(pd.Timestamp(d[i])-pd.Timestamp(FIRST[i])).days for i in range(9)]
    H={"Sahm":haz(S,th["Sahm"],True,co),"IUR":haz(IURg,th["IUR"],True,co),"pay":haz(-PAY1,th["payrolls"],True,co),
       "hou":haz(H6,th["housing"],True,co),"bill":haz(BILL,th["bill"],True,co),"clause":haz(S,th["clause"],False,cco)}
    u=1-np.prod([1-p for p in H.values()])
    print("\nc = %.0f%%  thresholds %s" % (100*(mult-1),th))
    print("   onsets %s" % d)
    print("   lags %s | ends %s | troughs %s | false %s | no-inv %d/9 | armed %d | lane %s" % (l,e,t,f if f else 0,n,a,lv))
    print("   days from the recession's first day %s   (v11: [-87,-37,-29,17,2,-58,3,-2,2], total lateness 22)" % dd)
    print("   fitted hazard %.4f/yr (1 in %.0f) | inside +-1 month: %d of 9" % (u,1/max(u,1e-9),sum(1 for x in l if x is not None and abs(x)<=1)))
