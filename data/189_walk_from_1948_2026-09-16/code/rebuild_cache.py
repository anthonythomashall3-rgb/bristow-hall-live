"""Recompute every cached summary with the current code and data (patched build_v) and compare with the cache.

Why: the container's fresh summary() and walk 81's device-computed cache disagree on 44 of 120 sampled
configurations, all in one field -- the cache carries a false alarm dated 2026-04-28 (leg N's WARN
proposal) that the corrected arming bar removes. Either those entries were computed under the older bar
or on a data vintage in which the core opened in 2026. A cut can only see false alarms before it, so the
walks' selections were not touched by that entry, but the cache must be made consistent with the code
and data it claims to represent. The memoised build_v makes a full recompute affordable.
"""
import sys, os, io, contextlib, time, pickle, collections
os.chdir('/home/claude/ws'); sys.path.insert(0, '/home/claude/ws')
src = open('walk90.py').read()          # walk 90's preamble carries every leg letter used in any cache key
sys.argv = ['walk90.py', '2027', '2026', 'wrebuild']
t0 = time.time(); buf = io.StringIO()
with contextlib.redirect_stdout(buf): exec(compile(src, 'walk90', 'exec'))
print('preamble %.0f s' % (time.time() - t0), flush=True)
old = pickle.load(open('cache/w90_sum.pkl', 'rb'))
SUM.clear()
keys = list(old.keys()); print('recomputing', len(keys), flush=True)
diff = []; t1 = time.time()
for i, k in enumerate(keys):
    p = dict(zip(NAMES, k)); p.update({n: v for n, v in BASE15.items() if n not in p})
    try: s = summary(p)
    except Exception as e:
        print('ERROR', k, e, flush=True); continue
    r = old[k]
    d = {kk: (s[kk], r[kk]) for kk in ('lags', 'early', 'fa', 'tro', 'pair', 'opens') if s[kk] != r[kk]}
    if d: diff.append((k, d))
    if (i + 1) % 1000 == 0:
        print('%d/%d  %d differ  %.1f min' % (i + 1, len(keys), len(diff), (time.time() - t1) / 60), flush=True)
        pickle.dump(SUM, open('cache/clean_sum.pkl', 'wb'))
pickle.dump(SUM, open('cache/clean_sum.pkl', 'wb'))
pickle.dump(diff, open('cache/clean_diff.pkl', 'wb'))
print('DONE', len(keys), 'differ', len(diff), '%.1f min' % ((time.time() - t1) / 60), flush=True)
c = collections.Counter()
for k, d in diff:
    for kk in d: c[kk] += 1
print('fields differing:', dict(c))
seen = 0
for k, d in diff:
    if any(f in d for f in ('lags', 'early', 'tro', 'pair', 'opens')): seen += 1
    elif 'fa' in d:
        a, b = d['fa']
        if [x for x in a if x < pd.Timestamp('2026-01-01')] != [x for x in b if x < pd.Timestamp('2026-01-01')]: seen += 1
print('differences visible to a cut <= 2026:', seen, flush=True)
