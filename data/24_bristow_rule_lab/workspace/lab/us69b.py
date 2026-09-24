import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
for c,pk_off,tr_off in [('United States','1969-12','1970-11'),
                        ('United States (interwar)','1920-01','1921-07'),
                        ('United States (interwar)','1929-08','1933-03')]:
    ch=[(nm,s) for nm,s in channels(c) if nm not in bench.SKIP]
    pkm=ts(pk_off); trm=ts(tr_off)
    w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
    use=[(nm,s) for nm,s in ch if s.index.min()<=w0 and s.index.max()>=trm] or ch
    r=date_any(c,use,w0,w1,band_t=.12,band_p=.01,n=3,L=12,peak_cap=18,min_depth=5.,lam=500000.)
    dt_a=[ch_trough(s,w0,w1,.12,3,12,abstain=True) for nm,s in use]
    dt_b=[ch_trough(s,w0,w1,.12,3,12,abstain=False) for nm,s in use]
    l_tr=med_fallback(dt_a,dt_b); end=l_tr if l_tr is not None else w1
    comp=composite_dev(use,12,3,1)[w0:end].dropna(); cross=None
    for d_,v in comp.items():
        if v>=2.0: cross=d_; break
    p0=w0 if cross is None else max(w0,cross-pd.DateOffset(months=18))
    print(f'=== {c} {pk_off}/{tr_off}  answer P={r["peak"].date()} T={r["trough"].date()}  '
          f'verdict={r["verdict"]}  p0={p0.date()} end={end.date()} cross={cross.date() if cross is not None else None}')
    for nm,s in use:
        pa=ch_peak(s,p0,end,.01,3,abstain=True); pb=ch_peak(s,p0,end,.01,3,abstain=False)
        print(f'   {nm:40s} abst={str(pa.date()) if pa is not None else "-":12s} noabst={str(pb.date()) if pb is not None else "-"}')
