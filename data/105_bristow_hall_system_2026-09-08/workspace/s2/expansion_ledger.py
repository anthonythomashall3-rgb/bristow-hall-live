# -*- coding: utf-8 -*-
"""L7 - THE EXPANSION LEDGER (plan Step 5, L7 and item 18; 23 September 2026, collection 335).

At each yearly cut without a recession the null extends by a year and the margin audit is filed: the year's standing, the days the
rule stood open, the near-miss spells of the year (the index at or above 0.80 outside an episode - plan item 18), the highest reading
outside an episode and its branch, and the channels' worst status. A line may tighten only through the walk; this file is evidence.
Run by the runners on the first run of each year (a mark in cache/); by hand: python3 s2/expansion_ledger.py [YYYY]. Appends one line
to chronology/expansions.jsonl and rewrites nothing."""
import os, sys, json, datetime
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def line_for(year, S):
    d = S['series']['dates']; v = S['series']['values']; ph = S['series']['phase']; br = S['series']['branch']
    ix = [i for i, x in enumerate(d) if x.startswith(str(year))]
    if not ix: return None
    open_days = sum(1 for i in ix if ph[i] == 'open')
    out = [(v[i], d[i], br[i]) for i in ix if ph[i] != 'open' and v[i] is not None]
    hi = max(out) if out else (None, None, None)
    spells = [x for x in (S.get('near_misses') or {}).get('spells', []) if str(x.get('start', ''))[:4] == str(year) or str(x.get('end', ''))[:4] == str(year)]
    eps = [(e['open_pub'], e.get('close_pub')) for e in S['episodes'] if str(e.get('open_pub', ''))[:4] == str(year) or str(e.get('close_pub', '') or '')[:4] == str(year)]
    return dict(year=int(year), filed=datetime.date.today().isoformat(), version=S.get('version'), days_on_grid=len(ix), days_open=open_days, episodes_touching_year=eps,
                highest_outside=dict(value=hi[0], day=hi[1], branch=hi[2]), near_miss_spells=spells,
                channels_worst=max((c.get('status') for c in S.get('channels', [])), key=lambda s: {'current': 0, 'substitute': 1, 'stale': 2, 'dark': 3}.get(s, 0), default=None),
                note='the null extends by this year if no episode opened; a line may tighten only through the walk')
def main(year=None):
    S = json.load(open(os.path.join(HERE, 'out', 'bhs_state.json')))
    year = int(year) if year else datetime.date.today().year - 1
    row = line_for(year, S)
    if row is None: print('expansion ledger: no days for', year); return 1
    p = os.path.join(HERE, 'chronology', 'expansions.jsonl'); os.makedirs(os.path.dirname(p), exist_ok=True)
    have = []
    if os.path.exists(p): have = [json.loads(l) for l in open(p) if l.strip()]
    if any(h.get('year') == year for h in have): print('expansion ledger: %d already filed' % year); return 0
    with open(p, 'a') as f: f.write(json.dumps(row) + '\n')
    print('expansion ledger: filed %d - %d days open, highest outside %s on %s (%s), %d near-miss spells' % (year, row['days_open'], row['highest_outside']['value'], row['highest_outside']['day'], row['highest_outside']['branch'], len(row['near_miss_spells'])))
    return 0
if __name__ == '__main__': sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
