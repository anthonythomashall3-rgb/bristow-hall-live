"""Stage 73: +-1-tick perturbation map for v8."""
exec(open("stage65_minimal.py").read().split('P0=dict(')[0])
import numpy as np
P8=dict(sahm=0.36,iur=0.40,pay=0.0018,hou=20,bill=1.45,sahmC=0.55,iurC=0.50,houC=25,
        claims=0.40,ip=0.02,vix=22,baa=1.50)
KEEP=["sahm","iur","pay","hou","bill","sahmC","vix"]
print("%-30s %-7s %-7s %s" % ("threshold moved","false","misses","lags outside a month"))
nfa=0; tot=0
for lab,k,v in [("Sahm 0.36 -> 0.34","sahm",0.34),("Sahm 0.36 -> 0.38","sahm",0.38),
  ("IUR 0.40 -> 0.35","iur",0.35),("IUR 0.40 -> 0.45","iur",0.45),
  ("payrolls 0.18 -> 0.13","pay",0.0013),("payrolls 0.18 -> 0.23","pay",0.0023),
  ("housing 20% -> 18%","hou",18),("housing 20% -> 22%","hou",22),
  ("bill 1.45 -> 1.40","bill",1.40),("bill 1.45 -> 1.50","bill",1.50),
  ("Sahm clause 0.55 -> 0.50","sahmC",0.50),("Sahm clause 0.55 -> 0.60","sahmC",0.60),
  ("VIX lane 22 -> 20","vix",20),("VIX lane 22 -> 24","vix",24)]:
    p=dict(P8); p[k]=v
    o,l,f,n,_=run(p,KEEP); tot+=1
    miss=sum(1 for x in l if x is None); out=[x for x in l if x is not None and abs(x)>1]
    if f: nfa+=1
    print("%-30s %-7s %-7d %s%s" % (lab, len(f) if f else "0", miss, out, "" if n==9 else "  [no-inv %d/9]"%n))
print("\n%d of %d one-tick moves create a false alarm" % (nfa,tot))
