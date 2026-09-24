import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_p=0.01,peak_cap=18)
LEVEL=[c for c in ALL if CONCEPT[c]=='level']
for tag,cs in [('level chronologies',LEVEL),('all nine chronologies',ALL)]:
    B=[];R=[]
    for c in cs:
        B+=run_country_bb(c); R+=run_country_concept(c,**K)
    # keep only episodes Bry-Boschan reaches
    idx=[i for i,r in enumerate(B) if r['nch']>0 and (r['pk'] is not None or r['tr'] is not None)]
    n=len(idx)
    hb=(sum(B[i]['hp'] for i in idx), sum(B[i]['ht'] for i in idx))
    hr=(sum(R[i]['hp'] for i in idx), sum(R[i]['ht'] for i in idx))
    print(f'{tag}: {n} episodes both rules reach   Bristow {hr[0]}/{n} {hr[1]}/{n}   Bry-Boschan {hb[0]}/{n} {hb[1]}/{n}')
