import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np, collections
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
tot=[]
for c in ALL: tot+=run_country_concept(c,**K)
# drop the one episode with no data at all
tot=[r for r in tot if not (r['pk'] is None and r['tr'] is None)]
n=len(tot)
ep=[abs(r['ep']) for r in tot if r['ep'] is not None]
et=[abs(r['et']) for r in tot if r['et'] is not None]
print(f'{n} contractions with data (Japan 1951 excluded for want of data)')
print(f'{"error":>8s} {"peaks":>12s} {"troughs":>12s}   (quarterly chronologies in quarters)')
for k in range(0,7):
    a=sum(1 for x in ep if x==k); b=sum(1 for x in et if x==k)
    print(f'{k:8d} {a:5d} ({100*a/len(ep):3.0f}%) {b:5d} ({100*b/len(et):3.0f}%)')
print(f'{">6":>8s} {sum(1 for x in ep if x>6):5d}        {sum(1 for x in et if x>6):5d}')
for lim in (0,1,2,3):
    a=sum(1 for x in ep if x<=lim); b=sum(1 for x in et if x<=lim)
    print(f'within {lim}: peaks {a}/{len(ep)} ({100*a/len(ep):.0f}%)   troughs {b}/{len(et)} ({100*b/len(et):.0f}%)')
print(f'mean |error| peaks {np.mean(ep):.2f}  troughs {np.mean(et):.2f}')
print()
print('the ones outside two:')
for r in tot:
    if (r['ep'] is not None and abs(r['ep'])>2) or (r['et'] is not None and abs(r['et'])>2):
        print(f"   {r['country']:26s} {str(r['peak_off']):12s} peak err {str(r['ep']):>4s}  trough err {str(r['et']):>4s}")
