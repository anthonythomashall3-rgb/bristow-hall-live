"""The C.D. Howe Council's own statement about employment, applied literally.

"Before 1980, employment was often less sensitive to declines in output; after 1980,
employment moves more closely with the business cycle."  So employment joins the
dating evidence for episodes from 1980 and not before.  The Canadian record makes
the case concretely: in the 1990-92 recession monthly GDP - the Council's own dating
series - bottomed in March 1991, employment in October 1992, and the Council put the
trough at May 1992, between the two and much nearer employment.
"""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
ch=dict(channels('Canada'))
gdp=ch['monthly GDP']; ip=ch['industrial production']; emp=ch['employment']
base=run_country_concept('Canada',**K)
for tag,cut in (('GDP only (shipped)',None),('employment joins from 1980',1980),
                ('employment joins from 1975',1975),('employment always',0)):
    hp=ht=0; det=[]
    for i,(pk_off,tr_off) in enumerate(CA_M):
        pkm=ts(pk_off); trm=ts(tr_off)
        w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        use=[gdp] if (gdp.index.min()<=w0 and gdp.index.max()>=trm) else [ip]
        u2=list(use)
        if cut is not None and pkm.year>=cut and emp.index.min()<=w0 and emp.index.max()>=trm:
            u2=use+[emp]
        tr=med([ch_trough(s,w0,w1,0.12,3,12,abstain=False) for s in u2])
        pk=med([ch_peak(s,w0,tr if tr is not None else w1,0.01,3,abstain=False) for s in u2])
        a,ep=hit(pk,pk_off,'M'); b,et=hit(tr,tr_off,'M'); hp+=a; ht+=b
        f2=lambda x: ('%+d'%x) if x is not None else ' --'
        det.append(f"   {pk_off}->{tr_off}  {f2(ep):>4s}/{f2(et):<4s} {'P' if a else '-'}{'T' if b else '-'}")
    print(f'{tag}: peak {hp}/12 trough {ht}/12')
    for d in det: print(d)
