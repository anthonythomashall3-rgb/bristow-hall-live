#!/usr/bin/env python3
"""Does the vectorised `as_of` return what the original returned? Checked on real channels.

The rewrite replaces a per-observation `pb.get(t)` loop with a reindex. Equivalent in principle; this
compares the actual returned series, index and read-type on a sample of channels, and then compares
the emitted screen rows, which is what the result depends on.
"""
import os, sys, random, warnings, numpy as np, pandas as pd
sys.path.insert(0, '/home/claude/w'); warnings.filterwarnings('ignore')
import us_screen_local as L
S = L.S
L._apply(0)
cand = L.candidates(); random.seed(11)
# bias toward channels that HAVE first prints, since that is the branch that was rewritten
fps = {f[:-len('_firstprint.csv')] for f in os.listdir(L.FP) if f.endswith('_firstprint.csv')}
sample = sorted(fps & set(cand)) + random.sample(cand, 60)
bad = 0
for sid in sample:
    for dn, dfn in S.DIRS.items():
        a = S._as_of_orig(sid, dfn); b = L._as_of_fast(sid, dfn)
        if (a[0] is None) != (b[0] is None): bad += 1; print('NONE DIFF', sid, dn); continue
        if a[0] is None: continue
        if a[1] != b[1] or a[2] != b[2]: bad += 1; print('META DIFF', sid, dn, a[1:], b[1:]); continue
        if not a[0].index.equals(b[0].index): bad += 1; print('INDEX DIFF', sid, dn, len(a[0]), len(b[0])); continue
        if not np.allclose(a[0].values.astype(float), b[0].values.astype(float), equal_nan=True):
            bad += 1; print('VALUE DIFF', sid, dn)
print('as_of checked on %d channels x 4 directions, mismatches %d' % (len(sample), bad))

S.init()
rb = 0
for sid in sample[:40]:
    S.as_of = S._as_of_orig; x = L.one_any(sid)
    S.as_of = L._as_of_fast;  y = L.one_any(sid)
    if x != y: rb += 1; print('ROWS DIFF', sid, len(x), len(y))
print('screen rows checked on %d channels, mismatches %d' % (min(40, len(sample)), rb))
