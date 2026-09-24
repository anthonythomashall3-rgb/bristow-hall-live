import sys; sys.path.insert(0,'/home/claude/lab')
import plateau
from plateau import run
from w2 import w2
import bench
from bench import score
res=[]
for wt in ('last','mid'):
  for wp in ('last','mid'):
    for bt in (0.01,0.03,0.05,0.08,0.12):
      for bp in (0.005,0.01,0.02,0.04,0.08):
        tot=run(wt,wp,band_t=bt,band_p=bp)
        a,na,b,nb,ma_,mb,sa,sb=w2(tot)
        s=score(tot,'',show=False)
        res.append((a+b,a,b,s['hp'],s['ht'],ma_,mb,wt,wp,bt,bp))
res.sort(reverse=True)
print(f'{"w2":>4s} {"pk":>3s} {"tr":>3s} {"hP":>3s} {"hT":>3s} {"MAEp":>5s} {"MAEt":>5s}  where_t where_p band_t band_p')
for x in res[:18]:
    print(f'{x[0]:4d} {x[1]:3d} {x[2]:3d} {x[3]:3d} {x[4]:3d} {x[5]:5.2f} {x[6]:5.2f}  {x[7]:6s} {x[8]:6s} {x[9]:5} {x[10]}')
