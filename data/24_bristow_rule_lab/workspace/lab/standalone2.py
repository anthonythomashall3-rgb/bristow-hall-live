import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
LEVEL=[c for c in ALL if CONCEPT[c]=='level']
allr=[]; nx=0; xs=[]; dep_m=[]; dep_x=[]
for c in LEVEL:
    det=standalone(c,thr=1.5,q=0.5,gap=12,band_t=0.03,band_p=0.01)
    det=[d for d in det if d['depth'] is not None and d['depth']<=-2.0]
    rows,extra=match(c,det,window=18); allr+=rows; nx+=len(extra); xs+=[(c,d) for d in extra]
    for r in rows:
        if r['found'] and r.get('depth') is not None: dep_m.append(r['depth'])
    for d in extra:
        if d.get('depth') is not None: dep_x.append(d['depth'])
n=len(allr)
print(f'level chronologies, standalone: episodes found {sum(1 for r in allr if r["found"])}/{n}'
      f'   peak {sum(r["hp"] for r in allr)}/{n}   trough {sum(r["ht"] for r in allr)}/{n}'
      f'   episodes outside the chronology {nx}')
if dep_m and dep_x:
    print(f'   median depth: matched {abs(np.median(dep_m)):.1f}%   extra {abs(np.median(dep_x)):.1f}%')
from collections import Counter
print('   extra by country:', dict(Counter(c for c,_ in xs)))
