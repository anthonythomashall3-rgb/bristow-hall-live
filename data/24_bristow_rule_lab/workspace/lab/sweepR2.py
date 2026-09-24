import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
bench.SKIP={'exports','imports','car registrations','unemployment'}; bench.ABSTAIN=True
print(f'{"min_depth":>9s} {"lam":>9s}   {"peak":>10s} {"trough":>10s}   {"US":>10s} {"JP":>10s} {"KR":>10s}')
for mdp in [0.5,1.0,2.0,3.0,5.0,8.0]:
  for lam in [129600.,500000.]:
    tot=[]; d={}
    for c in ALL:
        r=run_country_any(c,min_depth=mdp,lam=lam); tot+=r; d[c]=score(r,'',show=False)
    s=score(tot,'',show=False)
    us,jp,kr=d['United States'],d['Japan'],d['Korea']
    print(f'{mdp:9.1f} {lam:9.0f}   {s["hp"]:4d}/{s["n"]:<4d} {s["ht"]:4d}/{s["n"]:<4d}   {us["hp"]:2d}/{us["ht"]:<2d}      {jp["hp"]:2d}/{jp["ht"]:<2d}      {kr["hp"]:2d}/{kr["ht"]:<2d}')
