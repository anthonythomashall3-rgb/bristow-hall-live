import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import trigger as T
import pandas as pd, numpy as np, itertools
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.ABSTAIN=True
chs=[(nm,s) for nm,s in channels('United States') if nm not in bench.SKIP]
D=T.composite_dev(chs,12,3,2).dropna()['1968':]
TR=[ts(t) for p,t in US_M if t>='1969']
res=[]
for thr,j,drop in itertools.product((1.5,2.0,2.5,3.0),(3,4,5,6),(0.0,0.25,0.5,1.0)):
    cs=T.calls(D,thr,j,drop)
    used=set(); matched=[]; extra=0
    for at,d in cs:
        ks=[i for i in range(len(TR)) if abs(md(d,TR[i]))<=6 and i not in used]
        if ks:
            k=min(ks,key=lambda i: abs(md(d,TR[i]))); used.add(k); matched.append((TR[k],at,d))
        else: extra+=1
    if not matched: continue
    lags=[md(at,t) for t,at,d in matched]; errs=[abs(md(d,t)) for t,at,d in matched]
    res.append((len(matched),-extra,-np.mean(errs),thr,j,drop,np.mean(lags),max(lags),np.mean(errs),extra))
res.sort(reverse=True)
for r in res[:14]:
    print(f'thr={r[3]} j={r[4]} drop={r[5]}  found {r[0]}/8  lag mean {r[6]:+.1f} max {r[7]}  |err| {r[8]:.2f}  false calls {r[9]}')
