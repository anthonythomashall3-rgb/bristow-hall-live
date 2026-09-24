"""A frozen sweep under the NEVER-LATE criterion: is there any configuration that is early everywhere?

This is a ceiling, not a record. A frozen run reads the whole sample at once and the walk must
choose without hindsight, so nothing here is a claim about what the rule would have called. It
answers one question: with the WARN leg armed, is there any configuration of `low`, `wline`,
`wline2` and `u45` that brings 1969 and 1981 inside a month of their peak month's end while keeping
thirteen of thirteen, no false alarm, and the calls leg N restores at 2007 and 2024?
Run:  python3 frozen_sweep_warn.py 1962 2026 fs
"""
import sys, pickle, os, csv, itertools
SEARCH_TERMS = ['unemp', 'layoffs', 'laidoff']; os.environ['BHS_SEARCH_TERMS'] = ','.join(SEARCH_TERMS)
_MARK = "# ---- the walk " + "itself"
import pandas as pd, numpy as np

_WP = os.path.expanduser('~/Projects/Onset Detector Data/121_warn_causal_breadth_2026-09-14/out/warn_leg_proposals.csv')
WARN_PROPOSALS = {}
for _r in csv.DictReader(open(_WP)):
    WARN_PROPOSALS.setdefault((int(_r['warnw']), int(_r['warnp'])), []).append(
        (pd.Timestamp(_r['published']), pd.Timestamp(_r['dated'])))

_hdr = open('walk54.py').read().split(_MARK)[0].replace("walk54_%s.out", "frozen_nolate_%s.out")
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
            if _keep:
                legs['N'] = _keep
                with contextlib.redirect_stdout(io.StringIO()): turns = B.american_chronology(legs, TL)"""
_hdr = _hdr.replace(_old, _new)
exec(_hdr)

PK9 = [pd.Timestamp(s + '-01') + pd.offsets.MonthEnd(0) for s in
       ['1969-12','1973-11','1980-01','1981-07','1990-07','2001-03','2007-12','2020-02','2024-04']]
base = pickle.load(open('cache/w60_carry.pkl', 'rb'))
rows = []
# Anthony's instruction of 14 September: every call must land BEFORE the peak month's end. The band
# sweep of frozen_sweep_warn.py found nothing with fewer than two late calls, but it only searched
# around walk 60's carried configuration, whose tight 'low' is exactly what pushes 1980 past its
# month's end. This sweep reopens the loose end of 'low' and the proposer lines that move 1980 and
# 2020, and scores by the count of LATE calls first.
for low, wl, wl2, u45, ic in itertools.product([0.60, 0.50, 0.45, 0.35, 0.30, 0.25, 0.20, 0.15],
                                               [0.40, 0.35, 0.30, 0.25], [0.60, 0.50, 0.45],
                                               [0.70, 0.55, 0.45, 0.35, 0.30], [60, 50, 45]):
    p = dict(base); p.update(low=low, wline=wl, wline2=wl2, u45=u45, ic=ic, warnw=26, warnp=90)
    try:
        r, t = build_v(p)
    except Exception as e:
        continue
    opens = [x for x in t if x['kind'] == 'peak']
    lags, legs_used, ok = [], [], True
    for pe in PK9:
        c = [x for x in opens if pe - pd.DateOffset(months=9) <= x['published'] <= pe + pd.DateOffset(months=9)]
        if not c:
            ok = False; break
        lags.append((c[0]['published'] - pe).days); legs_used.append(c[0]['leg'])
    if not ok:
        continue
    # a false alarm: an open that belongs to no recession window at all
    fa = 0
    for x in opens:
        if not any(pe - pd.DateOffset(months=9) <= x['published'] <= pe + pd.DateOffset(months=9) for pe in PK9) \
           and x['published'] > pd.Timestamp('1962-01-01'):
            fa += 1
    rows.append(dict(low=low, wline=wl, wline2=wl2, u45=u45, ic=ic, fa=fa,
                     late=sum(1 for l in lags if l >= 0),
                     outwin=sum(1 for l in lags if l < -31 or l > -7),
                     err9=sum(abs(l + 7) for l in lags),
                     outband=sum(1 for l in lags if l > 31 or l < -31),
                     lags=';'.join(str(l) for l in lags), legs=''.join(legs_used)))
    print(rows[-1], flush=True)
d = pd.DataFrame(rows)
d.to_csv('frozen_sweep_nolate.csv', index=False)
print('\nconfigurations kept 13/13 and no false alarm:', len(d[d.fa == 0]))
print(d[d.fa == 0].sort_values(['late', 'outwin', 'err9']).head(15).to_string(index=False))
