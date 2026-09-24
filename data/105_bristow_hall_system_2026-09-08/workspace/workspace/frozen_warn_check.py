"""A frozen check, not a walk: does leg N, armed by the rule's own record, restore the 2007 call?

Walk 62 will answer this properly and will take hours. This asks the same question cheaply, at one
configuration - the one walk 60 carried out of its last cut - so that the walk is not left running
on a leg that cannot help. Nothing here is a claim about the record: a frozen run reads the whole
sample at once and the walk must choose without hindsight.
Run:  python3 frozen_warn_check.py 1962 2026 fz
"""
import sys, pickle, os, csv
SEARCH_TERMS = ['unemp', 'layoffs', 'laidoff']; os.environ['BHS_SEARCH_TERMS'] = ','.join(SEARCH_TERMS)
_MARK = "# ---- the walk " + "itself"
import pandas as pd, numpy as np

_WP = os.path.expanduser('~/Projects/Onset Detector Data/121_warn_causal_breadth_2026-09-14/out/warn_leg_proposals.csv')
WARN_PROPOSALS = {}
for _r in csv.DictReader(open(_WP)):
    WARN_PROPOSALS.setdefault((int(_r['warnw']), int(_r['warnp'])), []).append(
        (pd.Timestamp(_r['published']), pd.Timestamp(_r['dated'])))

_hdr = open('walk54.py').read().split(_MARK)[0].replace("walk54_%s.out", "frozen_warn_%s.out")
_old = "    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TL)"
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
            print('  proposals kept:', [str(a.date()) for a, b in _keep])
            if _keep:
                legs['N'] = _keep
                with contextlib.redirect_stdout(io.StringIO()): turns = B.american_chronology(legs, TL)"""
_hdr = _hdr.replace(_old, _new)
exec(_hdr)

base = pickle.load(open('cache/w60_carry.pkl', 'rb'))
for warn in (None, (26, 90), (26, 85), (13, 90)):
    p = dict(base)
    p['warnw'], p['warnp'] = (warn if warn else (None, 90))
    r, t = build_v(p)
    opens = [(x['published'], x['leg']) for x in t if x['kind'] == 'peak']
    print('\n=== warn', warn, ' low', p['low'], 'wline', p['wline'])
    for pub, leg in opens:
        print('   OPEN', pub.date(), 'by', leg)
