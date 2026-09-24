"""Stage 62: the +-1-tick perturbation map re-run for v7.1 (bill backstop removed)."""
exec(open("stage47_perturb.py").read().split('print("\\n=== (c) PERTURBATION')[0])
import numpy as np
def v71_with(bsBill=None, **kw):
    kw.setdefault("bsBill", 1e9)      # a threshold no fall can reach = channel absent
    return v7_with(**kw)
b7  = v7_with();  b71 = v71_with()
print("v7   base: false", b7[1],  "lags", [r["lag"] for r in b7[0]])
print("v7.1 base: false", b71[1], "lags", [r["lag"] for r in b71[0]])
grid=[("Sahm fast 0.35 -> 0.30",dict(sahm=0.30)),("Sahm fast 0.35 -> 0.40",dict(sahm=0.40)),
 ("IUR fast 0.40 -> 0.35",dict(iurg=0.35)),("IUR fast 0.40 -> 0.45",dict(iurg=0.45)),
 ("payrolls 0.10 -> 0.05",dict(payx=0.0005)),("payrolls 0.10 -> 0.15",dict(payx=0.0015)),
 ("housing 20% -> 18%",dict(houx=18)),("housing 20% -> 22%",dict(houx=22)),
 ("bill fast 1.43 -> 1.38",dict(billx=1.38)),("bill fast 1.43 -> 1.48",dict(billx=1.48)),
 ("Sahm backstop 0.55 -> 0.50",dict(bsSahm=0.50)),("Sahm backstop 0.55 -> 0.60",dict(bsSahm=0.60)),
 ("IUR backstop 0.50 -> 0.45",dict(bsIUR=0.45)),("IUR backstop 0.50 -> 0.55",dict(bsIUR=0.55)),
 ("claims backstop 40% -> 35%",dict(bsIC=0.35)),("claims backstop 40% -> 45%",dict(bsIC=0.45)),
 ("housing backstop 25% -> 23%",dict(bsHou=23)),("housing backstop 25% -> 27%",dict(bsHou=27)),
 ("IP backstop 2.0% -> 1.8%",dict(bsIP=0.018)),("IP backstop 2.0% -> 2.2%",dict(bsIP=0.022)),
 ("VIX lane 17.4 -> 16.4",dict(vixx=16.425)),("VIX lane 17.4 -> 18.4",dict(vixx=18.425)),
 ("Baa lane 1.50 -> 1.40",dict(baax=1.40)),("Baa lane 1.50 -> 1.60",dict(baax=1.60))]
BILL7=[("bill backstop 2.50 -> 2.40",dict(bsBill=2.40)),("bill backstop 2.50 -> 2.60",dict(bsBill=2.60))]
def line(lab, fn, kw, base):
    r, f = fn(**kw)
    lags=[x["lag"] for x in r]
    miss=sum(1 for x in r if x["lag"] is None)
    out=[l for l in lags if l is not None and abs(l)>1]
    return "%-30s %-7s %-7d %s" % (lab, ("%d"%len(f)) if f else "0", miss, out)
print("\n=== v7 (as frozen) ===")
print("%-30s %-7s %-7s %s" % ("threshold moved","false","misses","lags outside a month"))
n7=0
for lab,kw in grid+BILL7:
    s=line(lab, v7_with, kw, b7); print(" ", s)
    if s.split()[-3] not in ("0",) : pass
for lab,kw in []: pass
print("\n=== v7.1 (bill backstop removed) ===")
print("%-30s %-7s %-7s %s" % ("threshold moved","false","misses","lags outside a month"))
for lab,kw in grid:
    print(" ", line(lab, v71_with, kw, b71))
