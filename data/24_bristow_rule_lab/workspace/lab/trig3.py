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
print('official NBER troughs from 1969:', [t.strftime('%Y-%m') for t in TR])
cs=T.calls(D,2.0,4,0.5)
print(f'{len(cs)} calls in all:')
for at,d in cs:
    near=min(TR,key=lambda t: abs(md(d,t)))
    print(f'   published {at:%Y-%m}   dated the trough {d:%Y-%m}   nearest official trough '
          f'{near:%Y-%m} ({md(d,near):+d} months)')
