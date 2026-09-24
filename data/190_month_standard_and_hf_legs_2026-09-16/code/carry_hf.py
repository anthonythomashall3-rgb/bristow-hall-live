"""v3.56 candidate -- the high-frequency legs carried on walk 94's record under the v3.55 protocol (16 September 2026).
Walk 96 (PREREG-v356) took leg / (30-year mortgage rate falling x petroleum products supplied falling) at the 2002 cut
and thereby did not take AY there: 2020 opened 2019-12-11 (-81) but 2007 fell back to the core's B on 2007-12-24 (-7).
On the standing tie-break (the record furthest from lateness, compared from the closest call outwards) walk 94 stands.
So the twelve legs are carried the way v3.55 carries its thirty-four: walk 94's chosen configuration at every cut is
recomputed with the legs armed; a leg that changes any walked call is NOT carried (armed from 2026-09-16, backtest
shown); every proposal that would have lapsed (passed the record bar, no core open within 400 days) is counted.
Run from 105/workspace:  python3 carry_hf.py"""
import sys, os, io, contextlib, pickle, json, time
import pandas as pd
_ROOT = os.path.expanduser('~/Projects/Onset Detector Data')
if not os.path.isdir(_ROOT): _ROOT = os.path.expanduser('~/mnt/Onset Detector Data')
OUT = os.path.join(_ROOT, '190_month_standard_and_hf_legs_2026-09-16', 'out'); os.makedirs(OUT, exist_ok=True)
src = open('walk96.py').read()
old_l = "            _keep = [(a, b) for a, b in _prop\n                     if not any(s <= a <= e for s, e in _bars) and _accelerates(a)]\n            if _keep:\n                legs[_L] = _keep; _added = True"
assert src.count(old_l) == 1
src = src.replace(old_l, old_l + "\n            LAPSED.extend([(a, b, _L) for a, b in _prop if not any(s <= a <= e for s, e in _bars) and not _accelerates(a)])")
old_n = "            _keep = [(a, b) for a, b in _prop\n                     if not any(s <= a <= e for s, e in _bars) and _accelerates(a)]\n            if _keep:\n                legs['N'] = _keep; _added = True"
assert src.count(old_n) == 1
src = src.replace(old_n, old_n + "\n            LAPSED.extend([(a, b, 'N') for a, b in _prop if not any(s <= a <= e for s, e in _bars) and not _accelerates(a)])")
tail_line = "exec(open('walk39.py').read().split(_MARK)[1].split(\"\\n\", 1)[1])"
assert src.count(tail_line) == 1
src = src.replace(tail_line, "")
sys.argv = ['walk96.py', '2027', '2026', 'wcarryhf']
LAPSED = []
t0 = time.time(); buf = io.StringIO()
with contextlib.redirect_stdout(buf): exec(compile(src, 'walk96_head', 'exec'))
print('preamble %.0f s' % (time.time() - t0), flush=True)
chosen = pickle.load(open('cache/w94_chosen_1962.pkl', 'rb'))
def record(letters):
    log = []; lapsed = []
    for cut in sorted(chosen):
        p = dict(chosen[cut]); Y = cut.year; p['hf'] = letters or None
        LAPSED.clear(); r, t = build_v(p)
        for x in t:
            if x['kind'] in ('peak', 'trough') and cut <= x['published'] < pd.Timestamp(Y + 1, 1, 1):
                log.append((x['published'].strftime('%Y-%m-%d'), 'OPEN' if x['kind'] == 'peak' else 'CLOSE', x['date'].strftime('%Y-%m'), x['leg']))
        for a, b, L in LAPSED:
            # 17 Sep 2026: a proposal is lapsed only when its 400 days have passed with no core open; the build's LAPSED
            # collector also lists proposals still pending (leg N's 2026-04-28 was written into every hf leg's column)
            if a.year == Y and (pd.Timestamp.today() - a).days > 400: lapsed.append((cut.year, a.strftime('%Y-%m-%d'), b.strftime('%Y-%m'), L))
    return sorted(log), sorted(lapsed)
base_log, base_lapsed = record('')
all_log, all_lapsed = record(HF_ALL)
print('walk 94 record:'); [print('  ', x) for x in base_log]
print('with every hf leg:'); [print('  ', x) for x in all_log]
changed = [x for x in all_log if x not in base_log] + [x for x in base_log if x not in all_log]
print('record changed by carrying all:', changed)
bad = []
per = {}
for L in HF_ALL:
    lg, lp = record(L); per[L] = dict(changes=[x for x in lg if x not in base_log], lapsed=lp)
    if lg != base_log: bad.append(L)
    print('  leg', L, 'changes:', per[L]['changes'], 'lapsed:', lp)
keep = ''.join(L for L in HF_ALL if L not in bad)
final_log, final_lapsed = record(keep)
print('carried after exclusion:', repr(keep), 'record identical to walk 94:', final_log == base_log, 'lapsed:', final_lapsed)
sel = pd.read_csv(os.path.join(OUT, 'hf_legs_selected.csv'))
sel['carried'] = sel.letter.isin(list(keep)); sel['changes_walked_record'] = sel.letter.map(lambda L: json.dumps(per[L]['changes']))
sel['lapsed_proposals'] = sel.letter.map(lambda L: ' '.join(a for (y, a, b, l) in per[L]['lapsed'] if l == L))   # the leg's own lapsed proposals (17 Sep 2026: was every leg's)
sel['proposals'] = sel.letter.map(lambda L: ' '.join(a.strftime('%Y-%m-%d') for a, b in NEW_LEGS[L]))
sel.to_csv(os.path.join(OUT, 'v356_hf_carried_legs.csv'), index=False)
json.dump(dict(walk94=base_log, with_all_hf=all_log, changed_by_all=changed, future_only=bad, carried=keep, lapsed_walk94=base_lapsed,
               lapsed_all=all_lapsed, lapsed_carried=final_lapsed, walk96_record=[l.strip() for l in open('walk96_1962.out') if l.startswith('   ') and ('OPEN' in l or 'CLOSE' in l)]),
          open(os.path.join(OUT, 'v356_record.json'), 'w'), indent=1, default=str)
pickle.dump(dict(HF={L: NEW_LEGS[L] for L in HF_ALL}, keep=keep, table=sel.to_dict('records')), open('cache/v356_hf_carry.pkl', 'wb'))
print('written', OUT, flush=True)
