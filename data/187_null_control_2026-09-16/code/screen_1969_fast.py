#!/usr/bin/env python3
"""The 1969 screen, run on the vectorised engine. Same screen, same bar, same arithmetic.

WHY IT IS WRITTEN THIS WAY. This file does not restate the screen. It imports `screen_1969` and
replaces exactly three functions -- `daily`, `hold`, `episodes` -- with the versions in `fastscreen`,
which `fastscreen.verify()` checks against the originals over hundreds of randomised boolean paths
including the degenerate always-on, never-on, isolated-spike and duplicated-date cases. Every other
line of the screen -- the candidate list, the leakage filter, the grid, the confirmer set, the
[-92,-1] window, the quiet count, the 1965-68 credit-crunch count -- is the original file's own code.
Rewriting the whole screen would have been quicker to write and impossible to audit.

TWO TRAPS THIS FILE EXISTS TO AVOID.
1. Patching at import only. macOS spawns pool workers, and a spawned worker re-imports the module
   fresh; without `_patch()` inside the initialiser the workers quietly run the originals -- same
   answer, no speed, and nothing in the output says so. So the patch is applied in the initialiser too.
2. Measuring the speedup after the patch is already in. `_ORIG` is captured at import BEFORE anything
   is replaced, and `_unpatch()` restores it, because a comparison that imports this module first is
   comparing the fast engine with itself. The first timing run here did exactly that and reported a
   1.0x speedup on an engine that is roughly twenty-five times faster.
"""
import os, sys, time, numpy as np, pandas as pd, multiprocessing as mp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import screen_1969 as S
from fastscreen import hold_np, episodes_np, daily_np

_ORIG = (S.daily, S.hold, S.episodes)

def _daily(b): return daily_np(b, S.IDX)
def _hold(b, d): return hold_np(b, d)
def _episodes(fire, minexp=9): return list(S.IDX[episodes_np(fire, minexp)])

def _patch(): S.daily, S.hold, S.episodes = _daily, _hold, _episodes
def _unpatch(): S.daily, S.hold, S.episodes = _ORIG
_patch()

def _init():
    _patch(); S.init()

def candidates():
    conf_ids = {v[0] for v in S.CONFS.values()}
    seen, cand = set(), []
    for f in S.FOLDERS:
        if not os.path.isdir(f): continue
        for fn_ in sorted(os.listdir(f)):
            if not fn_.endswith('.csv'): continue
            sid = fn_[:-4]
            if sid in seen or sid in conf_ids or S.LEAK.match(sid): continue
            seen.add(sid); cand.append(sid)
    return cand

if __name__ == '__main__':
    cand = candidates()
    ncpu = max(1, (os.cpu_count() or 4) - 1)
    print('candidate channels %d, workers %d' % (len(cand), ncpu), flush=True)
    t0 = time.time(); rows = []
    with mp.Pool(ncpu, initializer=_init) as pool:
        for i, res in enumerate(pool.imap_unordered(S.one, cand, chunksize=8)):
            rows += res
            if (i + 1) % 250 == 0:
                print('  %d/%d, %d admissible, %.1f min' % (i + 1, len(cand), len(rows),
                                                            (time.time() - t0) / 60), flush=True)
    D = pd.DataFrame(rows)
    if len(D):
        D = D.sort_values(['proposer', 'direction', 'p_q', 'p_win', 'p_hold', 'confirmer', 'c_q']).reset_index(drop=True)
    D.to_csv(os.path.join(S.OUT, 'screen_1969.csv'), index=False)
    print('\ncompleted in %.1f minutes' % ((time.time() - t0) / 60))
    print('ADMISSIBLE leg configurations: %d over %d distinct channels'
          % (len(D), D.proposer.nunique() if len(D) else 0))
