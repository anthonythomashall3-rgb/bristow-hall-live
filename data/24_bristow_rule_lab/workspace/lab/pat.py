"""Phase Average Trend (Boschan and Ebanks, 1978).

The trend Statistics Korea uses to build the cyclical component of its coincident
composite index, and the trend the OECD used before it moved to Hodrick-Prescott.
It is not a filter with a smoothing constant: the trend is built from the cycle's
own phases, so it cannot cut into a long expansion the way a fixed-lambda filter
can.

  1. divide by a centred 75-month moving average to get a first deviation
  2. find that deviation's turning points with Bry-Boschan
  3. average the ORIGINAL series over each phase, and place the average at the
     phase's midpoint
  4. average each three successive phase means (the 'triplet'), place at the middle
     phase's midpoint
  5. join the triplet points with straight lines, extend at the ends, interpolate
     monthly
  6. smooth with a short centred moving average; the cycle is series / trend * 100
"""
import numpy as np, pandas as pd
from onset import bry_boschan

def _cma(s, w):
    r = s.rolling(w, center=True, min_periods=max(3, w//3)).mean()
    return r

def pat_trend(s, long_ma=75, smooth=12):
    s = s.dropna().astype(float)
    if len(s) < 60: return None
    ls = np.log(s)
    prelim = ls - _cma(ls, long_ma)
    prelim = prelim.dropna()
    if len(prelim) < 40: return None
    tp = bry_boschan(prelim, smooth=3)
    tp = [(d, k) for d, k in tp if d in s.index]
    if len(tp) < 3:
        return pd.Series(_cma(ls, long_ma).ffill().bfill().values, index=ls.index)
    # phase means of the original series
    bounds = [s.index[0]] + [d for d, k in tp] + [s.index[-1]]
    pts = []
    for a, b in zip(bounds[:-1], bounds[1:]):
        seg = ls[a:b]
        if len(seg) < 2: continue
        mid = seg.index[len(seg)//2]
        pts.append((mid, float(seg.mean())))
    if len(pts) < 3:
        return pd.Series(_cma(ls, long_ma).ffill().bfill().values, index=ls.index)
    # triplet means
    trip = []
    for i in range(1, len(pts)-1):
        v = (pts[i-1][1] + pts[i][1] + pts[i+1][1]) / 3.0
        trip.append((pts[i][0], v))
    trip = [pts[0]] + trip + [pts[-1]]
    idx = [t[0] for t in trip]; val = [t[1] for t in trip]
    tr = pd.Series(np.nan, index=ls.index, dtype=float)
    for d, v in zip(idx, val): tr.loc[d] = v
    tr = tr.interpolate(method='index').ffill().bfill()
    tr = _cma(tr, smooth).ffill().bfill()
    return tr

def pat_cycle(s, long_ma=75, smooth=12):
    s = s.dropna().astype(float)
    tr = pat_trend(s, long_ma, smooth)
    if tr is None: return None
    ls = np.log(s)
    tr = tr.reindex(ls.index).ffill().bfill()
    return pd.Series(np.exp(ls.values - tr.values) * 100.0, index=ls.index)
