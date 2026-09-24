import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd, collections
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.)
chs=[(nm,s) for nm,s in channels('Japan') if nm not in bench.SKIP]
RUNS=[2,3,4,5,6,7]
hits={r:[] for r in RUNS}
for pk_off,tr_off in JP_M:
    w0=ts(pk_off)-pd.DateOffset(months=12); w1=ts(tr_off)+pd.DateOffset(months=12)
    use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=ts(tr_off)]
    if not use: use=[(nm,s) for nm,s in chs if s.index.min()<=ts(tr_off) and s.index.max()>=ts(tr_off)]
    if not use: use=chs
    di=hist_di(use,5); base=date_any('Japan',use,w0,w1,**K)
    tr=None if di is None else ch_trough(di+1.0,w0,w1,0.30,3,12,abstain=False)
    end=tr if tr is not None else w1
    for r in RUNS:
        pk=None if di is None else di_peak_first(di,w0,end,45.0,r)
        if pk is None: pk=base['peak']
        hits[r].append(hit(pk,pk_off,'M')[0])
n=len(JP_M); oos=0; picks=collections.Counter()
for i in range(n):
    best=max(RUNS,key=lambda r: sum(hits[r][j] for j in range(n) if j!=i))
    picks[best]+=1
    oos+=hits[best][i]
print('in-sample by run:', {r:sum(hits[r]) for r in RUNS})
print(f'leave-one-out out-of-sample Japan peaks: {oos}/{n}')
print('run chosen by the other 15:', dict(picks))
