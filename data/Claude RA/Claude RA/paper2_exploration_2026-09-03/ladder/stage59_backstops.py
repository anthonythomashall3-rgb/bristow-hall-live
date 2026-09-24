"""Stage 59: the two ungated backstops (Sahm >= 0.55, bill fall >= 2.5 pp/60d) carry
two thirds of v7's false-alarm hazard (round 17 EVT) and are the top offenders on the
foreign panel too (round 19).  What do they buy?  Raise each, and re-run both the
record and the no-inversion simulation that justified them."""
exec(open("stage46_v7.py").read().split("t6,l6=build")[0])
import numpy as np, pandas as pd, itertools
S = Srel.reindex(cal).ffill().values.astype(float)
V7fastA = [SAHM[0.35], gapch(iur4,0.40), PAY, persist2(h3,20), fall(tb6,60,1.43)]
BSNAMES = ['Sahm>=0.55 x1 [nogate]','IUR gap>=0.5 [nogate]','claims 8wk>=40% [nogate]',
           'bill fall>=2.5/60d [nogate]','housing -25% x2 [nogate]','IP 3m first print <=-2.0% x2 [nogate]']

def machine(sahm_bs, bill_bs, gate_on=True, lane_on=True, drop=()):
    bs = []
    for nm in BSNAMES:
        if nm in drop: continue
        if nm.startswith("Sahm"):
            bs.append(D(Srel >= sahm_bs - 1e-9) if sahm_bs is not None else None)
        elif nm.startswith("bill"):
            bs.append(np.asarray(fall(tb6,60,bill_bs), bool) if bill_bs is not None else None)
        else:
            bs.append(np.asarray(BS[nm], bool))
    frozen = np.zeros(N, bool)
    g = GATE[12] if gate_on else np.ones(N, bool)
    for c in V7fastA: frozen |= fresh(c,120) & g
    for c in bs:
        if c is not None: frozen |= fresh(c,120)
    if not lane_on: return frozen, []
    lanearr = np.zeros(N, bool)
    for nm in LANE2: lanearr |= fresh(LANE[nm],120)
    valid = lanearr.copy(); lfa = []
    for i in np.flatnonzero(np.diff(lanearr.astype(np.int8))==1)+1:
        if not frozen[i:i+121].any():
            j=i
            while j<N and lanearr[j]: valid[j]=False; j+=1
            if cal[i]>=pd.Timestamp("1968-06-01"): lfa.append(str(cal[i].date()))
    return frozen | valid, lfa

def report(lab, sahm_bs, bill_bs, drop=()):
    t, lfa = machine(sahm_bs, bill_bs, True, True, drop)
    eps = replay(t); res, false = score_eps(eps, T_P1)
    lags = [r["lag"] for r in res]
    # the no-inversion world: gate forced off, fast channels ungated is not the test;
    # the test is whether the machine still calls with the gate never armed.
    t0, _ = machine(sahm_bs, bill_bs, False, True, drop)
    eps0 = replay(t0); res0, false0 = score_eps(eps0, T_P1)
    # the honest no-inversion test: gate NEVER arms, so gated fast channels are silent
    frozen = np.zeros(N, bool)
    bsl = []
    for nm in BSNAMES:
        if nm in drop: continue
        if nm.startswith("Sahm"): bsl.append(D(Srel >= sahm_bs - 1e-9) if sahm_bs is not None else None)
        elif nm.startswith("bill"): bsl.append(np.asarray(fall(tb6,60,bill_bs), bool) if bill_bs is not None else None)
        else: bsl.append(np.asarray(BS[nm], bool))
    for c in bsl:
        if c is not None: frozen |= fresh(c,120)
    epsN = replay(frozen); resN, falseN = score_eps(epsN, T_P1)
    nN = sum(1 for r in resN if r["lag"] is not None)
    print("%-34s %-8s %-32s %-6s %s" % (
        lab, false if false else "0",
        str(lags), "%d/9" % nN, falseN if falseN else "0"))

print("%-34s %-8s %-32s %-6s %s" % ("variant","false","onset lags (1969..2024)","no-inv","no-inv false"))
report("v7 as frozen (0.55 / 2.50)", 0.55, 2.50)
for s in [0.60, 0.70, 0.80, 1.00]:
    report("Sahm backstop %.2f" % s, s, 2.50)
for b in [2.60, 2.80, 3.00, 3.50]:
    report("bill backstop %.2f" % b, 0.55, b)
report("both raised (0.70 / 3.00)", 0.70, 3.00)
report("Sahm backstop removed", None, 2.50, drop=('Sahm>=0.55 x1 [nogate]',))
report("bill backstop removed", 0.55, None, drop=('bill fall>=2.5/60d [nogate]',))
report("both removed", None, None, drop=('Sahm>=0.55 x1 [nogate]','bill fall>=2.5/60d [nogate]'))
