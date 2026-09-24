import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
bench.ABSTAIN=True
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set()
K=dict(lam=500000.)
print(f'{"variant":38s} {"peak":>9s} {"trough":>9s}  sum')
for lab,kw in [('self-selected estimator, bagged',dict(bag=True)),
               ('self-selected estimator, full panel',dict(bag=False)),
               ('concept routing, bagged (level)',dict(bag=True,force='level'))]:
    tot=[]
    for c in ALL: tot+=run_country_self(c,**kw,**K)
    s=score(tot,'',show=False)
    print(f'{lab:38s} {s["hp"]:4d}/{s["n"]:<4d} {s["ht"]:4d}/{s["n"]:<4d}  {s["hp"]+s["ht"]}')
tot=[]
for c in ALL: tot+=run_country_concept(c,min_depth=5.0,lam=500000.)
s=score(tot,'',show=False)
print(f'{"concept routing (shipped)":38s} {s["hp"]:4d}/{s["n"]:<4d} {s["ht"]:4d}/{s["n"]:<4d}  {s["hp"]+s["ht"]}')
