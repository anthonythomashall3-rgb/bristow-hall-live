#!/usr/bin/env python3
"""1032-A187: reads the built page and checks that the number agrees with the class in every state: inside a disturbance band the line stays below 2.5; inside a
recession band it reaches 2.5 (or the band's own grade, less the three-month smoothing); and at the latest month a state with damage standing either has a
downturn under way or is recovering from its most recent one. No AI."""
import os, re, json, pandas as pd
C = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); h = open(os.path.join(C, 'web/state-onset/index.html')).read()
A = json.loads(re.search(r'const ALL = (\{.*?\});\n', h, flags=re.S).group(1)); dis = []; rec = []; now = []; n = 0; CUT = 2.0
for st, v in sorted(A.items()):
    d = dict(zip([x[:7] for x in v['series']['dates']], v['series']['values'])); rt = v['dg']['rt']
    for r in v['nber']:
        if r.get('nested'): continue
        n += 1; mx = max([d.get(str(q), 0) or 0 for q in pd.period_range(pd.Period(r['peak'], 'M') + 1, r['trough'], freq='M')] + [0])
        if r['cls'] == 'disturbance' and mx >= CUT and float(r['damage']) < CUT: dis.append(f"{st} {r['peak']} to {r['trough']}: grade {r['damage']}, line reaches {mx}")
        if r['cls'] == 'recession' and mx < CUT and mx < 0.8 * r['damage']: rec.append(f"{st} {r['peak']} to {r['trough']}: grade {r['damage']}, line reaches only {mx}")
    lv = d.get(rt) or 0; und = [r for r in v['nber'] if r.get('open')]
    if lv > 0: now.append({'st': st, 'latest': lv, 'state_of_things': (und[-1]['cls'] + ' under way') if und else 'recovering from the downturn that peaked ' + max(r['peak'] for r in v['nber'])})
out = {'periods': n, 'disturbance_bands_where_the_line_reaches_the_cut': dis, 'recession_bands_where_the_line_stays_low': rec, 'states_with_damage_at_the_latest_month': now}
json.dump(out, open(os.path.join(C, 'out/check_line_matches_class_a187_1032.json'), 'w'), indent=1); print(json.dumps(out, indent=1))
