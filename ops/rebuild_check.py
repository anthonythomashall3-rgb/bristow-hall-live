"""The monthly rebuild check (24 September 2026, collection 369; risks register R7): a machine that has never seen the project
clones the repository, builds the state from the committed data (BHS_MODE=build) and compares it with the state the live site
serves - every episode's open and close day and branches, the chronology, the standing, the grades, the walked record. The
calendar's next days and the build stamps may differ; nothing else may. Prints the verdict; exits 0 always; the caller notifies.
Usage: python3 ops/rebuild_check.py <rebuilt bhs_state.json> [live url]"""
import json, math, sys, urllib.request, os
p = sys.argv[1]; url = sys.argv[2] if len(sys.argv) > 2 else 'https://bhrrealtime.pages.dev/detector/bhs_state.json'
b = json.load(open(p))
a = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'bhr-rebuild-check'}), timeout=60))
def same(x, y):
    if isinstance(x, float) and isinstance(y, float): return (math.isnan(x) and math.isnan(y)) or x == y
    return x == y
def ep(d): return [(e.get('open_pub'), e.get('close_pub'), e.get('open_branch'), e.get('close_branch')) for e in d.get('episodes') or []]
out = {'live_version': a.get('version'), 'rebuilt_version': b.get('version'), 'live_built_at': a.get('built_at'), 'checks': {}}
out['checks']['episodes'] = ep(a) == ep(b)
out['checks']['chronology'] = [(e.get('open_pub'), e.get('close_pub')) for e in a.get('chronology') or []] == [(e.get('open_pub'), e.get('close_pub')) for e in b.get('chronology') or []]
out['checks']['standing'] = (a.get('standing') or {}) == (b.get('standing') or {})
out['checks']['grades'] = [e.get('damage_score') for e in a.get('episodes') or []] == [e.get('damage_score') for e in b.get('episodes') or []]
out['checks']['walked_record'] = json.dumps(a.get('walked_record'), sort_keys=True) == json.dumps(b.get('walked_record'), sort_keys=True)
out['checks']['lines'] = json.dumps(a.get('lines'), sort_keys=True) == json.dumps(b.get('lines'), sort_keys=True)
sa, sb = a.get('series') or {}, b.get('series') or {}
da = dict(zip(sa.get('dates', []), sa.get('values', []))); db = dict(zip(sb.get('dates', []), sb.get('values', [])))
common = [d for d in da if d in db]
out['checks']['series_values'] = all(same(da[d], db[d]) for d in common) and len(common) >= 0.99 * max(1, len(da))
out['checks']['schema_version'] = a.get('schema_version') == b.get('schema_version')   # R10 (collection 372): the same layout, live and rebuilt
out['schema_version'] = {'live': a.get('schema_version'), 'rebuilt': b.get('schema_version')}
out['series_days'] = {'live': len(da), 'rebuilt': len(db), 'common': len(common)}
ok = all(out['checks'].values()) and a.get('version') == b.get('version')
out['verdict'] = 'IDENTICAL' if ok else 'DIFFERENT'
fails = [k for k, v in out['checks'].items() if not v] + ([] if a.get('version') == b.get('version') else ['version %s vs %s' % (a.get('version'), b.get('version'))])
print('R7 rebuild check: %s (live %s built %s; rebuilt %s)%s' % (out['verdict'], a.get('version'), a.get('built_at'), b.get('version'), ('; differs in: ' + ', '.join(fails)) if fails else ''))
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'rebuild_check.json'), 'w'), indent=1)
