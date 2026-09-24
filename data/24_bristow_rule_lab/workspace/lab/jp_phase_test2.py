import sys; sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab')
import bench, itertools
from bench import *
bench.SKIP={'exports','imports','car registrations','unemployment','construction production','construction output','capital goods production','intermediate goods production','consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
def score(tag):
    bench._PH.clear()
    r=run_country_concept('Japan',**K)
    ep=[x['ep'] for x in r if x['ep'] is not None]; et=[x['et'] for x in r if x['et'] is not None]
    g=lambda e,t: sum(abs(x)<=t for x in e)
    print(f"{tag:30s} peaks {g(ep,0):2d}/{g(ep,1):2d}/{g(ep,3):2d} of {len(ep)} bias {sum(ep)/len(ep):+.2f} | troughs {g(et,0):2d}/{g(et,1):2d}/{g(et,3):2d} of {len(et)} bias {sum(et)/len(et):+.2f}  P {ep} T {et}",flush=True)
for bb,conv in itertools.product(('tool','std'),('tool','esri')):
    bench.DI_BB=bb; bench.PHASE_CONV=conv; bench.PHASE_REFINE=0
    score(f'bb={bb} conv={conv}')
