"""Can a faster-publishing channel bring the publishable date inside two months?

The final date keeps the coincident panel.  The PROVISIONAL date is allowed a
second panel chosen for publication speed: weekly insured unemployment (published
five days after the week it covers, so a month is complete within a week of month
end) alongside the coincident channels that are out fastest.  The provisional date
must still point to a month strictly before the month whose data is being read, and
publication is charged one further month.
"""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd, numpy as np
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.ABSTAIN=True
FRED='/home/claude/archive/data/fred'
iur=load(f'{FRED}/IURSA.csv').resample('MS').mean()
iur=100.0-iur                     # counter-cyclical -> pro-cyclical
chs=[(nm,s) for nm,s in channels('United States') if nm not in bench.SKIP]
FAST=[('insured unemployment (weekly)',iur)]
NB={'1991-03':21,'2001-11':20,'2009-06':15,'2020-04':15}

def provisional(panel, w0, T0, prev, pub_lag, strict=True):
    for k in range(0,37):
        T=T0+pd.DateOffset(months=k)
        a=[]
        for nm,s in panel:
            ss=s[:T]
            if len(ss)<24: continue
            d=dev(ss,12,3)[w0:T].dropna()
            if prev is not None: d=d[d.index>prev]
            if len(d): a.append(d.idxmax())
        p=med(a)
        if p is not None and (p<T if strict else p<=T):
            return T+pd.DateOffset(months=pub_lag), p
    return None,None

for tag,panel,pub,strict in (('strict: the date must precede the month read',chs,1,True),
                             ('the date may be the month read',chs,1,False),
                             ('the date may be the month read, plus weekly claims',chs+FAST,1,False)):
    lags=[];errs=[];prev=None
    rows=[]
    for pk,tr in US_M:
        if tr<'1969': continue
        w0=ts(pk)-pd.DateOffset(months=12); T0=ts(tr)
        at,d=provisional(panel,w0,T0,prev,pub,strict); prev=T0
        if at is None: rows.append((tr,'--',None,None)); continue
        lag=md(at,T0); err=md(d,T0)
        lags.append(lag); errs.append(abs(err))
        rows.append((tr,d.strftime('%Y-%m'),lag,err))
    print(f'{tag}')
    for r in rows: print(f'    trough {r[0]}  provisional {r[1]}  publishable {r[2]} months after  error {r[3]}')
    print(f'    mean lag {np.mean(lags):.1f}  max {max(lags)}   mean |error| {np.mean(errs):.2f}  within 2: {sum(1 for e in errs if e<=2)}/{len(errs)}')
    print()
