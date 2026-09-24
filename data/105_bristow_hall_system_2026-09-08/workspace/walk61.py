"""WALK 61 - WALK 60'S OBJECTIVE, WITH THE IN-BAND CALLS PROTECTED (14 September 2026).
Pre-registered in PREREG-v335-ADDENDUM-2026-09-14.md before this was run.

Walk 60 opened all nine peaks, produced no false alarm, and cut the nine-peak absolute error against a
-7 target from 386 days to 213, by counting a ratified call against a configuration when its lag falls
outside [-31, +31] on either side rather than only above +31. It failed on one call: 2007, which was
exactly on target at -7, moved to +4.

Here walk 60's objective is kept exactly and one clause is added to clean(): a configuration is
inadmissible at a cut if it makes a ratified call that was ALREADY INSIDE [-31, +31] under the
configuration carried into that cut land later than that configuration made it. Calls outside the band
stay free to move later - that is the improvement being sought, and it is why 1980's move from -63 to
+7 must remain available.

Walk 57 tried a clause of this shape and failed, but walk 57 defined 'already timely' as any lag at or
above -31 with no upper bound, and carried the target keys that walks 56, 58 and 60 have since shown to
be what damages the record. The keys here are v3.29's own.
Run:  python3 walk61.py 1962 2026 w61"""
import sys, pickle, os
SEARCH_TERMS = ['unemp', 'layoffs', 'laidoff']; os.environ['BHS_SEARCH_TERMS'] = ','.join(SEARCH_TERMS)
_MARK = "# ---- the walk " + "itself"
exec(open('walk54.py').read().split(_MARK)[0].replace("walk54_%s.out", "walk61_%s.out"))
import numpy as _np

EARLY = 31      # the mirror of v1's +31 late tolerance
BAND  = 31      # a call inside [-BAND, +BAND] is protected from being made later

def obj(vw):
    v, w = vw
    a = (sum(1 for x in v if x > 31 or x < -EARLY), float(_np.median(v)), float(_np.mean(v)))
    if not w: return a + (0, 0.0, 0.0)
    return a + (sum(1 for x in w if x > 31 or x < 0),
                float(_np.median([abs(x) for x in w])), float(_np.mean([abs(x) for x in w])))

_clean_base = clean
def clean(q, cut, ks, kt=()):
    v = _clean_base(q, cut, ks, kt)
    if v is None: return None
    inc = globals().get('last')          # the configuration carried into this cut
    if inc is None: return v
    si = summary(inc); sq = summary(q)
    for j in ks:
        if j in si['lags'] and j in sq['lags']:
            if -BAND <= si['lags'][j] <= BAND and sq['lags'][j] > si['lags'][j]:
                return None
    return v

GRID = [(n, [0.60, 0.55, 0.50, 0.45, 0.35, 0.30, 0.25, 0.20, 0.15]) if n == 'low' else (n, g) for n, g in GRID]
GD = dict(GRID)

exec(open('walk39.py').read().split(_MARK)[1].split("\n", 1)[1])
