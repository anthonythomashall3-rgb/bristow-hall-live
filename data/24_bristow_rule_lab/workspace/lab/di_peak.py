import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
import pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.)

def di_peak_first(di,w0,w1,line,run):
    """First month after which the index stays below the line for at least `run`
    months: the start of the first sustained fall, not the last touch above it."""
    d=di[w0:w1].dropna()
    if len(d)<run+2: return None
    v=(d>=line).values; idx=d.index
    for i in range(len(v)-1):
        if v[i] and not v[i+1]:
            j=i+1; c=0
            while j<len(v) and not v[j]: c+=1; j+=1
            if c>=run: return idx[i]
    return None

chs=[(nm,s) for nm,s in channels('Japan') if nm not in bench.SKIP]
print(f'{"line":>5s} {"run":>4s}  last-touch  first-fall')
for line in (40.,45.,50.,55.):
  for run in (1,2,3,5,7,9,12):
    hpA=hpB=0
    for pk_off,tr_off in JP_M:
        w0=ts(pk_off)-pd.DateOffset(months=12); w1=ts(tr_off)+pd.DateOffset(months=12)
        use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=ts(tr_off)] or chs
        di=hist_di(use,5)
        if di is None: continue
        tr=ch_trough(di+1.0,w0,w1,0.30,3,12,abstain=False)
        end=tr if tr is not None else w1
        a=di_dates_censored(di,w0,end,line,run,1)['peak']
        b=di_peak_first(di,w0,end,line,run)
        base=date_any('Japan',use,w0,w1,**K)
        a=a if a is not None else base['peak']; b=b if b is not None else base['peak']
        hpA+=hit(a,pk_off,'M')[0]; hpB+=hit(b,pk_off,'M')[0]
    print(f'{line:5.0f} {run:4d}      {hpA:2d}/16       {hpB:2d}/16')
