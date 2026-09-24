import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
from w2 import w2
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
res=[]
for wp in ('last','mid'):
  for bp in (0.005,0.01,0.02,0.04,0.08,0.12,0.16):
    for cap in (12,18,24):
      bench.PLATEAU_P=wp
      tot=[]
      for c in ALL: tot+=run_country_concept(c,band_t=0.12,band_p=bp,peak_cap=cap,
                                             n=3,L=12,min_depth=5.0,lam=500000.)
      a,na,b,nb,ma_,mb,sa,sb=w2(tot); s=score(tot,'',show=False)
      res.append((a+b,a,b,s['hp'],s['ht'],ma_,mb,sa,wp,bp,cap))
bench.PLATEAU_P='last'
res.sort(reverse=True)
print(f'{"w2":>4s} {"pk":>3s} {"tr":>3s} {"hP":>3s} {"hT":>3s} {"MAEp":>5s} {"MAEt":>5s} {"biasP":>6s}  where_p band_p cap')
for x in res[:16]:
    print(f'{x[0]:4d} {x[1]:3d} {x[2]:3d} {x[3]:3d} {x[4]:3d} {x[5]:5.2f} {x[6]:5.2f} {x[7]:+6.2f}  {x[8]:5s} {x[9]:6} {x[10]}')
