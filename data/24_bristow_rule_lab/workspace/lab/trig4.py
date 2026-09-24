"""A second trough cannot follow the first by less than a full cycle: Bry and Boschan's
fifteen-month minimum censoring, applied to the real-time call."""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import trigger as T
import pandas as pd, numpy as np
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.ABSTAIN=True
chs=[(nm,s) for nm,s in channels('United States') if nm not in bench.SKIP]
D=T.composite_dev(chs,12,3,2).dropna()['1968':]
TR=[ts(t) for p,t in US_M if t>='1969']
def censored(cs, mc):
    out=[]
    for at,d in cs:
        if out and md(d,out[-1][1])<mc: continue
        out.append((at,d))
    return out
for mc in (0,12,15,18,24):
    cs=censored(T.calls(D,2.0,4,0.5),mc)
    used=set(); matched=[]; extra=0
    for at,d in cs:
        ks=[i for i in range(len(TR)) if abs(md(d,TR[i]))<=6 and i not in used]
        if ks:
            k=min(ks,key=lambda i: abs(md(d,TR[i]))); used.add(k); matched.append((TR[k],at,d))
        else: extra+=1
    lags=[md(at,t) for t,at,d in matched]; errs=[abs(md(d,t)) for t,at,d in matched]
    print(f'min cycle {mc:2d}:  {len(cs)} calls, {len(matched)}/8 matched, {extra} unmatched, '
          f'lag mean {np.mean(lags):+.2f} max {max(lags)}, mean |error| {np.mean(errs):.2f}')
