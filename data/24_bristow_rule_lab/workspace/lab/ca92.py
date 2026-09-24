import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
ch=dict(channels('Canada'))
g=ch['monthly GDP']
m=ma(g,3)['1990-03':'1993-05'].dropna()
lo=m.min(); hi=m['1990-03':].max()
print('monthly GDP MA3, 1990-03..1993-05  (low=%.4f at %s)'%(lo,m.idxmin().date()))
amp=hi-lo
for d,v in m.items():
    print(f"  {d.date()}  {v:10.3f}   ({(v-lo)/amp*100:5.1f}% of amp above low)")
