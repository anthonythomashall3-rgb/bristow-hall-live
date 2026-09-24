#!/usr/bin/env python3
"""Vectorised replacements for the two hot functions in the frozen channel screens.

WHY. Profiling the 1969 screen showed the cost is not the data work and not the quantile lines; it is
`episodes()`, which walks a 29,463-day boolean index one Python step at a time and is called 512 times
per candidate channel -- about fifteen million interpreter steps for every series screened. The screen
was running at roughly 44 channels a minute on seven workers, which puts the 5,910-channel pool at
about two and a quarter hours and made a re-run something to avoid rather than something to do.

WHAT IS PRESERVED. Nothing about the method changes. `episodes` is a state machine over a CONTIGUOUS
daily index, so the day difference `(t - last).days` is exactly the difference of positions, and the
machine's next transition can be found by a binary search instead of by stepping. `hold` is a rolling
maximum of a boolean, which is the same thing as asking whether the last True lies inside the window.
Both rewrites are exact, not approximate, and `verify()` in this file checks that claim against the
original implementations rather than asserting it.

THE ONE BUG THIS AVOIDS. A naive rolling-max rewrite, `(idx - last_true_index) < d`, is wrong before
the first True: `last` is -1 there and `i + 1 < d` reports a hold that never started. The guard
`(last >= 0)` is load-bearing, and `verify()` fails without it.
"""
import numpy as np, pandas as pd
_np = np

def hold_np(arr, d):
    """Exactly pandas `Series(arr).rolling(d, min_periods=1).max().astype(bool)`."""
    a = np.asarray(arr, dtype=bool)
    idx = np.arange(a.size)
    last = np.maximum.accumulate(np.where(a, idx, -1))
    return (last >= 0) & ((idx - last) < d)

def episodes_np(arr, minexp=9):
    """Positions of episode starts. Exactly the original `episodes()` on a contiguous daily index."""
    a = np.asarray(arr, dtype=bool)
    tpos = np.flatnonzero(a); fpos = np.flatnonzero(~a)
    gap = minexp * 30
    out, i = [], 0
    nt, nf = tpos.size, fpos.size
    while True:
        k = np.searchsorted(tpos, i)
        if k >= nt: break
        c = int(tpos[k]); out.append(c)
        j = np.searchsorted(fpos, c + gap)
        if j >= nf: break
        i = int(fpos[j]) + 1
    return out


def daily_np(b, IDX):
    """Exactly `b.reindex(IDX.union(b.index)).ffill().reindex(IDX).fillna(False).astype(bool)`.

    Forward-filling a boolean observation series onto a daily calendar is a lookup: each day takes the
    value of the last observation at or before it, and False before the first observation. `side='right'`
    makes a duplicated observation date resolve to its last entry, which is what ffill does after the
    union. Requires `b.index` sorted ascending, which it is -- it inherits the sorted index of the
    transformed series.
    """
    n = len(IDX)
    if len(b) == 0: return _np.zeros(n, bool)
    pos = _np.searchsorted(_np.asarray(b.index.values), _np.asarray(IDX.values), side='right') - 1
    bv = _np.asarray(b.values).astype(bool)
    out = _np.zeros(n, bool)
    ok = pos >= 0
    out[ok] = bv[pos[ok]]
    return out

def _daily_ref(b, IDX):
    return b.reindex(IDX.union(b.index)).ffill().reindex(IDX).fillna(False).astype(bool)

# ---- the originals, kept here only so the rewrites can be checked against them ----
def _hold_ref(b, d): return b.rolling(d, min_periods=1).max().astype(bool)
def _episodes_ref(fire, minexp=9):
    out, armed, last = [], True, None
    for t, f in fire.items():
        if armed and f: out.append(t); armed = False; last = t
        elif not armed and last is not None and (t - last).days >= minexp * 30 and not f: armed = True
    return out

def verify(n_trials=400, n=29463, seed=0):
    """Compare each rewrite with the original it replaces, over random and degenerate boolean paths."""
    rng = np.random.default_rng(seed)
    IDX = pd.date_range('1946-01-31', periods=n, freq='D')
    bad_h = bad_e = 0
    for k in range(n_trials):
        mode = k % 4
        if mode == 0: a = rng.random(n) < rng.uniform(0.01, 0.9)
        elif mode == 1:                       # long blocks, the realistic shape
            a = np.zeros(n, bool); t = 0
            while t < n:
                w = rng.integers(5, 900); a[t:t + w] = rng.random() < 0.35; t += w
        elif mode == 2: a = np.zeros(n, bool)               # never fires
        else:
            a = np.zeros(n, bool); a[rng.integers(0, n, 3)] = True   # isolated spikes
        if mode == 2 and k % 8 == 2: a[:] = True            # always on
        s = pd.Series(a, index=IDX)
        for d in (180, 270, 1):
            if not np.array_equal(hold_np(a, d), _hold_ref(s, d).values): bad_h += 1
        for me in (9, 6):
            got = episodes_np(a, me)
            ref = [IDX.get_loc(t) for t in _episodes_ref(s, me)]
            if got != ref: bad_e += 1
    # daily_np: an irregular observation index forward-filled onto the daily calendar, including
    # observations before the calendar starts, after it ends, and repeated on one date.
    bad_d = 0
    for k in range(n_trials // 4):
        m = int(rng.integers(3, 400))
        off = rng.integers(-800, n + 800, m)
        obs = pd.DatetimeIndex(sorted(IDX[0] + pd.to_timedelta(off, unit='D')))
        if k % 5 == 0 and len(obs) > 3: obs = obs.append(obs[[1, 1, 2]]).sort_values()
        b = pd.Series(rng.random(len(obs)) < 0.4, index=obs)
        if not np.array_equal(daily_np(b, IDX), _daily_ref(b[~b.index.duplicated(keep='last')], IDX).values
                              if b.index.has_duplicates else _daily_ref(b, IDX).values):
            bad_d += 1
    return bad_h, bad_e, bad_d

if __name__ == '__main__':
    import time
    bh, be, bd = verify()
    print('hold mismatches %d, episode mismatches %d, daily mismatches %d' % (bh, be, bd))
    n = 29463
    rng = np.random.default_rng(1); a = np.zeros(n, bool); t = 0
    while t < n:
        w = rng.integers(5, 900); a[t:t + w] = rng.random() < 0.35; t += w
    IDX = pd.date_range('1946-01-31', periods=n, freq='D'); s = pd.Series(a, index=IDX)
    t0 = time.time(); [_episodes_ref(s) for _ in range(20)]; t1 = time.time()
    [episodes_np(a) for _ in range(20)]; t2 = time.time()
    print('episodes  old %.3f s  new %.4f s  speedup %.0fx' % (t1 - t0, t2 - t1, (t1 - t0) / max(t2 - t1, 1e-9)))
    t0 = time.time(); [_hold_ref(s, 270) for _ in range(20)]; t1 = time.time()
    [hold_np(a, 270) for _ in range(20)]; t2 = time.time()
    print('hold      old %.3f s  new %.4f s  speedup %.0fx' % (t1 - t0, t2 - t1, (t1 - t0) / max(t2 - t1, 1e-9)))
