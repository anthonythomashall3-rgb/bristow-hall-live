"""Real-time audit of the 400-day arming bar (16 September 2026).

The bar keeps a leg proposal only if the CORE opens within four hundred days after it. In real time the
tool cannot know that on the day the leg fires: a leg firing is a PROVISIONAL open that is confirmed when
the core follows and LAPSES when four hundred days pass without it. A lapsed provisional is a real-time
false alarm even though the walked chronology never shows it. This script lists, for every cut year of a
finished walk, the proposals of the configuration chosen at that cut that (a) fell inside the year,
(b) passed the record-bar filter and (c) failed the 400-day test -- exactly the provisional opens a
reader of the live tool would have seen and later watched lapse.
Run:  python3 lapsed_provisionals.py <walk script> <var>     e.g.  walk81.py w81
"""
import sys, os, io, contextlib, pickle
os.chdir('/home/claude/ws'); sys.path.insert(0, '/home/claude/ws')
WALK, VAR = sys.argv[1], sys.argv[2]
src = open(WALK).read()
# instrument walk 81's block: record proposals that pass the bars but fail _accelerates
old_n = "            _keep = [(a, b) for a, b in _prop\n                     if not any(s <= a <= e for s, e in _bars) and _accelerates(a)]\n            if _keep:\n                legs['N'] = _keep; _added = True"
new_n = old_n + "\n            LAPSED.extend([(a, b, 'N') for a, b in _prop if not any(s <= a <= e for s, e in _bars) and not _accelerates(a)])"
old_l = "            _keep = [(a, b) for a, b in _prop\n                     if not any(s <= a <= e for s, e in _bars) and _accelerates(a)]\n            if _keep:\n                legs[_L] = _keep; _added = True"
new_l = old_l + "\n            LAPSED.extend([(a, b, _L) for a, b in _prop if not any(s <= a <= e for s, e in _bars) and not _accelerates(a)])"
assert src.count(old_n) == 1 and src.count(old_l) == 1, 'instrumentation anchors not found'
src = src.replace(old_n, new_n).replace(old_l, new_l)
sys.argv = [WALK, '2027', '2026', 'wlapsed']
LAPSED = []
buf = io.StringIO()
with contextlib.redirect_stdout(buf): exec(compile(src, WALK, 'exec'))
chosen = pickle.load(open('cache/%s_chosen_1962.pkl' % VAR, 'rb')) if os.path.exists('cache/%s_chosen_1962.pkl' % VAR) else pickle.load(open('cache/%s_prog.pkl' % VAR, 'rb'))['chosen']
rows = []
for cut in sorted(chosen):
    p = chosen[cut]; LAPSED.clear()
    r, t = build_v(p)
    yr = cut.year
    for a, b, L in LAPSED:
        if a.year == yr: rows.append((cut.date(), a.date(), b.strftime('%Y-%m'), L))
print('lapsed provisional opens inside their own cut year, %s:' % VAR)
for x in rows: print('  cut %s  proposal published %s  dated %s  leg %s' % x)
print('total', len(rows))
pickle.dump(rows, open('cache/%s_lapsed.pkl' % VAR, 'wb'))
