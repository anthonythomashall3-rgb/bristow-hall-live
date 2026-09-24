"""Stage 78: can the Sahm clause be RAISED if a U-4 channel covers 2024?
In v8 the no-inversion world is carried entirely by the Sahm clause, so first find
which recession binds as the line rises; then price U-4 as a supplement."""
exec(open("stage46_v7.py").read().split("t6,l6=build")[0])
import numpy as np, pandas as pd, os
from scipy import stats as sst
G=np.asarray(GATE[12],bool); NG=~G
print("no-inversion world carried by the Sahm clause alone, as the line rises:")
for th in [0.55,0.58,0.60,0.70,0.90,1.20,1.50,1.80,2.10,2.40]:
    fz=fresh(np.asarray(D(Srel>=th-1e-9),bool),120)
    r,f=score_eps(replay(fz),T_P1)
    miss=[str(p)[:7] for (p,t),x in zip(T_P1,r) if x["lag"] is None]
    print("   %.2f -> %d/9   missing %s" % (th, 9-len(miss), miss))
u4=load(os.path.join(ODD,"01_labor_unemployment/monthly/U4RATE.csv"))
u5=load(os.path.join(ODD,"01_labor_unemployment/monthly/U5RATE.csv"))
u6=load(os.path.join(ODD,"01_labor_unemployment/monthly/U6RATE.csv"))
print("\nU-4 %s..%s  U-5 %s..%s  U-6 %s..%s" % (u4.index[0].date(),u4.index[-1].date(),
      u5.index[0].date(),u5.index[-1].date(),u6.index[0].date(),u6.index[-1].date()))
WINS=[(pd.Timestamp(p),pd.Timestamp(t)) for p,t in T_P1]
def score_stat(s, lag_days=5, label=""):
    """max-margin line on the machine's quiet set, then EVT hazard."""
    x=s.copy(); x.index=x.index+pd.Timedelta(days=lag_days)
    v=x.reindex(cal).ffill()
    q=np.ones(N,bool)&(cal>=pd.Timestamp("1968-06-01"))
    for (pp,tt) in WINS: q &= ~((cal>=pp-pd.DateOffset(months=6))&(cal<=tt+pd.DateOffset(months=12)))
    vq=pd.Series(v.values[q],index=cal[q]).dropna()
    if len(vq)<500: return None
    qm=float(vq.max())
    # the reading inside each recession window
    pk={}
    for (p,t) in WINS:
        m=(cal>=p-pd.DateOffset(months=6))&(cal<=t)
        vv=pd.Series(v.values[m],index=cal[m]).dropna()
        if len(vv): pk[str(p.date())[:7]]=float(vv.max())
    carried={k:val for k,val in pk.items() if val>qm}
    if not carried: return None
    thr=(qm+min(carried.values()))/2
    am=vq.groupby(vq.index.year).max(); am=am[vq.groupby(vq.index.year).size()>=60]
    p_=np.nan
    if len(am)>=12:
        c,loc,sc=sst.genextreme.fit(am.values); p_=float(sst.genextreme.sf(thr,c,loc,sc))
    return dict(qmax=qm,thr=thr,carried=sorted(carried),p=p_,nyrs=len(am),pk=pk)
print("\n%-22s %8s %8s %6s %10s %s" % ("candidate","quietmax","line","yrs","hazard/yr","carries"))
for nm,s,f in [("U-4, 12m %change",u4,lambda z:(z/z.shift(12)-1)*100),
               ("U-5, 12m %change",u5,lambda z:(z/z.shift(12)-1)*100),
               ("U-6, 12m %change",u6,lambda z:(z/z.shift(12)-1)*100),
               ("U-4 gap over 12m min",u4,lambda z:z.rolling(3).mean()-z.rolling(12).min()),
               ("U-5 gap over 12m min",u5,lambda z:z.rolling(3).mean()-z.rolling(12).min()),
               ("U-6 gap over 12m min",u6,lambda z:z.rolling(3).mean()-z.rolling(12).min())]:
    r=score_stat(f(s).dropna())
    if r is None: print("%-22s  no clean line" % nm); continue
    print("%-22s %8.3f %8.3f %6d %10.5f %s" % (nm,r["qmax"],r["thr"],r["nyrs"],r["p"],r["carried"]))
