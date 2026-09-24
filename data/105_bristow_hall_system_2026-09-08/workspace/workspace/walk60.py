"""WALK 60 - AN OUT-OF-BAND CALL IS COUNTED, AND NOTHING ELSE CHANGES (14 September 2026).
Pre-registered in PREREG-v334-ADDENDUM-2026-09-14.md before this was run.

Walks 56 and 58 both replaced obj's second and third keys with a distance from a target, and both made
most of the record later; walk 58 also produced the rule's first false alarm. The lesson of three runs is
that a distance key makes the walk choose slower proposers, and a slower proposer is slower everywhere.

So the distance keys are left alone. One line changes: the first key of the peak side counts a ratified
call against a configuration when its lag falls outside [-31, +31] days of the peak month's end, on
either side, instead of counting only lags above +31. The second and third keys stay v3.29's median and
mean of the lag itself, so among configurations that are equally in band the walk still prefers the
earlier one and can never buy an in-band call by making a good call later. +31 is v1's late tolerance;
-31 is its mirror, which is the symmetry the trough side has always had.

The menu for 'low' is walk58's widened one - the necessary condition for the walk to reach a line above
0.35 at all. Everything else is walk55's.
Run:  python3 walk60.py 1962 2026 w60"""
import sys, pickle, os
SEARCH_TERMS = ['unemp', 'layoffs', 'laidoff']; os.environ['BHS_SEARCH_TERMS'] = ','.join(SEARCH_TERMS)
_MARK = "# ---- the walk " + "itself"
exec(open('walk54.py').read().split(_MARK)[0].replace("walk54_%s.out", "walk60_%s.out"))
import numpy as _np

EARLY = 31      # the mirror of v1's +31 late tolerance

def obj(vw):
    v, w = vw
    a = (sum(1 for x in v if x > 31 or x < -EARLY), float(_np.median(v)), float(_np.mean(v)))
    if not w: return a + (0, 0.0, 0.0)
    return a + (sum(1 for x in w if x > 31 or x < 0),
                float(_np.median([abs(x) for x in w])), float(_np.mean([abs(x) for x in w])))

GRID = [(n, [0.60, 0.55, 0.50, 0.45, 0.35, 0.30, 0.25, 0.20, 0.15]) if n == 'low' else (n, g) for n, g in GRID]
GD = dict(GRID)

exec(open('walk39.py').read().split(_MARK)[1].split("\n", 1)[1])
