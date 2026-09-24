import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
for nm,s in channels('Japan'):
    print(f"{nm:36s} {s.index.min().date()} .. {s.index.max().date()} n={len(s.dropna())} {'SKIP' if nm in bench.SKIP else ''}")
