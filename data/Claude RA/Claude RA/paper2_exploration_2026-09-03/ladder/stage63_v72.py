"""Stage 63: v7.2 -- restrict the three backstops that DOMINATE a fast channel
(Sahm 0.55 > 0.35, IUR 0.50 > 0.40, housing 25% > 20%) to fire only when the curve
gate is NOT armed.  This cannot change any call: whenever the gate IS armed and the
backstop threshold is met, the same series has already met the looser fast threshold
on the same day with the same freshness, so the fast channel has already fired.
It removes those three channels' exposure in every year the gate is armed."""
exec(open("stage46_v7.py").read().split("t6,l6=build")[0])
import numpy as np, pandas as pd
G = np.asarray(GATE[12], bool); NG = ~G
FAST=[SAHM[0.35], gapch(iur4,0.40), PAY, persist2(h3,20), fall(tb6,60,1.43)]
def mk(dominated_restricted, bill_bs):
    frozen=np.zeros(N,bool)
    for c in FAST: frozen|=fresh(c,120)&G
    bsl=[("Sahm>=0.55 x1 [nogate]",True),("IUR gap>=0.5 [nogate]",True),
         ("claims 8wk>=40% [nogate]",False),("housing -25% x2 [nogate]",True),
         ("IP 3m first print <=-2.0% x2 [nogate]",False)]
    if bill_bs: bsl.append(("bill fall>=2.5/60d [nogate]",False))
    for nm,dom in bsl:
        a=np.asarray(BS[nm],bool)
        if dominated_restricted and dom: a = a & NG
        frozen|=fresh(a,120)
    la=np.zeros(N,bool)
    for nm in LANE2: la|=fresh(LANE[nm],120)
    valid=la.copy(); lfa=[]
    for i in np.flatnonzero(np.diff(la.astype(np.int8))==1)+1:
        if not frozen[i:i+121].any():
            j=i
            while j<N and la[j]: valid[j]=False; j+=1
            if cal[i]>=pd.Timestamp("1968-06-01"): lfa.append(str(cal[i].date()))
    return frozen|valid, lfa
for lab,dr,bb in [("v7   ",False,True),("v7.1 ",False,False),("v7.2 ",True,False)]:
    t,lfa=mk(dr,bb); eps=replay(t); res,false=score_eps(eps,T_P1)
    print("%s onsets %s" % (lab,[str(r["onset"])[:10] for r in res]))
    print("       lags %s | ends %s | trough %s | false %s | lane-void %s" %
          ([r["lag"] for r in res],[r["end_lag"] for r in res],[r["tr_err"] for r in res],
           false if false else 0, lfa))
print("\nno-inversion world (gate never arms; the five fast channels silent):")
for lab,dr in [("v7.1 backstops",False),("v7.2 backstops (restricted)",True)]:
    frozen=np.zeros(N,bool)
    for nm,dom in [("Sahm>=0.55 x1 [nogate]",True),("IUR gap>=0.5 [nogate]",True),
                   ("claims 8wk>=40% [nogate]",False),("housing -25% x2 [nogate]",True),
                   ("IP 3m first print <=-2.0% x2 [nogate]",False)]:
        a=np.asarray(BS[nm],bool)
        # in this world the gate never arms, so the restriction is vacuous by construction
        frozen|=fresh(a,120)
    eps=replay(frozen); res,false=score_eps(eps,T_P1)
    print("  %-30s calls %d/9 | false %s" % (lab, sum(1 for r in res if r["lag"] is not None), false if false else 0))
print("\nsanity: does any backstop ever open an episode while the gate is armed?")
for nm in ["Sahm>=0.55 x1 [nogate]","IUR gap>=0.5 [nogate]","housing -25% x2 [nogate]"]:
    a=np.asarray(BS[nm],bool)
    lost=int((a & G).sum()); kept=int((a & NG).sum())
    fastnm={"Sahm>=0.55 x1 [nogate]":SAHM[0.35],"IUR gap>=0.5 [nogate]":gapch(iur4,0.40),
            "housing -25% x2 [nogate]":persist2(h3,20)}[nm]
    dom_ok = bool((a & ~np.asarray(fastnm,bool)).sum()==0)
    print("  %-30s days on: %5d armed / %5d not armed | backstop implies fast on every day: %s"
          % (nm, lost, kept, dom_ok))
print("\ngate-armed share of quiet years (round 17): the three restricted backstops lose their exposure there.")
