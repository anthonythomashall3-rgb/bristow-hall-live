import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
from w2 import w2
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
res=[]
for bt in (0.0,0.01,0.02,0.03,0.05):
  for bp in (0.0,0.005,0.01,0.02,0.03):
    for cap in (12,18,24):
      for L in (9,12,15):
        tot=[]
        for c in ALL: tot+=run_country_concept(c,n=3,L=L,band_t=bt,band_p=bp,peak_cap=cap,
                                               min_depth=5.0,lam=500000.)
        a,na,b,nb,ma_,mb,sa,sb=w2(tot)
        s=score(tot,'',show=False)
        res.append((a+b,a,b,s['hp'],s['ht'],ma_,mb,sa,sb,bt,bp,cap,L))
res.sort(reverse=True)
print(f'{"w2":>4s} {"pk":>3s} {"tr":>3s} {"hitP":>4s} {"hitT":>4s} {"MAEp":>5s} {"MAEt":>5s} {"bias":>12s}  params')
for x in res[:20]:
    print(f'{x[0]:4d} {x[1]:3d} {x[2]:3d} {x[3]:4d} {x[4]:4d} {x[5]:5.2f} {x[6]:5.2f} {x[7]:+5.2f}/{x[8]:+5.2f}  bt={x[9]} bp={x[10]} cap={x[11]} L={x[12]}')
print('shipped bt=0.03 bp=0.01 cap=18 L=12:',[r for r in res if r[9:]==(0.03,0.01,18,12)])
