#!/usr/bin/env python3
"""Does the integer-position scorer give what the Timestamp scorer gave? Checked on real episode lists.

The rewrite replaces Timestamp subtraction with integer day arithmetic on a contiguous daily index.
That is exact by construction, but "exact by construction" is what was said about the rolling-maximum
rewrite that was wrong before the first True. So: run the screen's own grid over real channels, and
for every configuration score the same episode list both ways and compare all seven returned fields.
Shifted chronologies are included, since that is where the position arithmetic has to handle peaks
that sit near the ends of the index.
"""
import os, sys, json, random, itertools, warnings, numpy as np, pandas as pd
sys.path.insert(0, '/home/claude/w'); warnings.filterwarnings('ignore')
import us_screen_local as L
S = L.S

def timestamp_scorer(pk, tr, IDX, CRUNCH):
    def inside(t): return any(p <= t <= r for p, r in zip(pk, tr))
    def score(calls_pos):
        calls = [IDX[t] for t in calls_pos]
        used, leads = set(), {}
        for p in pk:
            c = [t for t in calls if 0 <= (p - t).days <= 400]
            if c:
                t = max(c); leads[p.strftime('%Y-%m')] = (t - p).days; used.add(t)
        quiet = [t for t in calls if t not in used and not inside(t)]
        crunch = [t for t in quiet if CRUNCH[0] <= t <= CRUNCH[1]]
        inwin = {k: v for k, v in leads.items() if -92 <= v <= -1}
        return (len(calls), len(leads), len(inwin), len(quiet), len(crunch),
                json.dumps(inwin), json.dumps(leads))
    return score

random.seed(5)
L._apply(0); cand = L.candidates(); sample = random.sample(cand, 40)
total = bad = 0
for shift in (0, 4, -5, 11, 40, -25):
    L._apply(shift); S.init()
    ref = timestamp_scorer(S.PK, S.TR, S.IDX, S.CRUNCH)
    fast = S.score
    for sid in sample:
        for dname, dfn in S.DIRS.items():
            x, ny, how = S.as_of(sid, dfn)
            if x is None: continue
            for pq, pwy, phold in itertools.product((95, 97), (10, 20), (180, 270)):
                Pb = S.hold(S.daily(S.over_q(x, pq, max(12, int(pwy * ny)))), phold)
                for key, Cb in S.CB.items():
                    calls = S.episodes(Pb & Cb)
                    a, b = fast(calls), ref(calls)
                    total += 1
                    if a != b:
                        bad += 1
                        if bad < 4: print('DIFF shift%+d %s %s\n  fast %s\n  ref  %s' % (shift, sid, dname, a, b))
    print('  shift %+3dy done, running total %d comparisons, %d mismatches' % (shift, total, bad), flush=True)
print('\nscore compared %d times across 6 chronologies, mismatches %d' % (total, bad))
