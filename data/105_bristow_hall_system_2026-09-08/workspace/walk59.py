"""WALK 59 - THE SYMMETRIC PEAK SIDE (WALK 58) PLUS THE WARN LEG, ARMED BY THE RULE ITSELF (14 September 2026).
Pre-registered in PREREG-v333-ADDENDUM-2026-09-14.md before this was run.

walk57 put the WARN leg and a dominance clause into the walk together and was refuted; the leg was not the
reason, and the leg's own numbers were the best thing in that run - on the (26 week, 90th percentile) setting
it fires on 18 December 2007, thirteen days before that peak month ends, and on 16 April 2024, fourteen days
before that one. Its defect is elsewhere and it is visible in the proposal list: the leg also fires on
5 January 2010 and 5 January 2021, six and eight months after the troughs of those two recessions. After a
recession the Sahm gap stays above any gate worth setting for a year or more, so the gate cannot tell a new
downturn from the tail of the old one.

The amendment: LEG N IS ARMED BY THE RULE AS IT STANDS WITHOUT IT. The chronology is built once with the core
legs only; a WARN proposal is then refused if it falls while that record is open, or within eighteen months of
the close that ended its last episode; and the chronology is rebuilt with whatever survives. The rule's own
close is a causal mark - it is made from data published by that day - where the NBER trough announcement is
not: the June 2009 trough was not announced until 20 September 2010, months after the January 2010 firing this
clause has to stop.

The objective is walk58's: the peak side made symmetric with the trough side, counting a ratified call against
a configuration when it falls outside [-31, +31] days of the peak month's end on either side, with the second
and third keys measuring distance from a target of -7 days. The menu for 'low' is walk58's widened one.

Run:  python3 walk59.py 1962 2026 w59"""
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

_hdr = open('walk54.py').read().split(_MARK)[0].replace("walk54_%s.out", "walk59_%s.out")
_old = "    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TL)"
assert _hdr.count(_old) == 1
_new = _old + """
    if p.get('warnw'):
        _prop = WARN_PROPOSALS.get((p['warnw'], p['warnp']), [])
        if _prop:
            # The bars: while the record built without leg N is open, and for eighteen months after the
            # close that ended each episode. Built from the record's own published dates, so the bar at
            # any moment uses only calls the rule had already made by then.
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

TARGET = -7      # a week early
EARLY  = 31      # the mirror of v1's +31 late tolerance

def obj(vw):
    v, w = vw
    a = (sum(1 for x in v if x > 31 or x < -EARLY),
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
