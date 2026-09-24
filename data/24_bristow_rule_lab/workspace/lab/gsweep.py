import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import itertools
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
res=[]
for n in (2,3,4):
 for L in (9,12,15,18):
  for bt in (0.02,0.03,0.05):
   for bp in (0.0,0.01,0.02,0.03,0.05):
    for pc in (6,9,12,18,None):
     tot=[]
     for c in ALL: tot+=run_country_concept(c,n=n,L=L,band_t=bt,band_p=bp,peak_cap=pc,
                                            min_depth=5.0,lam=500000.)
     s=score(tot,'',show=False)
     res.append((s['hp']+s['ht'],s['hp'],s['ht'],n,L,bt,bp,str(pc)))
res.sort(reverse=True)
for x in res[:25]: print('tot=%3d peak=%2d/80 trough=%2d/80  n=%d L=%2d band_t=%.2f band_p=%.2f peak_cap=%s'%x)
print()
print('shipped n=3 L=12 bt=0.03 bp=0.02 pc=12:',[r for r in res if r[3:]==(3,12,0.03,0.02,'12')])
