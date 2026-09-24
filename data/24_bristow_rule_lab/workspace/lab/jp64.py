"""Japan's 1964 peak: where does each object put it?"""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
chs=[(nm,s) for nm,s in channels('Japan') if nm not in bench.SKIP]
for pk_off,tr_off in [('1964-10','1965-10'),('1954-01','1954-11'),('1957-06','1958-06')]:
    pkm=ts(pk_off); trm=ts(tr_off)
    w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
    use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm] or chs
    di=hist_di(use,5)
    tr=ch_trough(di+1.0,w0,w1,0.30,3,12,abstain=False,where='last')
    pk=di_peak_first(di,w0,tr if tr is not None else w1,45.,4)
    print(f'=== {pk_off}/{tr_off}   n={len(use)}  DI peak {pk.date() if pk is not None else None}'
          f'  DI trough {tr.date() if tr is not None else None}')
    d=di[w0:w1].dropna()
    print('   DI: '+'  '.join(f"{x.strftime('%y-%m')}:{v:.0f}" for x,v in d.items()))
    for nm,s in use:
        p=ch_peak(s,w0,tr if tr is not None else w1,0.01,3,abstain=False)
        print(f'     {nm:36s} peak {p.date() if p is not None else None}')
