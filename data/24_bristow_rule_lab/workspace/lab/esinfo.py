import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
for c in ('Spain','Euro area'):
    print('===',c)
    for nm,s in channels(c):
        print(f"   {nm:34s} {s.index.min().date()} .. {s.index.max().date()} n={len(s.dropna())} {'SKIP' if nm in bench.SKIP else ''}")
