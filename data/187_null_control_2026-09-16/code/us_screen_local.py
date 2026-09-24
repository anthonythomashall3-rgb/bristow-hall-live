#!/usr/bin/env python3
"""The American screen, run here, with a placebo mode — and the placebo is the point.

WHY THIS FILE EXISTS. The 1969 screen has only ever been run against the true NBER chronology, and its
output has only ever been read as a count: 2,634 admissible configurations, then 71, then 190. A count
has no meaning without knowing what the same bar draws from a chronology that is WRONG. The Canadian
run made that concrete -- the identical screen on Canadian data produced 1,758 admissible
configurations, and the greedy cover over them reached 2008 and 2020 through poultry production. Four
hundred thousand conjunctions will always produce some winners.

So this runs the American screen twice over: once on the NBER peaks, and once on each of several
chronologies shifted whole by a fixed number of years. A shift preserves the number of peaks, their
spacing and the sample span, and destroys the economics. The surplus of the true run over the shifted
runs -- per peak, not in total -- is the part of the screen that is measuring anything.

PATHS. `screen_1969` is the original file and is not edited; its folder constants are replaced here so
the screen reads this workspace's copy of the collection rather than the device mount, where
background work does not advance between shell calls. The functions replaced for speed are the three
`fastscreen` checks against the originals, nothing else.
"""
import os, re, sys, json, time, warnings, numpy as np, pandas as pd, multiprocessing as mp
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
warnings.filterwarnings('ignore')
import screen_1969 as S

# `as_of` calls `rd_any` once per direction, so every channel's CSV was parsed four times.
_RD = {}
def _rd_cached(sid):
    if sid not in _RD:
        if len(_RD) > 400: _RD.clear()
        _RD[sid] = S._rd_any_orig(sid)
    v = _RD[sid]
    return None if v is None else v
from fastscreen import hold_np, episodes_np, daily_np

US = os.environ.get('US_DATA', '/mnt/user-data/outputs/us')
FP = os.environ.get('US_FP', '/mnt/user-data/outputs/fp2')
OUT = os.environ.get('US_OUT', '/mnt/user-data/outputs/us_out')
os.makedirs(OUT, exist_ok=True)
S.FOLDERS = [US]; S.VDIR = FP; S.OUT = OUT
S._rd_any_orig = S.rd_any
S.rd_any = _rd_cached


# `as_of`'s first-print branch walked the transformed series one observation at a time, looking each
# publication date up with `pb.get(t)` and boxing it with `pd.Timestamp`. That loop was 13,830 pandas
# scalar lookups for three channels and, once the scoring was vectorised, the single largest remaining
# cost. Reindexing the publication series onto the observation index does the same join in one step.
# `fp` is cached too: it was re-reading each first-print file once per direction, four times a channel.
_FP = {}
def _fp_cached(sid):
    if sid not in _FP:
        if len(_FP) > 400: _FP.clear()
        _FP[sid] = S._fp_orig(sid)
    return _FP[sid]

def _as_of_fast(sid, fn):
    s_, pb = S.fp(sid)
    if s_ is not None and len(s_) > 60:
        sp = S.spacing(s_); k = max(1, int(round(182.0 / max(sp, 1))))
        x = fn(s_, k).replace([np.inf, -np.inf], np.nan).dropna()
        a = pd.to_datetime(pb.reindex(x.index), errors='coerce')
        m = a.notna().values
        if int(m.sum()) > 60:
            y = pd.Series(x.values[m], index=pd.DatetimeIndex(a.values[m])).sort_index()
            return y[~y.index.duplicated(keep='first')], max(1, int(round(365.0 / max(sp, 1)))), 'firstprint'
    s_ = S.rd_any(sid)
    if s_ is None or len(s_) < 60: return None, None, None
    sp = S.spacing(s_); k = max(1, int(round(182.0 / max(sp, 1))))
    x = fn(s_, k).replace([np.inf, -np.inf], np.nan).dropna()
    if len(x) < 60: return None, None, None
    x = x.copy(); x.index = x.index + pd.Timedelta(days=S.lag_for(sp))
    return x, max(1, int(round(365.0 / max(sp, 1)))), 'current+lag'
S._fp_orig = S.fp; S.fp = _fp_cached
S._as_of_orig = S.as_of; S.as_of = _as_of_fast

def _daily(b): return daily_np(b, S.IDX)
def _hold(b, d): return hold_np(b, d)
def _episodes(fire, minexp=9): return list(S.IDX[episodes_np(fire, minexp)])
_TRUE_PK, _TRUE_TR = list(S.PK), list(S.TR)

