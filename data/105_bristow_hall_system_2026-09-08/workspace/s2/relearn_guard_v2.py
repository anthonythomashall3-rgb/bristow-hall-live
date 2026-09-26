# -*- coding: utf-8 -*-
"""Gap 11, v2 (collection 427; amendment A1 after the independent verification of collection 430): THE RE-SELECTION GUARD.
v1 compared counts and 'any close near the trough'; the verifier built six harmful re-walks that passed it. v2 compares the
matched EPISODE of every recession, event for event:
  clause 1  every diary event on or before the lesson day identical - date, kind, dated month and branch;
  clause 0  the diary alternates OPEN/CLOSE (a malformed diary is refused);
  clause 2a the new false alarms are a subset of the shipped ones (dates), on each board;
  clause 2b every recession the shipped diary calls is called, not later than shipped, and inside [-92, +31] if shipped was;
  clause 2c no more episodes opening inside a recession's span than shipped (no premature close and re-open);
  clause 3  the matched episode's OWN close: inside [-31, +31] if shipped was, and never further from the trough-month end if shipped was outside.
The labour diary is what the walk re-selects; the union with the openers is scored by the port battery.
    python3 relearn_guard_v2.py <new_memo> <lesson_day> [--shipped e29]      python3 relearn_guard_v2.py --selftest"""
import os, sys, json, pickle, importlib.util
import pandas as pd
OD = os.environ.get('OD') or os.path.expanduser('~/Projects/Onset Detector Data'); os.environ['OD'] = OD
sys.path.insert(0, os.path.join(OD, '275_best_bhrt_frozen_and_walk_2026-09-20', 'code')); import clock
SB = os.path.join(OD, '276_core_v6_lab_speed_1960_tiers_2026-09-20', 'sandbox', 'cache')
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'out', 'relearn_guard')   # v3.76: the guard's verdicts in the workspace
T = pd.Timestamp; MATCH_LO = -122
def diary(memo):
    return [(T(e[0]), e[1], T(e[2]), e[3]) for e in sorted(pickle.load(open(os.path.join(SB, memo + '_prog.pkl'), 'rb'))['log'], key=lambda z: z[0])]
def episodes(d):
    """(open, close) pairs; a CLOSE before the diary's first OPEN closes an episode another branch opened before the labour
    diary begins (the 1948-49 episode, opened by the activity opener) and is kept as an orphan close, not a malformation."""
    eps, cur, ok, orphans = [], None, True, []
    for i, (t, k, m, g) in enumerate(d):
        if k == 'OPEN':
            if cur is not None: ok = False
            cur = [t, None]
        else:
            if cur is None:
                if eps or cur is not None or any(x[1] == 'OPEN' for x in d[:i]): ok = False
                else: orphans.append(t)
                continue
            cur[1] = t; eps.append(tuple(cur)); cur = None
    if cur is not None: eps.append((cur[0], None))
    return eps, ok, orphans
def match(eps, board, orphans=()):
    ch = clock.BOARDS[board]; used = set(); rec = {}
    for pk, tr in ch:
        lo, hi = clock.mend(pk) + pd.Timedelta(days=MATCH_LO), clock.mend(tr)
        inside = [i for i, (o, c) in enumerate(eps) if lo <= o <= hi]
        first = next((i for i in inside if i not in used), None)
        if first is None:
            oc = [c for c in orphans if abs((c - clock.mend(tr)).days) <= 400]       # an orphan close is scored against the nearest trough
            rec[pk] = dict(open=None, close=(int((oc[0] - clock.mend(tr)).days) if oc else None), splits=0); continue
        used.update(inside); o, c = eps[first]
        rec[pk] = dict(open=int((o - clock.mend(pk)).days), close=(int((c - clock.mend(tr)).days) if c is not None else None), splits=len(inside) - 1)
    fa = sorted(str(eps[i][0].date()) for i in range(len(eps)) if i not in used)
    return rec, fa
