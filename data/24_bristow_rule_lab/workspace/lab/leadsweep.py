import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_p=0.01,peak_cap=18)
res=[]
for lead in (6,9,12,15,18):
  for tail in (6,9,12,15,18):
    tot=[]
    for c in ALL: tot+=run_country_concept(c,lead=lead,tail=tail,**K)
    s=score(tot,'',show=False)
    res.append((s['hp']+s['ht'],s['hp'],s['ht'],lead,tail))
res.sort(reverse=True)
for x in res[:12]: print('tot=%3d peak=%2d trough=%2d  lead=%2d tail=%2d'%x)
print('shipped lead=12 tail=12:',[r for r in res if r[3:]==(12,12)])
