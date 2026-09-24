"""Stage 57: the rate-channel labour guard (G1), found by the international replay,
tested on the actual US v7 machinery."""
exec(open("stage46_v7.py").read().split("t6,l6=build")[0])
import numpy as np, pandas as pd
S = Srel.reindex(cal).ffill().values.astype(float)
print("Srel on the days the bill channel first fires in each episode:")
billF = fall(tb6,60,1.43); billB = BS['bill fall>=2.5/60d [nogate]']
for nm, arr in [("bill fast 1.43", billF), ("bill backstop 2.50", billB)]:
    on = np.flatnonzero(np.diff(np.asarray(arr, bool).astype(np.int8)) == 1) + 1
    on = [i for i in on if cal[i] >= pd.Timestamp("1968-06-01")]
    print(" ", nm, [(str(cal[i].date()), None if np.isnan(S[i]) else round(float(S[i]),2)) for i in on][:20])

print("\n%-24s %-11s %-46s %s" % ("guard on the bill channel","false eps","onset lags","ends"))
for g in [None, 0.0, 0.05, 0.10, 0.15, 0.20, 0.30]:
    if g is None:
        bf, bb = billF, billB
    else:
        ok = np.nan_to_num(S, nan=-9) >= g - 1e-12
        bf = np.asarray(billF, bool) & ok
        bb = np.asarray(billB, bool) & ok
    fast = [SAHM[0.35], gapch(iur4,0.40), PAY, persist2(h3,20), bf]
    BS2 = dict(BS); BS2['bill fall>=2.5/60d [nogate]'] = bb
    frozen = np.zeros(N, bool)
    for c in fast: frozen |= fresh(c,120) & GATE[12]
    for nm in ['Sahm>=0.55 x1 [nogate]','IUR gap>=0.5 [nogate]','claims 8wk>=40% [nogate]',
               'bill fall>=2.5/60d [nogate]','housing -25% x2 [nogate]',
               'IP 3m first print <=-2.0% x2 [nogate]']:
        frozen |= fresh(BS2[nm],120)
    lanearr = np.zeros(N, bool)
    for nm in LANE2: lanearr |= fresh(LANE[nm],120)
    valid = lanearr.copy(); lfa = []
    for i in np.flatnonzero(np.diff(lanearr.astype(np.int8))==1)+1:
        if not frozen[i:i+121].any():
            j=i
            while j<N and lanearr[j]: valid[j]=False; j+=1
            if cal[i]>=pd.Timestamp("1968-06-01"): lfa.append(str(cal[i].date()))
    eps = replay(frozen | valid); res, false = score_eps(eps, T_P1)
    lab = "none (v7 as frozen)" if g is None else "Sahm reading >= %.2f" % g
    print("%-24s %-11s %-46s %s" % (lab, false, [r["lag"] for r in res], [r["end_lag"] for r in res]))
    if g in (None, 0.10, 0.20):
        print("      onsets:", [str(r["onset"]) for r in res], "| lane voided:", lfa)
