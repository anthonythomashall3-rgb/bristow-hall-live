exec(open('minimise.py').read().split('print("PEAK-LEG SUBSETS')[0])
import itertools, numpy as np
PKEYS=list(PL.keys()); TKEYS=[k for k in TLG.keys()]
CAND=[]
for n in (2,3):
    for c in itertools.combinations(PKEYS,n): CAND.append(('P',c))
POOL=[]
for pn in (2,3):
    for pc in itertools.combinations(PKEYS,pn):
        for tn in (3,4):
            for tc in itertools.combinations(TKEYS,tn):
                POOL.append((pc,tc))
print("candidate (peak,trough) subsets:",len(POOL))
CACHE={}
def ev(pc,tc):
    k=(pc,tc)
    if k in CACHE: return CACHE[k]
    try:
        r=run({x:PL[x] for x in pc},{x:TLG[x] for x in tc})
        v=(r['lags_p'],r['errs_p'],r['lags_t'],r['errs_t'],r['other']) if len(r['lags_p'])==len(PK) and len(r['lags_t'])==len(TR) else None
    except Exception: v=None
    CACHE[k]=v; return v
print("evaluating ...")
ok=[(pc,tc) for pc,tc in POOL if ev(pc,tc) is not None and ev(pc,tc)[4]<=1]
print("complete subsets:",len(ok))
print("\nLEAVE-ONE-RECESSION-OUT  (subset re-picked on the other eleven; held-out peak scored)")
print(f"  {'held out':10} {'chosen peak/trough legs':26} {'held lag(d)':>11} {'held err':>9}")
from collections import Counter
picks=Counter()
for i in range(len(PK)):
    best=None
    for pc,tc in ok:
        lp,ep,lt,et,oth=ev(pc,tc)
        L=[v for j,v in enumerate(lp) if j!=i]; E=[abs(v) for j,v in enumerate(ep) if j!=i]
        key=(np.median(L),np.mean(E),len(pc)+len(tc))
        if best is None or key<best[0]: best=(key,(pc,tc))
    pc,tc=best[1]; lp,ep,_,_,_=ev(pc,tc)
    picks[(''.join(pc),''.join(tc))]+=1
    print(f"  {PK[i]:%Y-%m}   {''.join(pc)+' / '+''.join(tc):26} {lp[i]:>11} {ep[i]:>+9}")
print("\n  configurations chosen across the twelve folds:")
for k,v in picks.most_common(): print(f"    {k[0]} / {k[1]}   chosen in {v} of 12 folds")
