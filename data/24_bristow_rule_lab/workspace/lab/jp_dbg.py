import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.ABSTAIN=True
chs=[(nm,s) for nm,s in channels('Japan') if nm not in bench.SKIP]
for pk_off,tr_off in [('1957-06','1958-06'),('1964-10','1965-10'),('1970-07','1971-12'),('1980-02','1983-02')]:
    w0=ts(pk_off)-pd.DateOffset(months=12); w1=ts(tr_off)+pd.DateOffset(months=12)
    use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=ts(tr_off)]
    if not use: use=[(nm,s) for nm,s in chs if s.index.min()<=ts(tr_off) and s.index.max()>=ts(tr_off)]
    if not use: use=chs
    di=hist_di(use,5)
    tr=ch_trough(di+1.0,w0,w1,0.30,3,12,abstain=False)
    end=tr if tr is not None else w1
    a=di_peak_first(di,w0,end,45.0,5)
    b=di_dates_censored(di,w0,end,45.0,1,1)['peak']
    d=date_diffusion_panel(use,w0,w1)
    f=lambda x: x.strftime('%Y-%m') if x is not None else '--'
    print(f"{pk_off}  nch={len(use)}  first-fall={f(a)}  last-touch={f(b)}  panelfn={f(d['peak'])}  trough={f(tr)}")
    seg=di[w0:end].dropna()
    print('   DI:', ' '.join(f'{i:%y-%m}:{v:.0f}' for i,v in list(seg.items())[:36]))
