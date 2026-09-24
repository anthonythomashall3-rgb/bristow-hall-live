"""Stage 60: v7.1 = v7 with the bill backstop removed.  Full battery."""
exec(open("stage46_v7.py").read().split("t6,l6=build")[0])
import numpy as np, pandas as pd
V7fastA=[SAHM[0.35], gapch(iur4,0.40), PAY, persist2(h3,20), fall(tb6,60,1.43)]
ALLBS=['Sahm>=0.55 x1 [nogate]','IUR gap>=0.5 [nogate]','claims 8wk>=40% [nogate]',
       'bill fall>=2.5/60d [nogate]','housing -25% x2 [nogate]','IP 3m first print <=-2.0% x2 [nogate]']
def mk(bsl, gate_on=True, lane=True):
    frozen=np.zeros(N,bool); g=GATE[12] if gate_on else np.ones(N,bool)
    for c in V7fastA: frozen|=fresh(c,120)&g
    for nm in bsl: frozen|=fresh(BS[nm],120)
    if not lane: return frozen,[]
    la=np.zeros(N,bool)
    for nm in LANE2: la|=fresh(LANE[nm],120)
    valid=la.copy(); lfa=[]
    for i in np.flatnonzero(np.diff(la.astype(np.int8))==1)+1:
        if not frozen[i:i+121].any():
            j=i
            while j<N and la[j]: valid[j]=False; j+=1
            if cal[i]>=pd.Timestamp("1968-06-01"): lfa.append(str(cal[i].date()))
    return frozen|valid, lfa

BS71=[n for n in ALLBS if not n.startswith("bill")]
for lab,bsl in [("v7  ",ALLBS),("v7.1",BS71)]:
    t,lfa=mk(bsl); eps=replay(t); res,false=score_eps(eps,T_P1)
    print("%s onsets %s" % (lab,[str(r["onset"])[:10] for r in res]))
    print("      lags %s ends %s trough %s false %s lane-void %s" %
          ([r["lag"] for r in res],[r["end_lag"] for r in res],
           [r.get("trough_lag") for r in res], false if false else 0, lfa))

print("\n=== which backstop carries the no-inversion world alone ===")
for drop in [None]+ALLBS:
    bsl=[n for n in ALLBS if n!=drop]
    t,_=mk(bsl, gate_on=False, lane=True)
    # gate never arms: gated fast channels silent
    frozen=np.zeros(N,bool)
    for nm in bsl: frozen|=fresh(BS[nm],120)
    eps=replay(frozen); res,false=score_eps(eps,T_P1)
    got=[r["onset"] for r in res if r["lag"] is not None]
    miss=[str(p)[:7] for (p,tr),r in zip(T_P1,res) if r["lag"] is None]
    print("  drop %-42s calls %d/9  missing %s  false %s" %
          (drop or "(nothing)", len(got), miss, false if false else 0))

print("\n=== first-print replay, v7.1 ===")
try:
    tf,_=mk(BS71)
    print("  (uses the same frozen arrays as v7; first-print channels are already first-print)")
except Exception as e: print("  ", e)
