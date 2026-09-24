"""WALK 62 - WALK 60'S OBJECTIVE AND THE WARN LEG, ARMED BY THE RULE ITSELF (14 September 2026).
Pre-registered in PREREG-v336-ADDENDUM-2026-09-14.md before this was run.

Walk 60 opened all nine peaks with no false alarm and cut the nine-peak absolute error against a -7
target from 386 days to 213, at the cost of moving 2007 from -7 to +4. Walk 61 showed that no causal
clause can prevent that cost: the 2007 call is made on 4 January 2008, and the 2007 peak was not
announced until 1 December 2008, so at the moment of the call there is no ratified 2007 lag to protect.

The only thing that can restore 2007 is evidence the rule does not yet read. The WARN breadth of
collection 121 fires on 18 December 2007, thirteen days before that peak month ends, and on 16 April
2024, fourteen days before that one.

So: walk 60's objective, unchanged, plus leg N. The leg is ARMED BY THE RULE AS IT STANDS WITHOUT IT -
the chronology is built once from the core legs, a WARN proposal is refused while that record is open
or within eighteen months of the close that ended its last episode, and the chronology is rebuilt with
what survives. That is what stops the 5 January 2010 and 5 January 2021 firings, which the Sahm gate
cannot stop because after a recession the gap stays above any gate worth setting for a year or more.
Run:  python3 walk62.py 1962 2026 w62"""
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

_hdr = open('walk54.py').read().split(_MARK)[0].replace("walk54_%s.out", "walk62_%s.out")
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

EARLY = 31

def obj(vw):
    v, w = vw
    a = (sum(1 for x in v if x > 31 or x < -EARLY), float(np.median(v)), float(np.mean(v)))
    if not w: return a + (0, 0.0, 0.0)
    return a + (sum(1 for x in w if x > 31 or x < 0),
                float(np.median([abs(x) for x in w])), float(np.mean([abs(x) for x in w])))

GRID = [(n, [0.60, 0.55, 0.50, 0.45, 0.35, 0.30, 0.25, 0.20, 0.15]) if n == 'low' else (n, g) for n, g in GRID]
GRID = GRID + [('warnw', [26, 13, None]), ('warnp', [95, 90, 85])]
NAMES = [n for n, _ in GRID]; GD = dict(GRID)
BASE15 = dict(BASE15); BASE15.update(warnw=None, warnp=90)

exec(open('walk39.py').read().split(_MARK)[1].split("\n", 1)[1])