def guard(new, lesson_day, shipped='e29', new_diary=None, tag=None, ship_diary=None):
    L = T(lesson_day); a = ship_diary if ship_diary is not None else diary(shipped); b = new_diary if new_diary is not None else diary(new)
    reasons = []
    pa = [e for e in a if e[0] <= L]; pb = [e for e in b if e[0] <= L]
    if pa != pb: reasons.append(dict(clause=1, what='the diary changed on or before the lesson day', shipped_only=[str(x[0].date()) + ' ' + x[1] for x in pa if x not in pb], new_only=[str(x[0].date()) + ' ' + x[1] for x in pb if x not in pa]))
    ea, oka, oa = episodes(a); eb, okb, ob = episodes(b)
    if not okb: reasons.append(dict(clause=0, what='the new diary does not alternate OPEN/CLOSE'))
    for board in ('N+P1', 'BHRC'):
        ra, fa_a = match(ea, board, oa); rb, fa_b = match(eb, board, ob)
        extra = sorted(set(fa_b) - set(fa_a))
        if extra: reasons.append(dict(clause='2a', board=board, what='new false alarms', new=extra))
        for pk, s in ra.items():
            n = rb.get(pk)
            if s['open'] is not None:
                if n['open'] is None: reasons.append(dict(clause='2b', board=board, pk=pk, what='a called recession is no longer called'))
                else:
                    if n['open'] > s['open']: reasons.append(dict(clause='2b', board=board, pk=pk, what='the call is later', shipped=s['open'], new=n['open']))
                    if -92 <= s['open'] <= 31 and not (-92 <= n['open'] <= 31): reasons.append(dict(clause='2b', board=board, pk=pk, what='the call leaves [-92, +31]', new=n['open']))
            if n['splits'] > s['splits']: reasons.append(dict(clause='2c', board=board, pk=pk, what='more episodes inside the recession (a premature close and re-open)', shipped=s['splits'], new=n['splits']))
            if s['close'] is not None:
                if n['close'] is None: reasons.append(dict(clause=3, board=board, pk=pk, what='the episode no longer closes'))
                elif abs(s['close']) <= 31 and abs(n['close']) > 31: reasons.append(dict(clause=3, board=board, pk=pk, what='the close leaves [-31, +31]', new=n['close']))
                elif abs(s['close']) > 31 and abs(n['close']) > abs(s['close']): reasons.append(dict(clause=3, board=board, pk=pk, what='an outside close moves further out', shipped=s['close'], new=n['close']))
    res = dict(new=tag or new, shipped=shipped, lesson_day=lesson_day, verdict='REFUSED' if reasons else 'MAY PROCEED', reasons=reasons)
    os.makedirs(OUT, exist_ok=True); json.dump(res, open(os.path.join(OUT, 'guard_v2_%s.json' % (tag or new)), 'w'), indent=1, default=str)
    print('%-36s lesson %s -> %s' % (tag or new, lesson_day, res['verdict']))
    for r in reasons[:4]: print('      ', json.dumps(r, default=str)[:300])
    return 0 if not reasons else 2
def _edit(d, drop=(), add=(), move=()):
    d = [e for e in d if (e[0], e[1]) not in {(T(x), k) for x, k in drop}]
    for (x, k), y in move: d = [((T(y), e[1], e[2], e[3]) if (e[0] == T(x) and e[1] == k) else e) for e in d]
    d += [(T(x), k, T(x[:7] + '-01'), g) for x, k, g in add]
    return sorted(d, key=lambda z: z[0])
