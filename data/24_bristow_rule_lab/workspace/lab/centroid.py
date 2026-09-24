"""Where exactly in the plateau: the middle index, or the centre of mass?

'mid' takes the middle month of the within-band run, which ignores how deep each
month is.  The centroid weights each month by how far past the band edge it lies, so
a plateau with one clearly deepest month is dated at that month and a genuinely flat
one at its centre.  Both reduce to the same thing on a symmetric plateau.
"""
import sys; sys.path.insert(0,'/home/claude/lab')
import bench
from bench import *
from w2 import w2
import numpy as np, pandas as pd
bench.SKIP={'exports','imports','car registrations','unemployment','construction production',
            'construction output','capital goods production','intermediate goods production',
            'consumer durables production'}
bench.SKIP_PEAK=set(); bench.SKIP_TROUGH=set(); bench.ABSTAIN=True
K=dict(min_depth=5.0,lam=500000.,band_t=0.12,band_p=0.01,peak_cap=18)
orig=bench._plateau_pick
def make(kind, edge):
    def pick(on, where):
        if len(on)==0: return None
        if where=='last': return on.index[-1]
        if kind=='mid': return on.index[len(on)//2]
        v=on.values.astype(float)
        w=(edge(v)-v) if edge is not None else None
        # trough: deeper = larger weight; peak: higher = larger weight.  Detect by
        # comparing the run's own extreme to its edge.
        lo,hi=v.min(),v.max()
        w = (hi - v) if (v[0]>=v[-1] or True) else None
        return None
    return pick
def pick_centroid(on, where):
    if len(on)==0: return None
    if where=='last': return on.index[-1]
    v=on.values.astype(float)
    # weight by distance from the far edge of the band, whichever side the run sits on
    if abs(v.min()-v[len(v)//2])<=abs(v.max()-v[len(v)//2]):
        w=v.max()-v+1e-12          # a trough plateau: deeper months weigh more
    else:
        w=v-v.min()+1e-12          # a peak plateau: higher months weigh more
    if w.sum()<=0: return on.index[len(on)//2]
    i=int(round(float(np.average(np.arange(len(v)),weights=w))))
    return on.index[min(max(i,0),len(v)-1)]
for tag,fn in (('middle index (shipped)',orig),('centre of mass',pick_centroid)):
    bench._plateau_pick=fn
    tot=[]
    for c in ALL: tot+=run_country_concept(c,**K)
    a,na,b,nb,ma_,mb,sa,sb=w2(tot); s=score(tot,'',show=False)
    print(f'{tag:24s} within2 {a}+{b}={a+b}  hits {s["hp"]}/{s["ht"]}  MAE {ma_:.2f}/{mb:.2f}')
bench._plateau_pick=orig
