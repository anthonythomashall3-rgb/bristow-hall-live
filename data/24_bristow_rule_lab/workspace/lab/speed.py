"""How fast can a date be published, and what sets the floor?

Three stages are separated:
  publication lag  - the month a series for month t actually appears
  detection lag    - the first month at which the rule's answer exists at all
  settling lag     - the first month after which it stops changing
The provisional date uses clause (a) alone on data through T; the rule is run again
each month as data arrives.
"""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd, numpy as np
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.ABSTAIN=True
NB={'1970-11':None,'1975-03':None,'1980-07':None,'1982-11':None,
    '1991-03':21,'2001-11':20,'2009-06':15,'2020-04':15}
chs=[(nm,s) for nm,s in channels('United States') if nm not in bench.SKIP]
print(f'{"trough":9s} {"first answer":13s} {"lag":>4s}  {"within 2 of truth":18s} {"lag":>4s}  {"settled":9s} {"lag":>4s}')
L1=[];L2=[];L3=[]
prev=None
for pk,tr in US_M:
    if tr<'1969': continue
    w0=ts(pk)-pd.DateOffset(months=12); T0=ts(tr)
    first=None; within=None; final=None
    path=[]
    for k in range(0,37):
        T=T0+pd.DateOffset(months=k)
        a=[]
        for nm,s in chs:
            ss=s[:T]
            if len(ss)<24: continue
            d=dev(ss,12,3)[w0:T].dropna()
            if prev is not None: d=d[d.index>prev]
            if len(d): a.append(d.idxmax())
        p=med(a)
        if p is None: continue
        path.append((T,p))
        if first is None: first=(T,p)
        if within is None and abs(md(p,T0))<=2: within=(T,p)
    if not path: print(f'{tr:9s} no answer'); continue
    end=path[-1][1]; run=0; st=None
    for T,p in path:
        if p==end:
            if st is None: st=T
            run+=1
            if run>=3: break
        else: run=0; st=None
    prev=T0
    f=lambda x: x.strftime('%Y-%m') if x is not None else '--'
    l1=md(first[0],T0)+1; L1.append(l1)
    l2=(md(within[0],T0)+1) if within else None
    if l2 is not None: L2.append(l2)
    l3=md(st,T0)+1 if st is not None else None
    if l3 is not None: L3.append(l3)
    print(f'{tr:9s} {f(first[1]):13s} {l1:4d}  {f(within[1]) if within else "--":18s} {str(l2):>4s}  {f(end):9s} {str(l3):>4s}')
print(f'\nmean: first answer {np.mean(L1):.1f} months; within two months of the truth {np.mean(L2):.1f}; settled {np.mean(L3):.1f}')
