#!/usr/bin/env python3
"""Does the fast screen give the SAME rows as the slow one? Checked on real channels, not on synthetics.

`fastscreen.verify()` shows the two rewritten functions agree on random boolean paths. That is the
narrow claim. This is the wide one: run the screen's own `one()` over a sample of the actual candidate
channels, once with the original functions and once patched, and compare the emitted rows field by
field. If the two disagree anywhere the fast screen is not usable and the speed is worth nothing.
"""
import os, sys, time, random, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import screen_1969 as S
import screen_1969_fast as F

N = int(sys.argv[1]) if len(sys.argv) > 1 else 25
# Second argument restricts the sample to chosen FOLDERS entries, e.g. "0,3" for the monthly
# collections. A uniform sample over all 5,913 candidates is dominated by the high-frequency folder,
# where most series are too short to clear the screen's 60-observation floor and `one()` returns
# before the grid is ever entered -- so a uniform sample compares two code paths on inputs that
# exercise neither, and reports a truthful but empty agreement.
PICK = [int(z) for z in sys.argv[2].split(',')] if len(sys.argv) > 2 else list(range(len(S.FOLDERS)))
conf_ids = {v[0] for v in S.CONFS.values()}
seen, cand = set(), []
for fi, f in enumerate(S.FOLDERS):
    if not os.path.isdir(f) or fi not in PICK: continue
    for fn_ in sorted(os.listdir(f)):
        if not fn_.endswith('.csv'): continue
        sid = fn_[:-4]
        if sid in seen or sid in conf_ids or S.LEAK.match(sid): continue
        seen.add(sid); cand.append(sid)
random.seed(7); sample = random.sample(cand, min(N, len(cand)))
print('sampling %d of %d candidates' % (len(sample), len(cand)), flush=True)

# Importing the fast module patches the screen, so the baseline must be restored explicitly.
# Without this the comparison runs the fast engine twice and reports a 1.0x speedup.
F._unpatch()
S.init(); t0 = time.time()
slow = {sid: S.one(sid) for sid in sample}
t_slow = time.time() - t0

F._patch(); S.init(); t0 = time.time()
fast = {sid: S.one(sid) for sid in sample}
t_fast = time.time() - t0

bad = 0
for sid in sample:
    a, b = slow[sid], fast[sid]
    if len(a) != len(b): bad += 1; print('COUNT DIFF %s %d vs %d' % (sid, len(a), len(b))); continue
    for ra, rb in zip(a, b):
        if ra != rb:
            bad += 1; print('ROW DIFF %s\n  slow %s\n  fast %s' % (sid, ra, rb)); break
print('\nrows slow %d, rows fast %d, mismatching channels %d'
      % (sum(len(v) for v in slow.values()), sum(len(v) for v in fast.values()), bad))
print('slow %.1f s, fast %.1f s, speedup %.1fx' % (t_slow, t_fast, t_slow / max(t_fast, 1e-9)))
