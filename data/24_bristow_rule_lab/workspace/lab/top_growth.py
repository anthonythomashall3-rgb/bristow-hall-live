"""The flat-top convention on the growth-cycle committees' own objects - the peak side of
floor_growth.py.  Section 14 lists long, shallow contractions where the rule's peak sits deep
inside a flat top (South Africa 1974, +18 months; 1989, +4; Korea 2002, +16).  A committee
that dates the growth-cycle peak as the LAST month of the expansion may be taking the FIRST
month of the plateau, where the rule's plateau reading takes its centre.  On each committee's
own detrended object (South Africa: the Reserve Bank's coincident indicator, ratio to its HP
trend; Taiwan: the Council's published detrended index; Korea, in sample: Statistics Korea's
cyclical component) the peak is the plateau within `beta` of the maximum read at its first,
middle or last month, beta in {0, 0.5, 1, 2, 3 per cent}.  Korea is the in-sample check;
South Africa and Taiwan are held out.  Troughs untouched.  Every setting printed."""
import sys, itertools, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab')
import numpy as np, pandas as pd
import bristow_rule_v3 as B, bench, floor_growth as F
from bench import ts
_orig=B._plateau_pick
def pick(on, where):
    if where=='first': return on.index[0] if len(on) else None
    return _orig(on, where)
B._plateau_pick=pick
def md(a,b): return (a.year-b.year)*12+(a.month-b.month)
def score(obj, chron, smooth, beta, where):
    errs=[]
    for pk,tr in chron:
        pkm=ts(pk); trm=ts(tr); w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
        if obj.index.min()>w0 or obj.index.max()<trm: continue
        t=B.channel_trough(obj,w0,w1,0.0,smooth,12,abstain=False)      # the shipped trough reading, so the peak window is the shipped one
        end=t if t is not None else w1
        p=B.channel_peak(obj,w0,end,beta,smooth,abstain=False,where=where,refine=False)
        errs.append((pk[:7],None if p is None else md(p,pkm)))
    e=[x for _,x in errs if x is not None]
    f=lambda k: sum(abs(x)<=k for x in e)
    return errs, f'n {len(e)} exact {f(0)} w1 {f(1)} w3 {f(3)} mae {np.mean(np.abs(e)):.2f}'
if __name__=='__main__':
    for name,(obj,chron,sm) in F.objects().items():
        print(f'\n=== {name}: peaks on the committee\'s own object, band beta x plateau reading (first / mid / last)')
        for beta,where in itertools.product((0.0,0.005,0.01,0.02,0.03),('first','mid','last')):
            errs,summ=score(obj,chron,sm,beta,where)
            flag=' <- shipped reading (band 0, mid)' if beta==0.0 and where=='mid' else ''
            print(f'  beta {beta:.3f} {where:5s}: {summ}{flag}')
            if beta in (0.01,0.02) and where=='first': print('       ',{k:v for k,v in errs})
