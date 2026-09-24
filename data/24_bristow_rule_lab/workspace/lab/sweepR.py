import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
bench.SKIP={'exports','imports','car registrations','unemployment'}; bench.ABSTAIN=True
print(f'{"min_depth":>9s} {"lam":>9s}   {"peak":>10s} {"trough":>10s}   {"US peak":>8s} {"US tr":>6s}')
for mdp in [0.0,0.5,1.0,1.5,2.0,3.0]:
  for lam in [129600.,500000.,1600000.]:
    tot=[]; us=None
    for c in ALL:
        r=run_country_any(c,min_depth=mdp,lam=lam); tot+=r
        if c=='United States': us=score(r,'',show=False)
    s=score(tot,'',show=False)
    print(f'{mdp:9.1f} {lam:9.0f}   {s["hp"]:4d}/{s["n"]:<4d} {s["ht"]:4d}/{s["n"]:<4d}   {us["hp"]:4d}/12  {us["ht"]:3d}/12')
