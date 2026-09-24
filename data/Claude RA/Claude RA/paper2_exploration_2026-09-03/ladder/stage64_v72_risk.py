"""Stage 64: v7.2 risk arithmetic."""
exec(open("stage45_evt2.py").read().split("# expected number of false alarms")[0])
import numpy as np
V7  = {k:v for k,v in adj.items() if "sentiment" not in k}
V71 = {k:v for k,v in V7.items() if k != "bill backstop"}
DOM = {"Sahm backstop","IUR backstop","housing backstop"}
V72 = {k:(v*(1-share) if k in DOM else v) for k,v in V71.items()}
def u(d): return 1-np.prod([1-p for p in d.values()])
print("gate armed in %.0f%% of quiet years; the three dominated backstops keep only the other %.0f%%\n" % (100*share, 100*(1-share)))
print("%-40s %-10s %-16s %-14s %s" % ("rule","union/yr","one every","6.5-yr risk","10-yr risk"))
for lab,d in [("v6 (with sentiment)",adj),("v7 (round 18)",V7),
              ("v7.1 (bill backstop removed)",V71),
              ("v7.2 (+ dominated backstops gate-restricted)",V72)]:
    p=u(d); print("%-40s %-10.4f 1 in %-11.0f %-14.0f%% %.0f%%" % (lab,p,1/p,100*(1-(1-p)**6.5),100*(1-(1-p)**10)))
print("\nv7.2 channel hazards, largest first:")
for k,v in sorted(V72.items(), key=lambda kv:-kv[1]):
    print("   %-22s %.5f/yr%s" % (k, v, ("  1 in %.0f yr" % (1/v)) if v>0 else ""))
print("\ndetection x no-false-alarm over a 6.5-year expansion, v7.2:")
for det,lab in [(0.867,"95%% lower bound, deep recessions (21/21)"),(0.955,"point estimate")]:
    print("   %-42s %.0f%%" % (lab % () if "%%" in lab else lab, 100*det*(1-u(V72))**6.5))
