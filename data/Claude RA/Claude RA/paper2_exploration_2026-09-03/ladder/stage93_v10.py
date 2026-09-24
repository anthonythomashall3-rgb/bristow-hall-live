"""Stage 93: v10 -- replace the housing channel (starts, 3-month fall, twice, line 0.200,
margin 0.006) with starts, 6-month fall, three consecutive releases, line 0.19.  Quiet
max 0.122 against a 1981 reading of 0.257: a margin of 0.135, twenty-two times the old
one, and it carries four recessions instead of one."""
exec(open("stage46_v7.py").read().split("t6,l6=build")[0])
exec(open("stage44_evt.py").read().split("print(\"\\n=== (B) EXTREME")[0])
import numpy as np, pandas as pd
from scipy import stats as sst
G=np.asarray(GATE[12],bool); NG=~G
QC=(~allowed)&(~openmask)&(cal>=pd.Timestamp("1968-06-01"))
def sd(s,lag=0):
    x=s.copy(); x.index=x.index+pd.Timedelta(days=lag); return x.reindex(cal).ffill().values.astype(float)
CL=np.nan_to_num(sd(r8,5),nan=-9); CO=CL>=0.03; CCO=CL>=0.12
h6=fpch("HOUST_all_vintages.csv",6)
def persist_k(series, th, k):
    a=(series<=-th)
    for j in range(1,k): a=a & series.shift(j).le(-th)
    return np.asarray(D(a.fillna(False)),bool)
REF=['1969-10-06','1973-10-25','1980-01-03','1981-08-18','1990-08-03','2001-02-02','2008-01-04','2020-02-28','2024-05-03']
def run(house_arr, label):
    F=[np.asarray(D(Srel>=0.36-1e-9),bool),np.asarray(gapch(iur4,0.40),bool),
       np.asarray(D(pd.Series((pay.d1.astype(float)<=-0.18).values,index=pd.to_datetime(pay.rel.values))),bool),
       house_arr, np.asarray(fall(tb6,60,1.45),bool)]
    fr=np.zeros(N,bool)
    for c in F: fr|=fresh(c&CO,120)&G
    CLA=np.asarray(D(Srel>=0.55-1e-9),bool)&CCO
    fr|=fresh(CLA&NG,120)
    la=fresh(np.asarray(lane_arr(vix-vix.shift(20),1,22.0),bool),120); valid=la.copy(); lv=[]
    for i in np.flatnonzero(np.diff(la.astype(np.int8))==1)+1:
        if not fr[i:i+121].any():
            j=i
            while j<N and la[j]: valid[j]=False; j+=1
            if cal[i]>=pd.Timestamp("1968-06-01"): lv.append(str(cal[i].date()))
    eps=replay(fr|valid); res,false=score_eps(eps,T_P1)
    fz=fresh(CLA,120); rN,_=score_eps(replay(fz),T_P1)
    armed=np.zeros(N,bool)
    for c in F: armed|=(c&CO&G)
    armed|=(CLA&NG)
    d=[str(e["onset"].date()) for e in eps]
    print("%-26s dates %-9s | lags %s | ends %s | trough %s | false %s | no-inv %d/9 | lane %s | quiet-armed days %d"
          % (label,"identical" if d==REF else "CHANGED",[x["lag"] for x in res],[x["end_lag"] for x in res],
             [x["tr_err"] for x in res],false if false else 0,
             sum(1 for x in rN if x["lag"] is not None),lv,int((armed&QC).sum())))
    if d!=REF: print("   ",d)
    return eps
run(np.asarray(persist2(h3,20),bool),"v9 (starts 3m x2, 0.200)")
for th,k in [(0.19,3),(0.18,3),(0.20,3),(0.27,2)]:
    run(persist_k(h6,th,k), "v10 (starts 6m x%d, %.2f)"%(k,th))
# hazard of the new channel
v=np.minimum.reduce([sd(-h6.shift(j)) for j in range(3)])
q=pd.Series(v[QC&CO&G],index=cal[QC&CO&G]).dropna()
am=q.groupby(q.index.year).max(); am=am[q.groupby(q.index.year).size()>=30]
c,loc,sc=sst.genextreme.fit(am.values)
share=0.40
print("\nnew housing channel hazard at 0.19: %.5f/yr (was 0.01009)" % (float(sst.genextreme.sf(0.19,c,loc,sc))*share))
