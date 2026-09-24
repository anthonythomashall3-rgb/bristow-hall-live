import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.)
BASE={'exports','imports','car registrations','unemployment','construction production',
      'construction output','capital goods production','intermediate goods production',
      'consumer durables production'}
for tag,skip in [('with RS',BASE),('without RS in level route',BASE|{'monthly reference GDP'})]:
    tot=[]
    for c in ALL:
        bench.SKIP = BASE if CONCEPT.get(c)=='growth' else skip
        tot+=run_country_concept(c,**K)
    bench.SKIP=BASE
    s=score(tot,'',show=False)
    per=' '.join(f'{c[:4]}{score([r for r in tot if r["country"]==c],"",show=False)["hp"]}/{score([r for r in tot if r["country"]==c],"",show=False)["ht"]}' for c in ALL)
    print(f'{tag:28s} peak {s["hp"]}/80 trough {s["ht"]}/80 | {per}')
