"""Stage 81: one global co-condition instead of five bespoke ones.
'No episode opens unless the 8-week average of initial claims is at least X% above its
52-week minimum.'  One parameter, one economic idea: no recession call without a rise in
layoffs.  Find the largest X that leaves every onset date, every end date and the
no-inversion world untouched."""
exec(open("stage46_v7.py").read().split("t6,l6=build")[0])
import numpy as np, pandas as pd
G=np.asarray(GATE[12],bool); NG=~G
WINS=[(pd.Timestamp(p),pd.Timestamp(t)) for p,t in T_P1]
QUIET=np.ones(N,bool)&(cal>=pd.Timestamp("1968-06-01"))
for p,t in WINS: QUIET &= ~((cal>=p-pd.DateOffset(months=6))&(cal<=t+pd.DateOffset(months=12)))
def sd(s,lag):
    x=s.copy(); x.index=x.index+pd.Timedelta(days=lag); return x.reindex(cal).ffill().values.astype(float)
CL=sd(r8,5)
FAST={"sahm":np.asarray(D(Srel>=0.36-1e-9),bool),"iur":np.asarray(gapch(iur4,0.40),bool),
      "pay":np.asarray(D(pd.Series((pay.d1.astype(float)<=-0.18).values,index=pd.to_datetime(pay.rel.values))),bool),
      "hou":np.asarray(persist2(h3,20),bool),"bill":np.asarray(fall(tb6,60,1.45),bool)}
CLAUSE=np.asarray(D(Srel>=0.55-1e-9),bool); LANE=np.asarray(lane_arr(vix-vix.shift(20),1,22.0),bool)
REF=['1969-10-06','1973-10-25','1980-01-03','1981-08-18','1990-08-03','2001-02-02','2008-01-04','2020-02-28','2024-05-03']
def build(X, apply_to_lane=False):
    co=np.nan_to_num(CL,nan=-9)>=X
    fr=np.zeros(N,bool)
    for c in FAST.values(): fr|=fresh(c&co,120)&G
    fr|=fresh(CLAUSE&co&NG,120)
    la=fresh(LANE&co,120) if apply_to_lane else fresh(LANE,120)
    valid=la.copy(); lv=[]
    for i in np.flatnonzero(np.diff(la.astype(np.int8))==1)+1:
        if not fr[i:i+121].any():
            j=i
            while j<N and la[j]: valid[j]=False; j+=1
            if cal[i]>=pd.Timestamp("1968-06-01"): lv.append(str(cal[i].date()))
    eps=replay(fr|valid); r,f=score_eps(eps,T_P1)
    fz=fresh(CLAUSE&co,120); rN,_=score_eps(replay(fz),T_P1)
    armed=np.zeros(N,bool)
    for c in FAST.values(): armed|=(c&co&G)
    armed|=(CLAUSE&co&NG)
    return ([str(e["onset"].date()) for e in eps],[str(e["end_call"].date()) for e in eps],
            f,sum(1 for x in rN if x["lag"] is not None),lv,100*(armed&QUIET).sum()/QUIET.sum())
d0,e0,f0,n0,lv0,x0=build(-9)
print("v8 baseline: dates ok %s | ends %s | false %s | no-inv %d/9 | quiet exposure %.3f%%" % (d0==REF,"ok",f0 if f0 else 0,n0,x0))
print("\n%-8s %-8s %-7s %-7s %-8s %-12s %s" % ("X","dates","ends","false","no-inv","exposure","lane voided"))
bestX=None
for X in [0.0,0.01,0.02,0.03,0.04,0.05,0.06,0.08,0.10,0.15]:
    d,e,f,n,lv,x=build(X)
    ok=(d==REF and e==e0 and not f and n==9)
    if ok: bestX=X
    print("%-8.2f %-8s %-7s %-7s %-8s %-12.3f %s" % (X,"ok" if d==REF else "BROKEN","ok" if e==e0 else "BROKEN",
          len(f) if f else 0,"%d/9"%n,x,lv))
print("\nlargest global claims floor that costs nothing: X = %.2f (claims 8-week average %.0f%% above its 52-week minimum)" % (bestX,100*bestX))
d,e,f,n,lv,x=build(bestX)
print("  quiet exposure %.3f%% of quiet days, from %.3f%% -- a %.0f%% reduction" % (x,x0,100*(1-x/x0)))