def _apply(shift):
    """Install the (possibly shifted) chronology, in INTEGER DAY POSITIONS rather than Timestamps.

    The profile was unambiguous: with `episodes` and `hold` vectorised, essentially all remaining time
    was pandas datetime work -- boxing each episode position back into a Timestamp, then subtracting
    Timestamps thirteen times per configuration inside `score`. `datetimelike.__getitem__` alone was
    1.02 s of a 1.61 s run over three channels. The daily index is contiguous, so a position IS a day
    offset and every one of those subtractions is an integer subtraction. Nothing about the scoring
    changes; `verify_score.py` checks this against the Timestamp version on real channels.
    """
    S.daily, S.hold = _daily, _hold
    S.episodes = lambda fire, minexp=9: episodes_np(fire, minexp)      # positions, not Timestamps
    S.FOLDERS = [US]; S.VDIR = FP; S.OUT = OUT
    pk = [pd.Timestamp(p + pd.DateOffset(years=shift)) + pd.offsets.MonthEnd(0) for p in _TRUE_PK]
    tr = [pd.Timestamp(t + pd.DateOffset(years=shift)) + pd.offsets.MonthEnd(0) for t in _TRUE_TR]
    S.PK, S.TR = pk, tr
    n = len(S.IDX); d0 = S.IDX[0]
    pk_pos = [(int((p - d0).days), p.strftime('%Y-%m')) for p in pk]
    inside_arr = np.zeros(n, bool)
    for p, r in zip(pk, tr):
        i = max(0, int((p - d0).days)); j = min(n - 1, int((r - d0).days))
        if j >= i: inside_arr[i:j + 1] = True
    cr_lo = int((S.CRUNCH[0] - d0).days); cr_hi = int((S.CRUNCH[1] - d0).days)

    def inside(t): return bool(inside_arr[t]) if 0 <= t < n else False
    S.inside = inside

    def score(calls):
        a = np.asarray(calls, dtype=np.int64)
        used, leads = set(), {}
        for pp, key in pk_pos:
            j = int(np.searchsorted(a, pp, side='right')) - 1
            if j >= 0 and a[j] >= pp - 400:
                t = int(a[j]); leads[key] = t - pp; used.add(t)
        quiet = [t for t in a.tolist() if t not in used and not inside_arr[t]]
        crunch = [t for t in quiet if cr_lo <= t <= cr_hi]
        inwin = {k: v for k, v in leads.items() if -92 <= v <= -1}
        return (len(a), len(leads), len(inwin), len(quiet), len(crunch),
                json.dumps(inwin), json.dumps(leads))
    S.score = score

_SHIFT = 0
def _init():
    _apply(_SHIFT); S.init()

# `screen_1969.one` ends its admission test with `and '1969-12' in iw`, a literal key. Under a shifted
# chronology no such key can exist, so the placebo would have returned nothing and the comparison
# would have read as "the true chronology finds channels and a false one finds none" -- an artefact of
# a hard-coded string, not a result. This is the same function with the peak requirement lifted out;
# the caller applies the correct key for whatever shift it is running.
import itertools as _it
def one_any(sid):
    out = []
    for dname, dfn in S.DIRS.items():
        x, ny, how = S.as_of(sid, dfn)
        if x is None: continue
        for pq, pwy, phold in _it.product((95, 97), (10, 20), (180, 270)):
            Pb = S.hold(S.daily(S.over_q(x, pq, max(12, int(pwy * ny)))), phold)
            for (cn, cq, cwy, chow), Cb in S.CB.items():
                n, nh, ni, nq, nc, iw, al = S.score(S.episodes(Pb & Cb))
                if nq == 0 and ni > 0:
                    out.append(dict(proposer=sid, direction=dname, p_read=how, p_q=pq, p_win=pwy,
                                    p_hold=phold, confirmer=cn, c_read=chow, c_q=cq, c_win=cwy,
                                    n_fire=n, n_peak=nh, n_in=ni, n_quiet=nq, n_crunch=nc,
                                    inwindow=iw, all_leads=al))
    return out

def candidates():
    conf_ids = {v[0] for v in S.CONFS.values()}
    seen, cand = set(), []
    for f in S.FOLDERS:
        if not os.path.isdir(f): continue
        for fn_ in sorted(os.listdir(f)):
            if not fn_.endswith('.csv') or fn_.startswith('MANIFEST'): continue
            sid = fn_[:-4]
            if sid in seen or sid in conf_ids or S.LEAK.match(sid): continue
            seen.add(sid); cand.append(sid)
    return cand

def _pool_init(shift):
    global _SHIFT
    _SHIFT = shift; _apply(shift); S.init()

def run(shift, cand, tag, require_1969):
    t0 = time.time(); rows = []
    ncpu = max(1, os.cpu_count() or 2)
    with mp.Pool(ncpu, initializer=_pool_init, initargs=(shift,)) as pool:
        for i, res in enumerate(pool.imap_unordered(one_any, cand, chunksize=8)):
            rows += res
            if (i + 1) % 1000 == 0:
                print('   %s %d/%d, %d, %.1f min' % (tag, i + 1, len(cand), len(rows),
                                                     (time.time() - t0) / 60), flush=True)
    if require_1969:
        key = (pd.Timestamp('1969-12-01') + pd.offsets.MonthEnd(0) + pd.DateOffset(years=shift)).strftime('%Y-%m')
        rows = [r for r in rows if key in json.loads(r['inwindow'])]
    import collections
    per = collections.Counter()
    for r in rows:
        for p in json.loads(r['inwindow']): per[p] += 1
    D = pd.DataFrame(rows)
    D.to_csv(os.path.join(OUT, 'us_screen_shift%+d.csv' % shift), index=False)
    return len(rows), (D.proposer.nunique() if len(D) else 0), dict(sorted(per.items())), (time.time() - t0) / 60

if __name__ == '__main__':
    shifts = [int(z) for z in (sys.argv[1].split(',') if len(sys.argv) > 1 else ['0', '4', '7', '-5', '11'])]
    req = os.environ.get('REQUIRE_1969', '0') == '1'
    _apply(0)
    cand = candidates()
    print('American candidate channels %d, workers %d, require_1969=%s'
          % (len(cand), os.cpu_count(), req), flush=True)
    res = []
    for sh in shifts:
        n, ch, per, mins = run(sh, cand, '%+dy' % sh, req)
        res.append((sh, n, ch, json.dumps(per)))
        print('shift %+dy: %d configs over %d channels, %.1f min\n   %s' % (sh, n, ch, mins, per), flush=True)
    pd.DataFrame(res, columns=['shift_years', 'n_configs', 'n_channels', 'per_peak']).to_csv(
        os.path.join(OUT, 'us_placebo.csv'), index=False)
