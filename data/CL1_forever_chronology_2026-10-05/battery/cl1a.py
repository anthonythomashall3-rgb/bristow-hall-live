# -*- coding: utf-8 -*-
"""CL1-A, exactly as pre-registered (doc/PREREG-CL1-A-2026-10-05.md, commit 8b3fd1d): twelve designs, one closer.
T1 = frozen lines on the whole quiet record (G1); T2 = every line from quiet days at least three years old (causal).
Run: python3 battery/cl1a.py   ->  out/cl1a_results.json and a printed table."""
import json, os, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, 'harness')); sys.path.insert(0, os.path.join(HERE, 'panel'))
import score  # noqa: E402

FAM = ['F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8']
LABOR = ['F1', 'F2', 'F3']
LAG_Q = 1095          # quiet days must be at least three years old (T2)
MIN_Q = 3652          # ten quiet years before a family is read (T2)
REARM = 182
CLOSE_DROP, CLOSE_WEEKS, CLOSE_MIN_DAYS = 0.105, 4, 91

DESIGNS = {  # name: (kind, k, h)
    'A1': ('all', 2, 1), 'A2': ('all', 2, 14), 'A3': ('all', 3, 1), 'A4': ('all', 3, 14),
    'A5': ('labor+1', 2, 1), 'A6': ('labor+1', 2, 14), 'A7': ('labor', 1, 1), 'A8': ('labor', 1, 14),
    'A9': ('labor', 2, 1), 'A10': ('labor', 2, 14), 'A11': ('all', 1, 1), 'A12': ('all', 1, 14)}


def load_panel():
    return pd.read_parquet(os.path.join(HERE, 'private', 'panel', 'families_daily.parquet'))


def quiet_mask(days, lead=365, after=365):
    P, T = score.ends()
    q = np.asarray(days >= pd.Timestamp('1948-01-01'))
    for p, t in zip(P, T):
        q &= ~np.asarray((days >= p - pd.Timedelta(days=lead)) & (days <= t + pd.Timedelta(days=after)))
    return q


def ratios_frozen(P, q):
    R = pd.DataFrame(index=P.index)
    for f in FAM:
        x = P[f]; xq = x[q].dropna()
        med, rec = float(xq.median()), float(xq.max())
        R[f] = (x - med) / (rec - med)
    return R


def ratios_causal(P, q):
    """line parameters re-set on the first day of every month from quiet days at least LAG_Q days old"""
    days = P.index; R = pd.DataFrame(index=days, columns=FAM, dtype=float)
    starts = pd.date_range(days[0], days[-1], freq='MS')
    for f in FAM:
        x = P[f].values; out = np.full(len(days), np.nan)
        for k, m0 in enumerate(starts):
            m1 = starts[k + 1] if k + 1 < len(starts) else days[-1] + pd.Timedelta(days=1)
            cut = m0 - pd.Timedelta(days=LAG_Q)
            sel = q & np.asarray(days <= cut) & np.isfinite(x)
            if sel.sum() < MIN_Q: continue
            xs = x[sel]; med, rec = np.median(xs), xs.max()
            if rec <= med: continue
            j = np.asarray((days >= m0) & (days < m1))
            out[j] = (x[j] - med) / (rec - med)
        R[f] = out
    return R


def breaches(R, h):
    B = (R >= 1.0 - 1e-12).astype(float).where(R.notna(), 0.0)
    if h > 1: B = B.rolling(h, min_periods=h).min().fillna(0.0)
    return B.astype(bool)


def opener(B, kind, k):
    if kind == 'all': return B[FAM].sum(axis=1) >= k
    if kind == 'labor': return B[LABOR].sum(axis=1) >= k
    if kind == 'labor+1':
        lab = B[LABOR].any(axis=1); tot = B[FAM].sum(axis=1)
        return lab & (tot >= k)
    raise ValueError(kind)


def run_tool(open_cond, rel, days):
    """the state machine. Closed: open on the first day the opener holds, unless fewer than REARM days have passed since
    the last close. Open: on each claims release day at least CLOSE_MIN_DAYS after the opening, close if the last
    CLOSE_WEEKS releases of the 4-week mean all stand at least CLOSE_DROP (log) below its highest release since the opening."""
    rel_days = rel.index; rel_vals = rel.values; ridx = {d: i for i, d in enumerate(rel_days)}
    eps, state, t0, lo, last_close = [], False, None, None, None
    oc = open_cond.values
    for i, d in enumerate(days):
        if not state:
            if last_close is not None and (d - last_close).days < REARM: continue
            if oc[i]:
                state, t0 = True, d
                lo = int(np.searchsorted(rel_days.values, np.datetime64(d), side='left'))
            continue
        j = ridx.get(d)
        if j is None or (d - t0).days < CLOSE_MIN_DAYS or j - CLOSE_WEEKS + 1 < lo: continue
        M = np.nanmax(rel_vals[lo:j + 1])
        last = rel_vals[j - CLOSE_WEEKS + 1:j + 1]
        if np.isfinite(M) and np.all(np.isfinite(last)) and np.all(np.log(last) <= np.log(M) - CLOSE_DROP):
            eps.append((t0, d)); state, t0, last_close = False, None, d
    if state: eps.append((t0, None))
    return eps


def main():
    P = load_panel()
    days = P.index
    q = quiet_mask(days)
    ic4 = P['IC4']
    rel = ic4[ic4.ne(ic4.shift())].dropna()        # the claims release days (the 4-week mean changes on each)
    out = {}
    for tag, R in [('T1', ratios_frozen(P, q)), ('T2', ratios_causal(P, q))]:
        R.to_parquet(os.path.join(HERE, 'private', 'panel', 'ratios_%s.parquet' % tag))
        for nm, (kind, k, h) in DESIGNS.items():
            B = breaches(R, h)
            eps = run_tool(opener(B, kind, k), rel, days)
            res = {}
            for wn, lead in [('W12', 365), ('W24', 730), ('W4', 122)]:
                s = score.score(eps, lead=lead)
                res[wn] = dict(hits=s['hits'], late=s['late'], missed=s['missed'], fa=s['fa'], troughs=s['trough_hits'],
                               rows=s['rows'], fa_list=s['fa_list'])
            out['%s %s' % (tag, nm)] = dict(episodes=[(str(a.date()), None if b is None else str(b.date())) for a, b in eps], **res)
            w = res['W12']
            print('%s %-4s %-8s k=%d h=%-2d  W12: %2d/13 hit, %d late, %d missed, FA %2d, troughs %2d/13 | W4 %2d/13 FA %2d'
                  % (tag, nm, kind, k, h, w['hits'], w['late'], w['missed'], w['fa'], w['troughs'], res['W4']['hits'], res['W4']['fa']))
    json.dump(out, open(os.path.join(HERE, 'out', 'cl1a_results.json'), 'w'), indent=1, default=str)
    return out


if __name__ == '__main__':
    main()
