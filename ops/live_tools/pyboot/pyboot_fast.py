# -*- coding: utf-8 -*-
"""THE STATE CHRONOLOGY'S parts(), ON THE ARRAYS (1167b, 25 Nov 2026; Anthony: "under 3 minutes of data releases"). No AI.

The v4 code path (state_chronology_v4_growth_cycle_a198_1032.py and the stress map's State layer, stress_map_v3_1_1052.py, which copies
it) grades a period month by month with

    def parts(UR, base, Gq, p, m):
        ex = (UR[(UR.index >= p) & (UR.index <= m)] - base).clip(lower=0); L = dd.labour_score(float(ex.max()), float(ex.sum())) if len(ex) else 0.0
        return L, dd.output_dimension(Gq, p, m), (float(ex.max()) if len(ex) else 0.0)

called 35,000 times a run (71 of the State layer's 110 profiled seconds), nearly all of it pandas' own overhead on 1- to 600-row
selections. parts() below is the same arithmetic on the arrays: the months p..m by binary search on the sorted dates (the same rows the
two comparisons select), the same subtraction, clip and sum (numpy's, which pandas itself calls), the same labour_score; and
output_dimension's own steps (its quarters by binary search, the peak-to-trough pass of sitecustomize.py, the same rounding). Anything
else - an unsorted, repeated or missing date, a missing value, a date that is not a plain Timestamp, a module whose functions are not the
code read on 25 Nov 2026 (SHA-256 below) - runs the original line. ops/live_tools/pyboot/run_rewritten.py puts it in place of the
scripts' own parts() (a one-line call, same line count), only in the files whose SHA-256 it knows."""
import hashlib, inspect
import numpy as np
import pandas as pd

_SHA = {'output_dimension': 'e85283ba6724f0f384db2f1a5d0718e633053270a61708198714a5ce338f2697',
        'qstart': '520491034142f9a91b1477bcfa12b972a174793c585967f9a525fd68d694cfd8',
        'pt_and_cum': '7b06690898f1d617d9cc2ed81cd2489bd3263e50fed6236eb965dcc2d1f97fe9',
        'score2': '71bb1309ef051b19bc0a6efa6640e63beb3fea58d0a4ad5926413dfdb3b82e3d',
        'labour_score': 'e0b43671b230a801e12310e726beed4818213c0643aa341993c31cefbd7e7e37'}
_DEP = {'u_depth': 21.7, 'u_pm': 528.3, 'gdp_pt': 26.3, 'gdp_cum': 298.5, 'ip_pt': 53.6, 'ip_cum': 1413.0}
_READY = {}
STATS = {'fast': 0, 'orig': 0}


def _ready(dd):
    """the damage module is the code read on 25 Nov 2026 (each function's source, the original pt_and_cum where sitecustomize replaced it)"""
    k = id(dd)
    if k not in _READY:
        try:
            ok = dict(getattr(dd, 'DEP', {})) == _DEP
            for n, h in _SHA.items():
                f = getattr(dd, n); f = getattr(f, '_bhs_orig', f)
                ok = ok and hashlib.sha256(inspect.getsource(f).encode()).hexdigest() == h
        except Exception:
            ok = False
        _READY[k] = ok
    return _READY[k]


def _orig(UR, base, Gq, p, m, dd):
    STATS['orig'] += 1
    ex = (UR[(UR.index >= p) & (UR.index <= m)] - base).clip(lower=0); L = dd.labour_score(float(ex.max()), float(ex.sum())) if len(ex) else 0.0
    return L, dd.output_dimension(Gq, p, m), (float(ex.max()) if len(ex) else 0.0)


def _plain(idx):
    return isinstance(idx, pd.DatetimeIndex) and idx.tz is None and idx.is_monotonic_increasing and idx.is_unique and not idx.hasnans


def _ts(x):
    return isinstance(x, pd.Timestamp) and x.tz is None and x is not pd.NaT


def _qstart(t):
    return pd.Timestamp(t.year, 3 * ((t.month - 1) // 3) + 1, 1)


def _ptcum(vals):
    """sitecustomize.py's pt_and_cum without not_before (bit-identical to damage_dimensions_live_v376.pt_and_cum on a sorted window)"""
    n = len(vals)
    start = np.arange(1, n + 1)
    sm = np.empty(n + 1); sm[n] = np.inf; sm[:n] = np.minimum.accumulate(vals[::-1])[::-1]
    has = start < n
    if not has.any(): return 0.0, 0.0
    lm = np.where(has, sm[np.minimum(start, n)], np.nan)
    f = np.where(has, (vals - lm) / vals * 100.0, -np.inf)
    i = int(np.argmax(f)); fi = f[i]
    if not fi > 0.0: return 0.0, 0.0
    x = (vals[i] - vals[start[i]:]) / vals[i] * 100.0
    return fi, float(np.where(x < 0, 0.0, x).sum())


def _output_dimension(dd, G, call, through):
    """damage_dimensions_live_v376.output_dimension(G, call, through) with no nowcast, on the arrays"""
    q0 = _qstart(call) - pd.DateOffset(months=3); q1 = _qstart(through)
    gi = G.index; j0 = int(gi.searchsorted(q0, side='left')); j1 = int(gi.searchsorted(q1, side='right'))
    n = max(j1 - j0, 0)
    if n < 2:
        return dict(pt=0.0, cum=0.0, score=0.0, quarters=int(n), nowcast=False, through=(str(gi[j1 - 1].date()) if n else None))
    vals = G.to_numpy()[j0:j1]
    pt, cum = _ptcum(vals)
    return dict(pt=round(float(pt), 4), cum=round(float(cum), 4), score=round(float(dd.score2(pt, cum, dd.DEP["gdp_pt"], dd.DEP["gdp_cum"])), 4),
                quarters=int(n), nowcast=False, through=str(gi[j1 - 1].date()))


def parts(UR, base, Gq, p, m, dd):
    """the scripts' parts(UR, base, Gq, p, m): (labour score, output dimension, highest excess)"""
    try:
        if not (_ready(dd) and _ts(p) and _ts(m) and isinstance(UR, pd.Series) and isinstance(Gq, pd.Series)
                and UR.dtype == np.float64 and Gq.dtype == np.float64 and _plain(UR.index) and _plain(Gq.index) and type(base) is float):
            return _orig(UR, base, Gq, p, m, dd)
        uv = UR.to_numpy(); gv = Gq.to_numpy()
        if np.isnan(uv).any() or np.isnan(gv).any():
            return _orig(UR, base, Gq, p, m, dd)
        i0 = int(UR.index.searchsorted(p, side='left')); i1 = int(UR.index.searchsorted(m, side='right'))
    except Exception:
        return _orig(UR, base, Gq, p, m, dd)
    STATS['fast'] += 1
    if i1 > i0:
        ex = uv[i0:i1] - base
        ex = np.where(ex >= 0, ex, 0.0)
        mx = float(ex.max()); L = dd.labour_score(mx, float(ex.sum()))
    else:
        mx = 0.0; L = 0.0
    return L, _output_dimension(dd, Gq, p, m), mx
