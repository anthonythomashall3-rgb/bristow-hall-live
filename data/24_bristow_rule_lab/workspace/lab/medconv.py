import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.)
orig=bench.med
def make(kind):
    def med2(dates,q=0.5):
        ds=sorted(d for d in dates if d is not None)
        if not ds: return None
        n=len(ds)
        if n%2==1: return ds[n//2]
        if kind=='lower': return ds[n//2-1]
        if kind=='upper': return ds[n//2]
        a,b=ds[n//2-1],ds[n//2]
        import pandas as _pd
        mid=a+(b-a)/2
        return _pd.Timestamp(year=mid.year,month=mid.month,day=1) if mid.day<=15 else \
               (_pd.Timestamp(year=mid.year,month=mid.month,day=1)+_pd.DateOffset(months=1))
    return med2
import types
for kind in ('current','lower','upper','mid'):
    bench.med = orig if kind=='current' else make(kind)
    # med is referenced inside med_fallback and date_any via module globals
    tot=[]
    for c in ALL: tot+=run_country_concept(c,**K)
    s=score(tot,'',show=False)
    per=' '.join(f'{c[:4]}{score([r for r in tot if r["country"]==c],"",show=False)["hp"]}/{score([r for r in tot if r["country"]==c],"",show=False)["ht"]}' for c in ALL)
    print(f'{kind:8s} peak {s["hp"]}/80 trough {s["ht"]}/80 | {per}')
bench.med=orig
