import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
bench.ABSTAIN=True
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set()
LEVELC=[c for c in ALL if CONCEPT[c]=='level']
print('level chronologies only (53 contractions)')
tot=[]
for c in LEVELC: tot+=run_country_concept(c,min_depth=5.0,lam=500000.)
s=score(tot,'   equal weight (shipped)')
for power in [0.5,1.0,2.0]:
    for floor in [0.5,1.0,2.0]:
        tot=[]
        for c in LEVELC: tot+=run_country_learned(c,power=power,floor=floor)
        s2=score(tot,'',show=False)
        print(f'   learned weights power={power} floor={floor}:  peak {s2["hp"]:3d}/{s2["n"]} trough {s2["ht"]:3d}/{s2["n"]}  sum {s2["hp"]+s2["ht"]}')
