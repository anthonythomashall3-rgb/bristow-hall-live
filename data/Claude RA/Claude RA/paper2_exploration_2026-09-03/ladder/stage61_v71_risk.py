"""Stage 61: v7.1 risk arithmetic -- the EVT union with the bill backstop removed."""
exec(open("stage45_evt2.py").read().split("# expected number of false alarms")[0])
import numpy as np
V7  = {k:v for k,v in adj.items() if "sentiment" not in k}
V71 = {k:v for k,v in V7.items() if k != "bill backstop"}
def u(d): return 1-np.prod([1-p for p in d.values()])
for lab, d in [("v6 (with sentiment)", adj), ("v7 (sentiment removed)", V7), ("v7.1 (bill backstop also removed)", V71)]:
    pu, pd_ = u(d), max(d.values())
    print("%-36s union %.4f/yr (1 in %2.0f yr) | dependent %.4f (1 in %2.0f) | 6.5-yr risk %.0f%% | 10-yr %.0f%%"
          % (lab, pu, 1/pu, pd_, 1/pd_, 100*(1-(1-pu)**6.5), 100*(1-(1-pu)**10)))
print("\nv7.1 channel hazards, largest first:")
for k,v in sorted(V71.items(), key=lambda kv:-kv[1]):
    print("   %-20s %.5f/yr%s" % (k, v, "  1 in %,.0f yr" % (1/v) if v>0 else ""))
print("\nreduction from removing the bill backstop: %.1f%% of the union hazard" % (100*(1-u(V71)/u(V7))))
