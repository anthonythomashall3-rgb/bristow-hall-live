import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
chs=[(nm,s) for nm,s in channels('Spain') if nm not in bench.SKIP]
for _e in [((1974,4),(1975,2)),((1978,3),(1979,2))]:
    pk_off,tr_off,freq=ep3(_e,'Q')
    pkm=q2m(pk_off); trm=q2m(tr_off)
    w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
    use=[(nm,to_quarterly(nm,s)) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm]
    print(f'=== {pk_off}/{tr_off} n={len(use)}  window {w0.date()}..{w1.date()}')
    for nm,s in use:
        p=ch_peak(s,w0,w1,0.01,1,abstain=False); t=ch_trough(s,w0,w1,0.12,1,4,abstain=False)
        print(f'   {nm:26s} peak {p.date() if p is not None else None}  trough {t.date() if t is not None else None}')
        print('      ', '  '.join(f"{d.strftime('%yQ')}{(d.month-1)//3+1}:{v:.1f}" for d,v in s[w0:w1].items()))
