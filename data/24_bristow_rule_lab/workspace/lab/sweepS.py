import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
bench.SKIP={'exports','imports','car registrations','unemployment'}; bench.ABSTAIN=True
for st in [False,True]:
    bench.STANDARDIZE=st
    for lam in [14400.,129600.,500000.]:
        for mdp in [3.0,5.0,8.0]:
            tot=[];d={}
            for c in ALL:
                r=run_country_any(c,min_depth=mdp,lam=lam); tot+=r; d[c]=score(r,'',show=False)
            s=score(tot,'',show=False)
            print(f'std={str(st):5s} lam={lam:8.0f} mind={mdp:4.1f}  peak {s["hp"]:3d}/80 trough {s["ht"]:3d}/80 sum {s["hp"]+s["ht"]:3d}   JP {d["Japan"]["hp"]:2d}/{d["Japan"]["ht"]:<2d} KR {d["Korea"]["hp"]:2d}/{d["Korea"]["ht"]:<2d} US {d["United States"]["hp"]:2d}/{d["United States"]["ht"]:<2d}')
