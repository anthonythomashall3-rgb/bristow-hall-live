import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.ABSTAIN=True
chs=[(nm,s) for nm,s in channels('United States') if nm not in bench.SKIP]
for pk_off,tr_off in [('1969-12','1970-11'),('1920-01','1921-07'),('1929-08','1933-03')]:
    c='United States (interwar)' if pk_off[:2]=='19' and int(pk_off[:4])<1940 else 'United States'
    ch=[(nm,s) for nm,s in channels(c) if nm not in bench.SKIP]
    pkm=ts(pk_off); trm=ts(tr_off)
    w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
    use=[(nm,s) for nm,s in ch if s.index.min()<=w0 and s.index.max()>=trm]
    print(f'=== {c} {pk_off}/{tr_off}  n={len(use)}')
    for nm,s in use:
        p=ch_peak(s,w0,w1,0.01,3,abstain=True); t=ch_trough(s,w0,w1,0.12,3,12,abstain=True)
        print(f'   {nm:36s} peak {str(p.date()) if p is not None else "abstain":12s} trough {str(t.date()) if t is not None else "abstain"}')
