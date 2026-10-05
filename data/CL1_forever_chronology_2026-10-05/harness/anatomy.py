# -*- coding: utf-8 -*-
"""CL1 anatomy: how a real-time daily reading behaves before recessions and outside them.

Populations (the user's 5 October 2026 standard: calls from 365 days before to 31 days after the end of the peak month):
  ONSET_i   [P_i - 365, P_i + 31]                     a reading here may call recession i
  BODY_i    (P_i + 31, T_i + 365]                     inside the recession and the year after its trough: neither a hit nor
                                                      a false alarm by itself (a re-arm rule decides whether a reading here
                                                      could open a new episode; reported separately as 'after-trough')
  QUIET     every other day from 1948-01-01           a reading here at the line is a false alarm
For a line L, a signal 'catches' i if it reaches L inside ONSET_i, and 'false-alarms' once per QUIET spell in which it
reaches L (spells more than 182 days apart are separate episodes, as in the program's W24 scorer).
"""
import numpy as np
import pandas as pd
from score import BOARD, ends

LEAD, LATE = 365, 31


def populations(days, board=None, lead=LEAD, late=LATE):
    P, T = ends(board)
    lab = pd.Series('QUIET', index=days)
    for i in range(len(P)):
        on = (days >= P[i] - pd.Timedelta(days=lead)) & (days <= P[i] + pd.Timedelta(days=late))
        body = (days > P[i] + pd.Timedelta(days=late)) & (days <= T[i] + pd.Timedelta(days=365))
        lab[body & (lab == 'QUIET')] = 'BODY%d' % i
        lab[on] = 'ONSET%d' % i
    lab[days < pd.Timestamp('1948-01-01')] = 'PRE'
    return lab


def episodes(mask, gap=182):
    """start days of spells where mask is True; a new spell needs > gap days since the last True day"""
    d = mask.index[mask.values]
    if not len(d): return []
    starts, last = [d[0]], d[0]
    for x in d[1:]:
        if (x - last).days > gap: starts.append(x)
        last = x
    return starts


def profile(x, lab, line=None):
    """x: daily reading; lab: populations. Returns per-recession first crossing (days vs P) and maxima, quiet maxima."""
    P, T = ends()
    out = {'onset': {}, 'quiet_max': np.nan, 'quiet_max_day': None}
    for i in range(len(P)):
        w = x[lab == 'ONSET%d' % i].dropna()
        r = {'max': float(w.max()) if len(w) else np.nan, 'first': None}
        if line is not None and len(w):
            hit = w[w >= line]
            if len(hit): r['first'] = (hit.index[0] - P[i]).days
        out['onset'][BOARD[i][0]] = r
    q = x[lab == 'QUIET'].dropna()
    if len(q):
        out['quiet_max'] = float(q.max()); out['quiet_max_day'] = str(q.idxmax().date())
    if line is not None:
        out['fa_spells'] = [str(d.date()) for d in episodes((x >= line) & (lab == 'QUIET'))]
    return out


def margin_table(signals, lab):
    """for each signal: the weakest recession's onset maximum against the highest quiet maximum (ratio and difference)"""
    rows = []
    for nm, x in signals.items():
        pr = profile(x, lab)
        mx = [v['max'] for v in pr['onset'].values()]
        worst = np.nanmin(mx) if np.isfinite(np.nanmin(mx)) else np.nan
        n_above = sum(1 for v in mx if np.isfinite(v) and v > pr['quiet_max'])
        rows.append(dict(signal=nm, quiet_max=pr['quiet_max'], quiet_max_day=pr['quiet_max_day'], weakest_onset=worst,
                         recessions_above_quiet_max=n_above, n_covered=sum(np.isfinite(mx))))
    return pd.DataFrame(rows).sort_values('recessions_above_quiet_max', ascending=False)
