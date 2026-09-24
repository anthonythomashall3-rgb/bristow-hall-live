"""Does clause (a) still earn its place at the trough?

The trough is the LATER of (a) the month the deviation statistic peaks and (b) the
plateau clause.  With (b) reading the centre of the plateau rather than its end, the
'later of' may be doing the biasing that moving to the centre was meant to remove.
"""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
from w2 import w2
import pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
src=open('/home/claude/lab/bench.py').read()
import importlib
VAR={'later of (a) and (b) - shipped':"    return max(d_peak,p) if p is not None else d_peak",
     '(b) alone':"    return p if p is not None else d_peak",
     'midpoint of (a) and (b)':"    return (p if p is None else (min(d_peak,p)+(max(d_peak,p)-min(d_peak,p))/2).to_period('M').to_timestamp()) if p is not None else d_peak",
     'earlier of (a) and (b)':"    return min(d_peak,p) if p is not None else d_peak"}
for tag,repl in VAR.items():
    new=src.replace("    return max(d_peak,p) if p is not None else d_peak",repl,1)
    open('/home/claude/lab/_ca.py','w').write(new)
    import _ca; importlib.reload(_ca)
    _ca.SKIP=bench.SKIP; _ca.SKIP_PEAK=set(); _ca.SKIP_TROUGH=set(); _ca.ABSTAIN=True
    tot=[]
    for c in _ca.ALL: tot+=_ca.run_country_concept(c,**K)
    a,na,b,nb,ma_,mb,sa,sb=w2(tot); s=_ca.score(tot,'',show=False)
    print(f'{tag:32s} within2 {a}+{b}={a+b}  hits {s["hp"]}/{s["ht"]}  MAE {ma_:.2f}/{mb:.2f}  bias {sa:+.2f}/{sb:+.2f}')
