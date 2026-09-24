import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.)
r=run_country_concept('Japan',**K)
for x in r:
    f=lambda d: d.strftime('%Y-%m') if d is not None else '--'
    print(f"{x['peak_off']}->{x['tr_off']}  {f(x['pk'])}/{f(x['tr'])} {'P' if x['hp'] else '-'}{'T' if x['ht'] else '-'} nch={x['nch']}")
