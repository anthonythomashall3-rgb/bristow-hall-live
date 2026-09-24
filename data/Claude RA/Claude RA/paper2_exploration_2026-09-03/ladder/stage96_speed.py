"""Stage 96: spend the insured-unemployment channel's unused margin on SPEED, scored in
the machine rather than channel by channel -- the earliest channel wins, so a faster form
is only an improvement if every one of the nine lags stays inside a month."""
exec(open("stage46_v7.py").read().split("t6,l6=build")[0])
exec(open("stage44_evt.py").read().split("print(\"\\n=== (B) EXTREME")[0])
import numpy as np, pandas as pd
G=np.asarray(GATE[12],bool); NG=~G
QC=(~allowed)&(~openmask)&(cal>=pd.Timestamp("1968-06-01"))
def sd(s,lag=0):
    x=s.copy(); x.index=x.index+pd.Timedelta(days=lag); return x.reindex(cal).ffill().values.astype(float)
CL=np.nan_to_num(sd(r8,5),nan=-9); CO=CL>=0.03; CCO=CL>=0.12
h6=fpch("HOUST_all_vintages.csv",6)
def persist_k(series,th,k):
    a=(series<=-th)
    for j in range(1,k): a=a & series.shift(j).le(-th)
    return np.asarray(D(a.fillna(False)),bool)
HOU=persist_k(h6,0.19,3)
REF=['1969-10-06','1973-10-25','1980-01-03','1981-08-18','1990-08-03','2001-02-02','2008-01-04','2020-02-28','2024-05-03']
REFd=[pd.Timestamp(x) for x in REF]
def machine(iur_arr):
    F=[np.asarray(D(Srel>=0.36-1e-9),bool), iur_arr,
       np.asarray(D(pd.Series((pay.d1.astype(float)<=-0.18).values,index=pd.to_datetime(pay.rel.values))),bool),
       HOU, np.asarray(fall(tb6,60,1.45),bool)]
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
    eps=replay(fr|valid); res,f=score_eps(eps,T_P1)
    fz=fresh(CLA,120); rN,_=score_eps(replay(fz),T_P1)
    armed=np.zeros(N,bool)
    for c in F: armed|=(c&CO&G)
    armed|=(CLA&NG)
    return ([e["onset"] for e in eps],[x["lag"] for x in res],[x["end_lag"] for x in res],
            f,sum(1 for x in rN if x["lag"] is not None),int((armed&QC).sum()),lv)
base=machine(np.asarray(gapch(iur4,0.40),bool))
print("v10 baseline: lags %s ends %s false %s no-inv %d/9 quiet-armed %d" % (base[1],base[2],base[3],base[4],base[5]))
cands=[]
for w in (2,4,8,13):
    ma=iur.rolling(w).mean()
    for lk in (26,52,78):
        gser=ma-ma.rolling(lk).min(); v=sd(gser,12)
        q=v[QC&CO&G]; q=q[np.isfinite(q)]
        if len(q)<300: continue
        qm=float(np.max(q))
        for extra in (0.02,0.04,0.06,0.08,0.10,0.13,0.16,0.20):
            th=round(qm+extra,3)
            a=np.asarray(np.nan_to_num(v,nan=-9)>=th,bool)
            d,l,e,f,n,arm,lv=machine(a)
            if f or n!=9 or arm!=0: continue
            if any(x is None or abs(x)>1 for x in l): continue
            if e!=base[2]: continue
            days=sum((rd-dd).days for dd,rd in zip(d,REFd))
            if days<=0: continue
            cands.append((days,w,lk,th,qm,[str(x.date()) for x in d],l))
cands.sort(reverse=True)
print("\nIUR forms that keep every lag inside a month, every end unchanged, zero false, zero quiet arming:")
print("%-28s %-9s %s" % ("form","days gained","onset dates / lags"))
for days,w,lk,th,qm,d,l in cands[:8]:
    ch=[("%s->%s"%(REF[i],d[i])) for i in range(9) if d[i]!=REF[i]]
    print("  %2d-wk avg over %2d-wk min, line %.3f (quiet max %.3f)  +%d days  %s  lags %s" % (w,lk,th,qm,days,ch,l))
if not cands: print("  none")
