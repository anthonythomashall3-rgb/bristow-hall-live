"""A second, faster channel: the Treasury's daily withheld income and FICA taxes.

The Daily Treasury Statement publishes the previous business day's federal tax deposits, so
a month's total is complete on the first business day of the following month - a shorter
lag than any claims report.  Withheld individual and FICA taxes are a payroll flow, which
is the concept the NBER's peak rests on, and the series needs no registered key.

The object is a growth cycle, so the rule's growth clauses apply: the peak is the maximum
of the smoothed year-over-year rate and the trough its minimum.  In real time the detector
fires when the rate has fallen `drop` points from its running maximum and has been falling
for `run` months, and dates the peak at that maximum; the trough is the mirror.
"""
import pandas as pd, numpy as np, itertools, warnings; warnings.filterwarnings('ignore')
s=pd.read_csv('/home/claude/lab/weekly/US_daily_withheld_taxes.csv',parse_dates=['d']).set_index('d')['value']
m=s.resample('MS').sum(); m=m[m>0]
PK={'2007-12':'NBER','2020-02':'NBER','2023-06':'Paper 1','2024-03':'Paper 1'}
TR={'2009-06':'NBER','2020-04':'NBER','2024-08':'Paper 1','2026-05':'Paper 1'}
def mn(i): return np.array([t.year*12+t.month for t in i],dtype=np.int64)
def lab(x): return f'{(x-1)//12:04d}-{((x-1)%12)+1:02d}'
def calls(g,drop,run,cens,up=True,pub=1):
    v=g.values if up else -g.values; idx=mn(g.index); n=len(v)
    out=[]; ext=-1e9; ei=0; fall=0; prev=v[0]; last=None
    for i in range(1,n):
        if not np.isfinite(v[i]): continue
        if v[i]>ext: ext=v[i]; ei=i; fall=0
        elif v[i]<prev: fall+=1
        else: fall=0
        prev=v[i]
        if fall>=run and (ext-v[i])>=drop:
            p=idx[i]+pub
            if last is None or p-last>=cens:
                out.append((p,idx[ei])); last=p; ext=v[i]; ei=i; fall=0
    return out
def score(c,T):
    TT={k:pd.Timestamp(k+'-01').year*12+pd.Timestamp(k+'-01').month for k in T}
    hits={}; oth=0
    for p,d in c:
        k=min(TT,key=lambda x:abs(d-TT[x]))
        if abs(p-TT[k])<=2 and abs(d-TT[k])<=2 and k not in hits: hits[k]=(p-TT[k],d-TT[k])
        else: oth+=1
    return hits,oth
best={}
for sm in (1,2,3,4,6,9,12):
    g=((np.log(m)-np.log(m.shift(12)))*100).rolling(sm).mean().dropna()
    for drop in (1.,2.,3.,4.,5.,6.,8.,10.):
        for run in (1,2,3):
            for cens in (12,15,18,24):
                for tag,T,up in [('P',PK,True),('T',TR,False)]:
                    h,o=score(calls(g,drop,run,cens,up),T)
                    key=(tag,len(h),o)
                    if key not in best: best[key]=(sm,drop,run,cens,{k:v for k,v in h.items()})
for tag,T in [('P',PK),('T',TR)]:
    print(f'=== {"PEAKS" if tag=="P" else "TROUGHS"} on the Treasury payroll-tax growth rate')
    ks=[k for k in best if k[0]==tag]
    for k in sorted(ks,key=lambda x:(-x[1],x[2]))[:6]:
        sm,drop,run,cens,h=best[k]
        print(f'  {k[1]}/{len(T)} hits, {k[2]} other   sm={sm} drop={drop} run={run} cens={cens}')
        for kk,vv in h.items(): print(f'        {kk}  lag {vv[0]:+d}  error {vv[1]:+d}')
print()
g=((np.log(m)-np.log(m.shift(12)))*100).rolling(6).mean().dropna()
print('the shipped-style setting, sm=6 drop=3 run=2 cens=15:')
for p,d in calls(g,3.,2,15,True): print(f'   PEAK   published {lab(p)}  dated {lab(d)}')
for p,d in calls(g,3.,2,15,False): print(f'   TROUGH published {lab(p)}  dated {lab(d)}')
