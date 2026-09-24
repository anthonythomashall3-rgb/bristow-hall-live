"""WALK 65 - WALK 64'S OBJECTIVE, LEG N, AND LEG S: STATE BREADTH ON A PANEL THAT REACHES 1948.
Pre-registered in PREREG-v339-ADDENDUM-2026-09-14.md before this was run.

leg_probe.py showed that BR - the lab's state breadth - spans only 1984-06 to 2026-08, so leg B is 'na'
at 1969, 1973, 1980 and 1981 at every line, and the rule leans on leg L there, whose loose lines propose
at -132, -160 and -174 days. Collection 139 builds the weekly state insured-rate panel back to January
1948 from the Department's own rate - reconstructed 1948-78, printed 1980-83, ETA 539 from 1984 - and
leg S is that panel priced exactly as leg N is priced: a state lit against the percentile of its own
prior quiet changes, breadth against the percentile of its own prior quiet breadth, everything expanding
and shifted, the nine-day publication lag charged, and the rule's own Sahm gap as the gate.

Both legs N and S are ARMED BY THE RULE AS IT STANDS WITHOUT THEM: the chronology is built from the core
legs, a proposal is refused while that record is open or within eighteen months of the close that ended
its last episode, and the chronology is rebuilt with what survives.

The setting menu is fixed in the pre-registration and ordered safest first by firing count.
Run:  python3 walk65.py 1962 2026 w65"""
import sys, pickle, os, csv
SEARCH_TERMS = ['unemp', 'layoffs', 'laidoff']; os.environ['BHS_SEARCH_TERMS'] = ','.join(SEARCH_TERMS)
_MARK = "# ---- the walk " + "itself"
import pandas as pd, numpy as np

_WP = os.path.expanduser('~/Projects/Onset Detector Data/121_warn_causal_breadth_2026-09-14/out/warn_leg_proposals.csv')
WARN_PROPOSALS = {}
for _r in csv.DictReader(open(_WP)):
    WARN_PROPOSALS.setdefault((int(_r['warnw']), int(_r['warnp'])), []).append(
        (pd.Timestamp(_r['published']), pd.Timestamp(_r['dated'])))

_SP = os.path.expanduser('~/Projects/Onset Detector Data/139_weekly_state_insured_rate_panel_2026-09-14/leg_s_proposals.csv')
S_PROPOSALS = {}
for _r in csv.DictReader(open(_SP)):
    S_PROPOSALS.setdefault(int(_r['setting']), []).append(
        (pd.Timestamp(_r['published']), pd.Timestamp(_r['dated'])))
print('leg S settings loaded:', {k: len(v) for k, v in sorted(S_PROPOSALS.items())}, flush=True)

_hdr = open('walk54.py').read().split(_MARK)[0].replace("walk54_%s.out", "walk65_%s.out")
_old = "    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TL)"
assert _hdr.count(_old) == 1
_new = _old + """
    _extra = []
    if p.get('warnw'): _extra.append(('N', WARN_PROPOSALS.get((p['warnw'], p['warnp']), [])))
    if p.get('sset'):  _extra.append(('S', S_PROPOSALS.get(p['sset'], [])))
    _extra = [(k, v) for k, v in _extra if v]
    if _extra:
        _bars = []; _op = None
        for _x in turns:
            if _x['kind'] == 'peak' and _op is None:
                _op = _x['published']
            elif _x['kind'] == 'trough' and _op is not None:
                _bars.append((_op, _x['published'] + pd.DateOffset(months=18))); _op = None
        if _op is not None:
            _bars.append((_op, pd.Timestamp('2100-01-01')))
        _any = False
        for _k, _prop in _extra:
            _keep = [(a, b) for a, b in _prop if not any(s <= a <= e for s, e in _bars)]
            if _keep:
                legs[_k] = _keep; _any = True
        if _any:
            with contextlib.redirect_stdout(io.StringIO()): turns = B.american_chronology(legs, TL)"""
_hdr = _hdr.replace(_old, _new)
exec(_hdr)

TARGET = -7
EARLIEST = -31
LATEST = -1

def obj(vw):
    v, w = vw
    a = (sum(1 for x in v if x >= 0),
         sum(1 for x in v if x < EARLIEST or x > LATEST),
         float(np.median([abs(x - TARGET) for x in v])),
         float(np.mean([abs(x - TARGET) for x in v])))
    if not w: return a + (0, 0.0, 0.0)
    return a + (sum(1 for x in w if x > 31 or x < 0),
                float(np.median([abs(x) for x in w])), float(np.mean([abs(x) for x in w])))

GRID = [(n, [0.60, 0.55, 0.50, 0.45, 0.35, 0.30, 0.25, 0.20, 0.15]) if n == 'low' else (n, g) for n, g in GRID]
GRID = GRID + [('warnw', [26, 13, None]), ('warnp', [95, 90, 85]),
               ('sset', [5, 3, 4, 6, 2, 1, None])]   # safest first, by firing count
NAMES = [n for n, _ in GRID]; GD = dict(GRID)
BASE15 = dict(BASE15); BASE15.update(warnw=None, warnp=90, sset=None)

exec(open('walk39.py').read().split(_MARK)[1].split("\n", 1)[1])
