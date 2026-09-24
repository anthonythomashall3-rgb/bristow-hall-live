"""WALK 57 - THE DOMINANCE CLAUSE AND THE WARN LEG, WALKED TOGETHER (14 September 2026).
Pre-registered in PREREG-v331-ADDENDUM-2026-09-14.md before this was run.

walk56 tried to fix the four calls that are months too early by changing the objective to target minus
seven days. It failed, and the way it failed says what the fix has to look like: the walk traded the
early calls for the late ones, made seven of nine later, and produced the rule's first false alarm. A
scalar objective cannot be trusted to balance early against late, because at an early cut it does not
yet know which calls it is about to spoil.

Three changes, declared in advance.

  A  THE DOMINANCE CLAUSE. A configuration is inadmissible at a cut if it makes any ALREADY-TIMELY
     ratified call later than the configuration carried into that cut made it. Timely means a call
     within a month of the reference month's end - lag at or after minus thirty-one days. Calls that
     are more than a month early are free to move later, because that is the improvement being sought.
     This forbids walk56's failure by construction rather than pricing it.

  B  THE TARGET CLAUSE, as in walk56: the peak side of obj becomes (number more than a month late,
     median |lag + 7|, mean |lag + 7|). On its own it failed; under A it can only move the early calls.

  C  THE WARN LEG, 'N'. A proposer built from state WARN notices - the only labour data in the country
     that is ahead of the event by statute, sixty days' written notice before a mass layoff. Breadth
     across states, every line priced from an expanding window ending before the week read, gated on
     the rule's own Sahm gap at 0.12 so the leg can only ever accelerate a call the core is already
     leaning towards. The window and the percentile are NOT fixed here: they go into the grid and the
     walk chooses them at each cut like every other line. The leg exists only from 2004, when six
     states have enough history to price a breadth line - the evolving menu, which is the point.

Everything else is walk55's, which is walk54's with the search week on three labour terms.

Run:  python3 walk57.py 1962 2026 w57
"""
import sys, pickle, os, csv
SEARCH_TERMS = ['unemp', 'layoffs', 'laidoff']; os.environ['BHS_SEARCH_TERMS'] = ','.join(SEARCH_TERMS)
_MARK = "# ---- the walk " + "itself"

import pandas as pd, numpy as np

# ---- C: the WARN leg's proposals, one list per (window, percentile) in the menu ----
_WP = os.path.expanduser('~/Projects/Onset Detector Data/121_warn_causal_breadth_2026-09-14/out/warn_leg_proposals.csv')
WARN_PROPOSALS = {}
for _r in csv.DictReader(open(_WP)):
    WARN_PROPOSALS.setdefault((int(_r['warnw']), int(_r['warnp'])), []).append(
        (pd.Timestamp(_r['published']), pd.Timestamp(_r['dated'])))
print('WARN leg settings loaded:', {k: len(v) for k, v in sorted(WARN_PROPOSALS.items())}, flush=True)

_hdr = open('walk54.py').read().split(_MARK)[0].replace("walk54_%s.out", "walk57_%s.out")
_old = "        if p.get('kc'): legs['K']=[(a,b) for a,b in leg_K_x(ICfp,p['kc'][0],p['kc'][1])]"
assert _hdr.count(_old) == 1
_hdr = _hdr.replace(_old, _old + "\n"
    "        if p.get('warnw'): legs['N']=list(WARN_PROPOSALS.get((p['warnw'],p['warnp']),[]))")
exec(_hdr)

TARGET = -7
def obj(vw):
    v, w = vw
    a = (sum(1 for x in v if x > 31),
         float(np.median([abs(x - TARGET) for x in v])),
         float(np.mean([abs(x - TARGET) for x in v])))
    if not w: return a + (0, 0.0, 0.0)
    return a + (sum(1 for x in w if x > 31 or x < 0),
                float(np.median([abs(x) for x in w])),
                float(np.mean([abs(x) for x in w])))

# the menu gains the WARN leg's two lines and the wider low; nothing is removed
GRID = [(n, [0.60, 0.55, 0.50, 0.45, 0.35, 0.30, 0.25, 0.20, 0.15]) if n == 'low' else (n, g)
        for n, g in GRID]
GRID = GRID + [('warnw', [26, 13, None]), ('warnp', [95, 90, 85])]
GD = dict(GRID); NAMES = [n for n, _ in GRID]
BASE15 = dict(BASE15); BASE15.update(warnw=None, warnp=90)

# ---- A: the dominance clause ----
TIMELY = -31
_clean_base = clean
def clean(q, cut, ks, kt=()):
    v = _clean_base(q, cut, ks, kt)
    if v is None: return None
    inc = globals().get('last')
    if inc is None: return v
    try:
        si = summary(inc); sq = summary(q)
    except Exception:
        return v
    for j in ks:
        if j in si['lags'] and j in sq['lags']:
            if si['lags'][j] >= TIMELY and sq['lags'][j] > si['lags'][j]:
                return None          # an already-timely call may never be made later
    return v

# ---- the walk itself: walk39's loop, verbatim ----
exec(open('walk39.py').read().split(_MARK)[1].split("\n", 1)[1])
