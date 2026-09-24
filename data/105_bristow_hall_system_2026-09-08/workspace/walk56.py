"""WALK 56 - WALK 55 WITH THE TARGET CLAUSE (14 September 2026). Pre-registered in
PREREG-v330-ADDENDUM-2026-09-14.md before this was run.

The walk chooses its lines each year by minimising obj, whose peak-side terms were (number of calls more
than a month late, median lag, mean lag), with the lag measured in days from the reference month's end
and negative for an early call. Minimising the median lag rewards earliness without bound: a call 155
days before the month ended scored better than one seven days before. That is the mechanical cause of
the four calls at -156, -74, -87 and -155, which between them carry 445 of the record's 774 days of
distance from the target.

Two changes, both declared in advance and neither touching the data, the legs, the confirmers or the
chronology:

  1  the peak side of obj becomes (number more than a month late, median |lag + 7|, mean |lag + 7|), so
     a call 150 days early is penalised as a call 150 days late already was. The first term and the
     whole trough side are unchanged.
  2  the menu for low, the line of the unemployment-gap leg L, is extended upward to
     [0.60, 0.55, 0.50, 0.45, 0.35, 0.30, 0.25, 0.20, 0.15]. Nothing is removed and the order is
     preserved, so the confirmer-versus-proposer tie-break of 8 September is unaffected. Under the old
     objective the walk always ran to the loosest end of this menu because looser fires earlier; under
     the target clause it needs values the menu did not contain.

Everything else is walk55's, which is walk54's with the search week on three labour terms.

Run:  python3 walk56.py 1962 2026 w56
"""
import sys, pickle, os
SEARCH_TERMS = ['unemp', 'layoffs', 'laidoff']; os.environ['BHS_SEARCH_TERMS'] = ','.join(SEARCH_TERMS)
_MARK = "# ---- the walk " + "itself"
exec(open('walk54.py').read().split(_MARK)[0].replace("walk54_%s.out", "walk56_%s.out"))

import numpy as _np
TARGET = -7          # days from the reference month's end; Anthony's stated target throughout

def obj(vw):
    v, w = vw
    a = (sum(1 for x in v if x > 31),
         float(_np.median([abs(x - TARGET) for x in v])),
         float(_np.mean([abs(x - TARGET) for x in v])))
    if not w: return a + (0, 0.0, 0.0)
    return a + (sum(1 for x in w if x > 31 or x < 0),
                float(_np.median([abs(x) for x in w])),
                float(_np.mean([abs(x) for x in w])))

GRID = [(n, [0.60, 0.55, 0.50, 0.45, 0.35, 0.30, 0.25, 0.20, 0.15]) if n == 'low' else (n, g)
        for n, g in GRID]
GD = dict(GRID); NAMES = [n for n, _ in GRID]

# ---- the walk itself: walk39's loop, verbatim ----
exec(open('walk39.py').read().split(_MARK)[1].split("\n", 1)[1])
