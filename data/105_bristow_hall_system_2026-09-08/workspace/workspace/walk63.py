"""WALK 63 - NEVER LATE, AND A WEEK TO A MONTH EARLY (14 September 2026).
Pre-registered in PREREG-v337-ADDENDUM-2026-09-14.md before this was run.

Anthony's standing instruction of 14 September supersedes the [-31, +31] band of v3.34 to v3.36: every
call must land BEFORE the peak month's end, never on or after it, and the target is seven days to one
month before. A late call is not a worse early call; it is a different and unacceptable kind of thing.

So the peak side of obj becomes four keys: first the number of ratified calls ON OR AFTER the peak
month's end, then the number outside the window of seven days to a month before, then the median and
mean distance from seven days before. Walks 56 and 58 failed because a DISTANCE key sat at the top and
made the walk choose slower proposers; here the distance keys sit under a count of late calls, so a
configuration that makes anything late is worse than every configuration that does not, whatever its
distances. That failure mode is blocked by construction rather than priced.

Everything else is walk62's: clean() untouched, the trough triple v1's, the widened 'low' menu, and
leg N - the WARN notices, armed by the rule as it stands without it.
Run:  python3 walk63.py 1962 2026 w63"""
import sys, pickle, os, csv
SEARCH_TERMS = ['unemp', 'layoffs', 'laidoff']; os.environ['BHS_SEARCH_TERMS'] = ','.join(SEARCH_TERMS)
_MARK = "# ---- the walk " + "itself"
import pandas as pd, numpy as np

_WP = os.path.expanduser('~/Projects/Onset Detector Data/121_warn_causal_breadth_2026-09-14/out/warn_leg_proposals.csv')
WARN_PROPOSALS = {}
for _r in csv.DictReader(open(_WP)):
    WARN_PROPOSALS.setdefault((int(_r['warnw']), int(_r['warnp'])), []).append(
        (pd.Timestamp(_r['published']), pd.Timestamp(_r['dated'])))
print('WARN leg settings loaded:', {k: len(v) for k, v in sorted(WARN_PROPOSALS.items())}, flush=True)

_hdr = open('walk54.py').read().split(_MARK)[0].replace("walk54_%s.out", "walk63_%s.out")
_old = "    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TL)"
assert _hdr.count(_old) == 1
_new = _old + """
    if p.get('warnw'):
        _prop = WARN_PROPOSALS.get((p['warnw'], p['warnp']), [])
        if _prop:
            _bars = []; _op = None
            for _x in turns:
                if _x['kind'] == 'peak' and _op is None:
                    _op = _x['published']
                elif _x['kind'] == 'trough' and _op is not None:
                    _bars.append((_op, _x['published'] + pd.DateOffset(months=18))); _op = None
            if _op is not None:
                _bars.append((_op, pd.Timestamp('2100-01-01')))
            _keep = [(a, b) for a, b in _prop if not any(s <= a <= e for s, e in _bars)]
            if _keep:
                legs['N'] = _keep
                with contextlib.redirect_stdout(io.StringIO()): turns = B.american_chronology(legs, TL)"""
_hdr = _hdr.replace(_old, _new)
exec(_hdr)

TARGET = -7          # a week before the peak month's end
EARLIEST = -31       # a month before; the far edge of the target window

def obj(vw):
    v, w = vw
    a = (sum(1 for x in v if x >= 0),                      # a call on or after the peak month's end
         sum(1 for x in v if x < EARLIEST or x > TARGET),  # a call outside a week-to-a-month before
         float(np.median([abs(x - TARGET) for x in v])),
         float(np.mean([abs(x - TARGET) for x in v])))
    if not w: return a + (0, 0.0, 0.0)
    return a + (sum(1 for x in w if x > 31 or x < 0),
                float(np.median([abs(x) for x in w])), float(np.mean([abs(x) for x in w])))

GRID = [(n, [0.60, 0.55, 0.50, 0.45, 0.35, 0.30, 0.25, 0.20, 0.15]) if n == 'low' else (n, g) for n, g in GRID]
GRID = GRID + [('warnw', [26, 13, None]), ('warnp', [95, 90, 85])]
NAMES = [n for n, _ in GRID]; GD = dict(GRID)
BASE15 = dict(BASE15); BASE15.update(warnw=None, warnp=90)

exec(open('walk39.py').read().split(_MARK)[1].split("\n", 1)[1])
