import sys
sys.argv=['x','1962','2026']
src=open('walk25.py').read().split('BASE15=dict(BASE)')[0].replace("out=open('walk25_%s.out'%sys.argv[1],'w')","out=open('cmpA.out','w')")
exec(src)
P(f"W={W}")
sys.path.insert(0,W+'/lab'); sys.path.insert(0,W)
import bench
from bench import PANELS, channels, ep3, ts, quantity, dating_series, md
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.ABSTAIN=True
chs=[(nm,s) for nm,s in channels('United States') if nm not in bench.SKIP]
P(f"channels: {len(chs)}")
for nm,s in chs: P(f"   {nm}: {s.index.min():%Y-%m} -> {s.index.max():%Y-%m}  n={len(s)}")
out.close()
