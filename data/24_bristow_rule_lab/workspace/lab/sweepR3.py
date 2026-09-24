import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
bench.SKIP={'exports','imports','car registrations','unemployment'}; bench.ABSTAIN=True
for mode in ['cycle','level_then_cycle']:
    bench.TROUGH_FROM=mode
    print('trough from:',mode)
    for mdp in [2.0,3.0,5.0,8.0,12.0]:
        tot=[]
        for c in ALL: tot+=run_country_any(c,min_depth=mdp,lam=129600.)
        s=score(tot,'',show=False)
        print(f'   min_depth={mdp:5.1f}  peak {s["hp"]:3d}/{s["n"]}  trough {s["ht"]:3d}/{s["n"]}  sum {s["hp"]+s["ht"]}')