if __name__ == '__main__':
    if len(sys.argv) >= 2 and sys.argv[1] == '--selftest':
        a = diary('e29'); E = []
        E.append(('T1_identity', guard('e29', '2026-09-26', tag='T1_identity'), 0))
        E.append(('T2_e79s_rule_change', guard('e79s', '2026-09-26', tag='T2_e79s_rule_change'), 2))
        E.append(('T3_synthetic_2015_fa', guard('x', '2015-01-01', new_diary=_edit(a, add=[('2015-06-01', 'OPEN', 'U'), ('2015-12-01', 'CLOSE', 'C')]), tag='T3_synthetic_2015_fa'), 2))
        E.append(('T4_synthetic_2024_late', guard('x', '2024-01-01', new_diary=_edit(a, move=[(('2024-05-03', 'OPEN'), '2024-07-15')]), tag='T4_synthetic_2024_late'), 2))
        E.append(('T5_benign_2024_earlier', guard('x', '2024-01-01', new_diary=_edit(a, move=[(('2024-05-03', 'OPEN'), '2024-04-01')]), tag='T5_benign_2024_earlier'), 0))
        E.append(('T6_redated_month', guard('x', '2026-09-26', new_diary=[((t, k, (T('2020-02-01') if (t == T('2020-03-12') and k == 'OPEN') else m), g)) for t, k, m, g in a], tag='T6_redated_month'), 2))
        # the verifier's six (collection 430, code/guard_adversarial.py), rebuilt here on the dated-month diary
        E.append(('A1_gap_inside_2008', guard('x', '2008-01-01', new_diary=_edit(a, add=[('2008-06-02', 'CLOSE', 'C'), ('2008-09-15', 'OPEN', 'U')]), tag='A1_gap_inside_2008'), 2))
        E.append(('A2_close_moved_spurious_2020', guard('x', '2020-01-01', new_diary=_edit(a, add=[('2020-04-20', 'CLOSE', 'C'), ('2020-04-27', 'OPEN', 'K')], move=[(('2020-05-07', 'CLOSE'), '2020-12-01')]), tag='A2_close_moved_spurious_2020'), 2))
        E.append(('A3_call_later_inside_2001', guard('x', '2001-01-01', new_diary=_edit(a, move=[(('2001-03-29', 'OPEN'), '2001-04-30')]), tag='A3_call_later_inside_2001'), 2))
        E.append(('A4_late_call_later_1960', guard('x', '1960-01-01', new_diary=_edit(a, move=[(('1960-08-30', 'OPEN'), '1960-11-15')]), tag='A4_late_call_later_1960'), 2))
        E.append(('A5_late_close_later_1950', guard('x', '1949-12-31', new_diary=_edit(a, move=[(('1950-01-26', 'CLOSE'), '1950-09-01')]), tag='A5_late_close_later_1950'), 2))
        s6 = _edit(a, add=[('2017-06-01', 'OPEN', 'U'), ('2017-12-01', 'CLOSE', 'C')]); n6 = _edit(a, add=[('2018-06-01', 'OPEN', 'U'), ('2018-12-01', 'CLOSE', 'C')])
        E.append(('A6_fa_swapped', guard('x', '2016-01-01', ship_diary=s6, new_diary=n6, tag='A6_fa_swapped'), 2))
        E.append(('C1_close_leaves_2009', guard('x', '2009-01-01', new_diary=_edit(a, move=[(('2009-06-18', 'CLOSE'), '2009-10-01')]), tag='C1_close_leaves_2009'), 2))
        E.append(('C2_too_early_open_2007', guard('x', '2007-01-01', new_diary=_edit(a, add=[('2007-07-16', 'OPEN', 'U'), ('2007-08-20', 'CLOSE', 'C')]), tag='C2_too_early_open_2007'), 2))
        bad = [(n, rc, want) for n, rc, want in E if rc != want]
        print('SELFTEST v2', 'PASS' if not bad else 'FAIL', '| cases', len(E), '| mismatches', bad); sys.exit(0 if not bad else 1)
    if len(sys.argv) < 3: print(__doc__); sys.exit(1)
    sh = sys.argv[sys.argv.index('--shipped') + 1] if '--shipped' in sys.argv else 'e29'
    sys.exit(guard(sys.argv[1], sys.argv[2], shipped=sh))
