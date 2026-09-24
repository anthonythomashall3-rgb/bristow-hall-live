"""HELD OUT: the South African Reserve Bank's own reference chronology, dated at the
frozen shipped configuration.  Nothing about South Africa entered any choice made in
building the rule.  The SARB states its concept itself: it "identifies reference turning
points in the business cycle according to the growth cycle definition, which entails
identifying turning points in the fluctuations around the long-term trend of aggregate
economic activity" (Quarterly Bulletin, September 2025).  So it is routed to the growth
branch, exactly as Statistics Korea is.

Chronology from the SARB Quarterly Bulletin statistical tables, "Business cycles in
South Africa": the peak is the last month of an upward phase, the trough the last month
of a downward phase.
"""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import numpy as np, pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
ZA=[('1946-07','1947-04'),('1948-11','1950-02'),('1951-12','1953-03'),('1955-04','1956-09'),
    ('1958-01','1959-03'),('1960-04','1961-08'),('1965-04','1965-12'),('1967-05','1967-12'),
    ('1970-12','1972-08'),('1974-08','1977-12'),('1981-08','1983-03'),('1984-06','1986-03'),
    ('1989-02','1993-05'),('1996-11','1999-08'),('2007-11','2009-08'),('2013-11','2017-04'),
    ('2019-06','2020-04')]
ref=load('/home/claude/lab/kei/ZAF_RS__T.csv')
retail=load('/home/claude/lab/kei/ZAF_TOVM_G47.csv')
mfg=load('/home/claude/lab/kei/ZAF_PRVM_C.csv')
print('reference series', ref.index.min().date(), ref.index.max().date())
hp=ht=0; ep=[]; et=[]; n=0
print(f'{"peak":9s} {"trough":9s}  {"rule peak":10s} {"err":>4s}  {"rule trough":11s} {"err":>4s}')
for pk_off,tr_off in ZA:
    pkm=ts(pk_off); trm=ts(tr_off)
    w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
    if ref.index.min()>w0 or ref.index.max()<trm:
        print(f'{pk_off:9s} {tr_off:9s}   no data'); continue
    n+=1
    tr=ch_trough(ref,w0,w1,0.0,3,12,abstain=False)
    pk=ch_peak(ref,w0,tr if tr is not None else w1,0.0,3,abstain=False)
    a,e1=hit(pk,pk_off,'M'); b,e2=hit(tr,tr_off,'M')
    hp+=a; ht+=b
    if e1 is not None: ep.append(abs(e1))
    if e2 is not None: et.append(abs(e2))
    f=lambda d: d.strftime('%Y-%m') if d is not None else '  --   '
    g=lambda e: f'{e:+4d}' if e is not None else '  --'
    print(f'{pk_off:9s} {tr_off:9s}  {f(pk)}    {g(e1)}  {f(tr)}       {g(e2)}')
print()
print(f'HELD OUT, {n} contractions: peaks {hp}/{n} troughs {ht}/{n}   '
      f'mean |error| {np.mean(ep):.2f} / {np.mean(et):.2f} months')
print(f'   within two months: peaks {sum(1 for x in ep if x<=2)}/{n}  troughs {sum(1 for x in et if x<=2)}/{n}')
print(f'   exact: peaks {sum(1 for x in ep if x==0)}/{n}  troughs {sum(1 for x in et if x==0)}/{n}')
