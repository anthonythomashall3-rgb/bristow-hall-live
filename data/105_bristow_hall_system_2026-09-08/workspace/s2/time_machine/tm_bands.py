#!/usr/bin/env python3
"""Time Machine (1137): the recessions, disturbances and activity line drawn above the page's timeline, as on the stress map.
Reads the national disturbance chronology the run has just re-dated (s2/disturbance/out/chronology.json, written on GitHub at every
update run by s2/disturbance/disturbance_site.py) and writes site/public/time-machine/bands.json:
  bands: ["R", peak, trough] recession, NBER dates | ["RB", ...] recession dated by the program | ["D", peak, trough, grade] disturbance
  line:  the chronology's composite of activity against its trend, by month.
Run after disturbance_site.py (run_cloud.sh). No AI; never fails the run."""
import json, os
H = os.path.dirname(os.path.abspath(__file__))
src = os.path.join(H, '..', 'disturbance', 'out', 'chronology.json')
out = os.path.abspath(os.path.join(H, '..', '..', '..', 'site', 'public', 'time-machine', 'bands.json'))
j = json.load(open(src, encoding='utf-8'))
nz = lambda x: None if x in (None, 'None', '') else x
bands = [['R', r['peak'], nz(r.get('trough'))] for r in j['recessions'] if r.get('source') == 'NBER']   # 1182: NBER's recessions only
bands += [['D', e['peak'], nz(e.get('trough')), float(e['grade']) if nz(e.get('grade')) else None]
          for e in j['episodes'] if str(e.get('status', '')).startswith('disturbance')]
assert sum(1 for b in bands if b[0] == 'R') >= 12 and len(j['deviation']['date']) == len(j['deviation']['dev']) > 900
new = json.dumps(dict(bands=bands, line=dict(date=j['deviation']['date'], dev=j['deviation']['dev']),
                      through=j.get('composite_last_month')), separators=(',', ':'))
os.makedirs(os.path.dirname(out), exist_ok=True)
if not os.path.exists(out) or open(out).read() != new: open(out, 'w').write(new); print('time machine bands: CHANGED', len(bands), 'bands')
else: print('time machine bands: unchanged')
