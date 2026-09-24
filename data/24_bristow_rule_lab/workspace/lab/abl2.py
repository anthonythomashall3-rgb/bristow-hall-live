import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
BASE={'exports','imports','car registrations','unemployment'}
bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.)
LEVELC=[c for c in ALL if CONCEPT[c]=='level']
bench.SKIP=BASE
tot=[]
for c in LEVELC: tot+=run_country_concept(c,**K)
base=score(tot,'',show=False)
print(f'base: peak {base["hp"]}/{base["n"]}  trough {base["ht"]}/{base["n"]}  sum {base["hp"]+base["ht"]}')
names=sorted({n for c in LEVELC for n,_ in channels(c)} - BASE)
res=[]
for nm in names:
    bench.SKIP=BASE|{nm}
    t=[]
    for c in LEVELC: t+=run_country_concept(c,**K)
    s=score(t,'',show=False); res.append((s['hp']+s['ht']-base['hp']-base['ht'],nm))
for d,nm in sorted(res): print(f'   {d:+3d}  {nm}')
