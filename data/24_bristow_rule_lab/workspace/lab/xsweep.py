import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd, re
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set()
K=dict(band_t=0.03,band_p=0.01,peak_cap=18,n=3,L=12,min_depth=5.0,lam=500000.)
print('--- abstention')
for ab in (True,False):
    bench.ABSTAIN=ab
    tot=[]
    for c in ALL: tot+=run_country_concept(c,**K)
    s=score(tot,'',show=False)
    print(f'   abstain={ab}  peak {s["hp"]}/83 trough {s["ht"]}/83')
bench.ABSTAIN=True
print('--- the 2.0-percent crossing that anchors the peak search')
src=open('/home/claude/lab/bench.py').read()
import importlib
for thr in (1.0,1.5,2.0,3.0,4.0,5.0):
    new=src.replace("        if v>=2.0: cross=d_; break","        if v>=%.1f: cross=d_; break"%thr)
    open('/home/claude/lab/_bt.py','w').write(new)
    import _bt; importlib.reload(_bt)
    _bt.SKIP=bench.SKIP; _bt.SKIP_PEAK=set(); _bt.SKIP_TROUGH=set(); _bt.ABSTAIN=True
    tot=[]
    for c in _bt.ALL: tot+=_bt.run_country_concept(c,**K)
    s=_bt.score(tot,'',show=False)
    print(f'   crossing={thr}  peak {s["hp"]}/83 trough {s["ht"]}/83')
