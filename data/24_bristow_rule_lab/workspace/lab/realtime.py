"""The real-time record of the provisional call, month by month.

From the official peak onward the rule is re-run each month on data through that
month, and the provisional date - the month the deviation statistic reached its
maximum - is recorded.  A call is made the first month a date exists.  What matters
is not only when the first call comes but how often it later moves, because a fast
rule that keeps changing its mind is not fast.
"""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd, numpy as np
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.ABSTAIN=True
chs=[(nm,s) for nm,s in channels('United States') if nm not in bench.SKIP]
print(f'{"trough":9s} {"1st call":9s} {"lag":>4s} {"err":>4s} {"revisions":>9s} {"final":9s} {"settled lag":>11s}')
L=[];E=[];R=[];S=[]
prev=None
for pk,tr in US_M:
    if tr<'1969': continue
    w0=ts(pk)-pd.DateOffset(months=12); T0=ts(tr); P0=ts(pk)
    calls=[]
    for k in range(0,49):
        T=P0+pd.DateOffset(months=k)
        a=[]
        for nm,s in chs:
            ss=s[:T]
            if len(ss)<24: continue
            d=dev(ss,12,3)[w0:T].dropna()
            if prev is not None: d=d[d.index>prev]
            if len(d): a.append(d.idxmax())
        p=med(a)
        if p is not None: calls.append((T,p))
    prev=T0
    if not calls: print(f'{tr:9s} no call'); continue
    first_T,first_p=calls[0]
    final=calls[-1][1]
    # number of times the call changed
    rev=sum(1 for i in range(1,len(calls)) if calls[i][1]!=calls[i-1][1])
    st=None; run=0
    for T,p in calls:
        if p==final:
            if st is None: st=T
            run+=1
            if run>=3: break
        else: run=0; st=None
    lag=md(first_T,T0)+1; err=md(first_p,T0)
    slag=md(st,T0)+1 if st is not None else None
    L.append(lag); E.append(abs(err)); R.append(rev)
    if slag is not None: S.append(slag)
    f=lambda x: x.strftime('%Y-%m')
    print(f'{tr:9s} {f(first_p):9s} {lag:4d} {err:4d} {rev:9d} {f(final):9s} {str(slag):>11s}')
print(f'\nfirst call: mean lag {np.mean(L):+.1f} months after the trough, mean |error| {np.mean(E):.2f}')
print(f'the call changed {np.mean(R):.1f} times on average; settled {np.mean(S):.1f} months after the trough')
