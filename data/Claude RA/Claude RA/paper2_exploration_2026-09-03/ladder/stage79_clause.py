"""Stage 79: cut the Sahm clause's exposure without losing 2024 in the no-inversion world.
Two routes: (A) raise the line and accept 8/9 there; (B) keep 0.55 but add a cheap
co-condition that was true in every recession window and is rare in quiet periods."""
exec(open("stage46_v7.py").read().split("t6,l6=build")[0])
import numpy as np, pandas as pd, os
from scipy import stats as sst
G=np.asarray(GATE[12],bool); NG=~G
WINS=[(pd.Timestamp(p),pd.Timestamp(t)) for p,t in T_P1]
QUIET=np.ones(N,bool)&(cal>=pd.Timestamp("1968-06-01"))
for p,t in WINS: QUIET &= ~((cal>=p-pd.DateOffset(months=6))&(cal<=t+pd.DateOffset(months=12)))
def evt(vals_daily, thr):
    v=pd.Series(vals_daily[QUIET],index=cal[QUIET]).dropna()
    am=v.groupby(v.index.year).max(); am=am[v.groupby(v.index.year).size()>=60]
    if len(am)<12: return np.nan
    c,loc,sc=sst.genextreme.fit(am.values); return float(sst.genextreme.sf(thr,c,loc,sc))
S=Srel.reindex(cal).ffill().values.astype(float)
share=0.40
print("(A) raising the clause")
for th in [0.55,0.70,1.00,1.50]:
    p=evt(S,th)*(1-share)
    fz=fresh(np.asarray(D(Srel>=th-1e-9),bool),120); r,_=score_eps(replay(fz),T_P1)
    print("   line %.2f  hazard %.5f/yr (1 in %5.0f)  no-inv %d/9" % (th,p,1/p,sum(1 for x in r if x["lag"] is not None)))
# co-conditions
g4=gapch_val(iur4) if "gapch_val" in dir() else None
iurgap=(iur4-iur4.rolling(52).min())
def sd(s,lag):
    x=s.copy(); x.index=x.index+pd.Timedelta(days=lag); return x.reindex(cal).ffill().values.astype(float)
IG=sd(iurgap,12)
CL=sd(r8,5)
PY3=sd(pd.Series(pay.d1.astype(float).values,index=pd.to_datetime(pay.rel.values)).rolling(3).sum(),0)
CO={"IUR gap >= 0.05":IG>=0.05,"IUR gap >= 0.10":IG>=0.10,"IUR gap >= 0.15":IG>=0.15,
    "claims 8wk >= 5% over min":CL>=0.05,"claims 8wk >= 10%":CL>=0.10,
    "payrolls 3m change <= 0":PY3<=0.0}
print("\n(B) clause at 0.55 with a co-condition")
base=np.asarray(D(Srel>=0.55-1e-9),bool)
FAST=[np.asarray(D(Srel>=0.36-1e-9),bool), np.asarray(gapch(iur4,0.40),bool),
      np.asarray(D(pd.Series((pay.d1.astype(float)<=-0.18).values,index=pd.to_datetime(pay.rel.values))),bool),
      np.asarray(persist2(h3,20),bool), np.asarray(fall(tb6,60,1.45),bool)]
def full(clause):
    fr=np.zeros(N,bool)
    for c in FAST: fr|=fresh(c,120)&G
    fr|=fresh(np.asarray(clause,bool)&NG,120)
    la=fresh(lane_arr(vix-vix.shift(20),1,22.0),120); valid=la.copy()
    for i in np.flatnonzero(np.diff(la.astype(np.int8))==1)+1:
        if not fr[i:i+121].any():
            j=i
            while j<N and la[j]: valid[j]=False; j+=1
    eps=replay(fr|valid); r,f=score_eps(eps,T_P1)
    fz=fresh(np.asarray(clause,bool),120); rN,_=score_eps(replay(fz),T_P1)
    return [str(e["onset"].date()) for e in eps],[x["lag"] for x in r],f,sum(1 for x in rN if x["lag"] is not None)
REF=['1969-10-06','1973-10-25','1980-01-03','1981-08-18','1990-08-03','2001-02-02','2008-01-04','2020-02-28','2024-05-03']
d,l,f,n=full(base); print("   %-28s dates ok %-5s false %s no-inv %d/9  exposure %5.2f%% of quiet days" %
      ("none (v8)",d==REF,f if f else 0,n,100*(base&QUIET).sum()/QUIET.sum()))
for nm,c in CO.items():
    cc=base&np.nan_to_num(c,nan=False).astype(bool)
    d,l,f,n=full(cc)
    print("   %-28s dates ok %-5s false %s no-inv %d/9  exposure %5.2f%%" %
          (nm,d==REF,f if f else 0,n,100*(cc&QUIET).sum()/QUIET.sum()))
