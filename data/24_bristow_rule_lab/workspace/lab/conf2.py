import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
tot=[]
for c in ALL: tot+=run_country_concept(c,**K)
rows=[r for r in tot if r.get('sp') is not None or r.get('st') is not None]
def tier(r):
    v=[x for x in (r.get('sp'),r.get('st')) if x is not None]
    if not v: return None
    m=max(v)
    return 'tight' if m<=6 else ('moderate' if m<=20 else 'wide')
import collections
c1=collections.Counter(); c2=collections.Counter()
for r in tot:
    t=tier(r)
    if t is None: continue
    c1[t]+=1; c2[t]+= (1 if (r['hp'] and r['ht']) else 0)
print('spread tier   contractions   both ends right')
for t in ('tight','moderate','wide'):
    if c1[t]: print(f'  {t:9s} {c1[t]:6d}  {c2[t]}/{c1[t]} ({100*c2[t]/c1[t]:.0f}%)')
print('total with a spread:',sum(c1.values()))
