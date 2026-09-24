import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
res=[]
for bt in (0.0,0.005,0.01,0.02,0.03,0.04,0.05,0.07):
  for L in (9,12,15,18,24):
    for n in (2,3,4):
      tot=[]
      for c in ALL: tot+=run_country_concept(c,n=n,L=L,band_t=bt,band_p=0.01,peak_cap=18,
                                             min_depth=5.0,lam=500000.)
      s=score(tot,'',show=False)
      res.append((s['hp']+s['ht'],s['hp'],s['ht'],bt,L,n))
      print('.',end='',flush=True)
print()
res.sort(reverse=True)
for x in res[:20]: print('tot=%3d peak=%2d trough=%2d  band_t=%.3f L=%2d n=%d'%x)
print('current bt=0.03 L=12 n=3:',[r for r in res if r[3:]==(0.03,12,3)])
