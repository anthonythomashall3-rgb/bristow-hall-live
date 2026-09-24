#!/usr/bin/env python3
"""From 1,758 admissible Canadian configurations to the smallest set that covers every reachable peak.

WHAT THE SCREEN LEFT. Each admissible row is one channel-and-confirmer pair that fires 1-92 days
before at least one C.D. Howe peak and never fires quietly over 1919-2026. A rule needs the peaks
covered TOGETHER, and by as few, and as causally different, channels as possible -- one channel
covering eight peaks is a better rule than eight channels covering one each, and two channels reading
the same underlying quantity are one channel wearing two hats.

Reachable means what the reachability table says it means: a peak no Canadian series could have had a
quantile line by is not a peak this can be asked to cover. 1929 through 1953 are unreachable with two
channels of history; 1957 onward are the test.

The cover is greedy on (peaks added, then earliest lead inside the window), and the same StatCan cube
is not allowed to supply two members -- a cube is one instrument, and two of its series are one
observation, not two.
"""
import os, re, sys, json, collections, pandas as pd

OUT = os.environ.get('CA_OUT', '/mnt/user-data/outputs/ca_out')
D = pd.read_csv(os.path.join(OUT, 'canada_screen.csv'))
R = pd.read_csv(os.path.join(OUT, 'canada_reachability.csv'))
REACH = [p for p, n in zip(R.peak, R.channels_with_10y_history) if n >= 10]
print('reachable peaks (>=10 channels with 10y of history): %s' % ', '.join(REACH))

D['hits'] = D.inwindow.map(lambda s: set(json.loads(s)))
D['leads'] = D.inwindow.map(json.loads)
def cube(sid):
    m = re.match(r'^CA(\d{8})_', sid)
    return m.group(1) if m else sid            # a StatCan cube is one instrument
D['cube'] = D.proposer.map(cube)

need = set(REACH); chosen = []; used_cubes = set()
while need:
    best = None
    for _, r in D.iterrows():
        if r.cube in used_cubes: continue
        gain = r.hits & need
        if not gain: continue
        key = (len(gain), -min(r.leads[p] for p in gain))   # more peaks, then earliest call
        if best is None or key > best[0]: best = (key, r)
    if best is None: break
    r = best[1]; chosen.append(r); used_cubes.add(r.cube); need -= r.hits

print('\ncover uses %d channels; peaks still uncovered: %s' % (len(chosen), sorted(need) or 'none'))
for r in chosen:
    print('  %-58s %-9s q%d/%dy/h%-3d  x  %-20s q%d   %s'
          % (r.proposer[:58], r.direction, r.p_q, r.p_win, r.p_hold, r.confirmer, r.c_q,
             json.dumps({k: v for k, v in sorted(r.leads.items())})))

cnt = collections.Counter()
for _, r in D.iterrows():
    for p in r.hits: cnt[p] += 1
print('\nadmissible configurations per peak: %s' % dict(sorted(cnt.items())))
print('distinct channels %d, distinct cubes %d' % (D.proposer.nunique(), D.cube.nunique()))
best_single = D.assign(k=D.hits.map(len)).sort_values('k', ascending=False).head(8)
print('\nchannels covering the most peaks on their own:')
for _, r in best_single.iterrows():
    print('  %-58s %-9s x %-20s  %s' % (r.proposer[:58], r.direction, r.confirmer, json.dumps(r.leads)))
