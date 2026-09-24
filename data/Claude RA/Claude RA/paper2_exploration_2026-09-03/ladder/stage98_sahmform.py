"""Stage 98: sweep the FORM of the Sahm signal, as round 22 did for housing.
The inherited construction is a 3-month mean less the minimum of the prior twelve
monthly 3-month means, at 0.36, margin 0.027 -- the thinnest left.  Try other means,
other lookbacks, and confirming prints, scored in the machine."""
exec(open("stage96_speed.py").read().split("base=machine(")[0])
import numpy as np, pandas as pd
# rebuild the Sahm family from the first-print unemployment series
U=None
for nm in ("ufp","u_fp","unrate_fp","UFP"):
    if nm in dir(): U=eval(nm); break
if U is None:
    # Srel is the 3/12 construction; recover the underlying first-print rate from the vintage file
    import glob, os
    p=os.path.join(ODD,"21_vintage_realtime/alfred_all_vintages")
    U=None
print("underlying first-print unemployment series available:", U is not None)
IUR4=np.asarray(gapch(iur4,0.40),bool)
def sahm_arr(th,k):
    a=(Srel>=th-1e-9)
    for j in range(1,k): a=a & Srel.shift(j).ge(th-1e-9)
    return np.asarray(D(a.fillna(False)),bool)
REFd=[pd.Timestamp(x) for x in REF]
def machine2(sahm_arr_, clause_th=0.55):
    F=[sahm_arr_, IUR4,
       np.asarray(D(pd.Series((pay.d1.astype(float)<=-0.18).values,index=pd.to_datetime(pay.rel.values))),bool),
       HOU, np.asarray(fall(tb6,60,1.45),bool)]
    fr=np.zeros(N,bool)
    for c in F: fr|=fresh(c&CO,120)&G
    CLA=np.asarray(D(Srel>=clause_th-1e-9),bool)&CCO
    fr|=fresh(CLA&NG,120)
    la=fresh(np.asarray(lane_arr(vix-vix.shift(20),1,22.0),bool),120); valid=la.copy()
    for i in np.flatnonzero(np.diff(la.astype(np.int8))==1)+1:
        if not fr[i:i+121].any():
            j=i
            while j<N and la[j]: valid[j]=False; j+=1
    eps=replay(fr|valid); res,f=score_eps(eps,T_P1)
    fz=fresh(CLA,120); rN,_=score_eps(replay(fz),T_P1)
    armed=np.zeros(N,bool)
    for c in F: armed|=(c&CO&G)
    armed|=(CLA&NG)
    return ([e["onset"] for e in eps],[x["lag"] for x in res],[x["end_lag"] for x in res],f,
            sum(1 for x in rN if x["lag"] is not None),int((armed&QC).sum()))
S=Srel.reindex(cal).ffill().values.astype(float)
q=S[QC&CO&G]; q=q[np.isfinite(q)]
print("Sahm gated quiet max with the 3%% claims floor: %.3f" % np.max(q))
base=machine2(sahm_arr(0.36,1))
print("v10 baseline: lags %s ends %s false %s no-inv %d/9 armed %d" % (base[1],base[2],base[3],base[4],base[5]))
print("\n%-18s %-8s %-30s %s" % ("Sahm form","margin","onset dates changed","lags"))
ok=[]
for th in [0.36,0.38,0.40,0.42,0.45,0.48,0.50]:
    for k in (1,2,3):
        d,l,e,f,n,arm=machine2(sahm_arr(th,k))
        good=(not f) and n==9 and arm==0 and e==base[2] and all(x is not None and abs(x)<=2 for x in l)
        if not good: continue
        ch=[("%s->%s"%(REF[i],str(d[i].date()))) for i in range(9) if str(d[i].date())!=REF[i]]
        marg=th-float(np.max(q))
        ok.append((marg,th,k,ch,l))
        print("%-18s %-8.3f %-30s %s" % (">=%.2f x%d"%(th,k), marg, ch if ch else "none", l))
if not ok: print("  nothing beats the current form")
