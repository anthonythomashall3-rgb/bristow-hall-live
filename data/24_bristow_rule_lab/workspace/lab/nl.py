import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
bench.SKIP={'exports','imports','car registrations','unemployment'}; bench.ABSTAIN=True
print('smoothing n and lookback L, concept routing, all 80 contractions')
print(f'{"n":>3s} {"L":>3s}   {"peak":>9s} {"trough":>9s}  sum')
best=[]
for n in [1,2,3,4,5]:
    for L in [6,9,12,18,24]:
        tot=[]
        for c in ALL: tot+=run_country_concept(c,min_depth=5.0,lam=500000.,n=n,L=L)
        s=score(tot,'',show=False)
        best.append((s['hp']+s['ht'],n,L,s))
        print(f'{n:3d} {L:3d}   {s["hp"]:4d}/{s["n"]:<4d} {s["ht"]:4d}/{s["n"]:<4d}  {s["hp"]+s["ht"]}')
best.sort(reverse=True)
print('\nbest:', best[0][1:3], best[0][0])
