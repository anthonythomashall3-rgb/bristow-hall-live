"""The committee's own emphasis as weights - a routing test with the committee's words as the source.

The NBER's dating-procedure statement says the committee places 'particular emphasis' on real personal
income less transfers and nonfarm payroll employment.  Test (3 September 2026): those two channels vote
twice in the median of channel dates, everything else shipped; also each alone.  Scored exact / within
one / within three against the committee on the twelve postwar contractions.  Output: nber_emphasis_test.log.
Result: worse than the equal median (5 peaks and 7 troughs exact against 6 and 8) - payrolls' jobless
recoveries then carry the median.  Not adopted.
"""
import sys, warnings; warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude'); sys.path.insert(0,'/home/claude/lab'); sys.argv=['x']
import numpy as np, pandas as pd, bristow_rule_v3 as B, bench
from bench import PANELS, channels, ep3, ts, quantity, dating_series, md
bench.SKIP={'exports','imports','car registrations','unemployment','construction production','construction output','capital goods production','intermediate goods production','consumer durables production'}
bench.ABSTAIN=True
c='United States'; cfg=PANELS[c]; chs=[(nm,s) for nm,s in channels(c) if nm not in bench.SKIP]
EMPH={'real income less transfers','payroll employment'}
def date(use,w0,w1,trm,dup):
    u=list(use)+[(nm+' (2)',s) for nm,s in use if nm in dup]
    vol=quantity(c,u) or u
    r=B.date_turning_points(u,w0,w1,volume_channels=vol,concept='level',lam=500000.0,band_trough=0.12,band_peak=0.01,peak_cap=18,smooth=3,lookback=12,dating_series=dating_series(c,w0,trm))
    return r['peak'],r['trough']
rows=[]
for _e in cfg['chrono']:
    pk_off,tr_off,freq=ep3(_e,cfg['freq']); pkm=ts(pk_off); trm=ts(tr_off)
    w0=pkm-pd.DateOffset(months=12); w1=trm+pd.DateOffset(months=12)
    use=[(nm,s) for nm,s in chs if s.index.min()<=w0 and s.index.max()>=trm] or [(nm,s) for nm,s in chs if s.index.min()<=trm and s.index.max()>=trm] or chs
    out={'ep':pk_off[:7]}
    for lab,dup in [('shipped',set()),('income+payrolls x2',EMPH),('payrolls x2',{'payroll employment'}),('income x2',{'real income less transfers'})]:
        p,t=date(use,w0,w1,trm,dup); out[lab]=(md(p,pkm) if p is not None else None, md(t,trm) if t is not None else None)
    rows.append(out)
def stat(errs):
    e=np.array([x for x in errs if x is not None],dtype=float); f=lambda k:int((np.abs(e)<=k).sum())
    return f'{f(0):2d}/{f(1):2d}/{f(3):2d} of {len(errs)} mae {np.abs(e).mean():.2f}'
keys=[k for k in rows[0] if k!='ep']
for k in keys: print(f'{k:20s} peaks {stat([r[k][0] for r in rows])}   troughs {stat([r[k][1] for r in rows])}')
f=lambda x:'  -' if x is None else f'{x:+d}'
print('episode  '+'  '.join(f'{k:>20s}' for k in keys))
for r in rows: print(f"{r['ep']}  "+'  '.join(f"{f(r[k][0]):>9s}/{f(r[k][1]):<9s}" for k in keys))
