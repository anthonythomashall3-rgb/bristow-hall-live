# -*- coding: utf-8 -*-
"""CL1 real-time engine: every reading is computed only from what was published on or before the day it is dated.

Data model
  A vintage table V has columns obs (the period the value describes, as a Timestamp), vintage (the day it was published)
  and value. A first-print table is the special case with one vintage per obs. A never-revised daily or weekly market
  series is a table whose vintage is the day after the observation (H.15 posts at 4:15 PM; the S&P close at 4 PM; the
  tool acts the next morning) unless a loader says otherwise.

Core operation
  rt_stat(V, f): for every distinct publication day r, take the series as known on r (each obs at its latest vintage
  <= r) and apply f to it. The result is a Series indexed by publication day: the real-time reading. Between publication
  days the reading stands; daily(s) forward-fills it onto the calendar.

Nothing here reads a recession date. Lines and chronologies live in other modules.
"""
import numpy as np
import pandas as pd

DAY0 = pd.Timestamp('1945-01-01')


def load_vintages(path, value_col='value'):
    V = pd.read_csv(path, parse_dates=['obs', 'vintage'])
    return V.rename(columns={value_col: 'value'})[['obs', 'vintage', 'value']].sort_values(['vintage', 'obs'])


def load_firstprint(path, obs='obs', rel='first_release', val='first_print'):
    F = pd.read_csv(path, parse_dates=[obs, rel])
    return pd.DataFrame({'obs': F[obs], 'vintage': F[rel], 'value': F[val]}).dropna().sort_values(['vintage', 'obs'])


def from_market(s, lag_days=1):
    """a never-revised series (index = observation day) -> vintage table, known lag_days later"""
    s = s.dropna()
    return pd.DataFrame({'obs': s.index, 'vintage': s.index + pd.Timedelta(days=lag_days), 'value': s.values})


def asof_iter(V):
    """yield (publication day, the series as known that day). The series keeps, for each obs, its latest vintage <= day."""
    V = V.sort_values(['vintage', 'obs'])
    cur = {}
    for r, g in V.groupby('vintage', sort=True):
        for o, v in zip(g['obs'].values, g['value'].values):
            cur[o] = v
        s = pd.Series(cur).sort_index()
        yield r, s


def rt_stat(V, f, start=None):
    """real-time reading: f(series as known on each publication day). f returns a float (or NaN)."""
    out = {}
    for r, s in asof_iter(V):
        if start is not None and r < start: continue
        try:
            out[r] = float(f(s))
        except Exception:
            out[r] = np.nan
    return pd.Series(out, dtype=float).sort_index()


def rt_stat_fast(V, f, start=None):
    """the same as rt_stat for tables where every vintage holds the complete series (ALFRED vintages): uses each
    vintage's own column directly"""
    out = {}
    for r, g in V.groupby('vintage', sort=True):
        if start is not None and r < start: continue
        s = pd.Series(g['value'].values, index=pd.DatetimeIndex(g['obs'].values)).sort_index()
        try:
            out[r] = float(f(s))
        except Exception:
            out[r] = np.nan
    return pd.Series(out, dtype=float).sort_index()


def daily(s, start='1947-01-01', end=None):
    """forward-fill a reading indexed by publication day onto every calendar day"""
    end = pd.Timestamp(end) if end is not None else s.index.max()
    idx = pd.date_range(start, end, freq='D')
    return s.sort_index().reindex(idx.union(s.index)).ffill().reindex(idx)


# ---- standard causal transforms of a series known on a day (s: obs-indexed Series) ----

def monthly(s):
    """put a monthly series on the calendar of months so that a month never collected (October 2025) is a gap, not a
    neighbour: three-month means then average the months that exist in the three calendar months"""
    s = s.dropna()
    if not len(s): return s
    return s.reindex(pd.date_range(s.index.min(), s.index.max(), freq='MS'))


def sahm_gap(s):
    """Sahm (2019): the latest 3-month mean minus the lowest 3-month mean of the prior 12 months (calendar months; a
    missing month is skipped inside its 3-month mean, as long as two of the three months exist)"""
    m = monthly(s).rolling(3, min_periods=2).mean()
    if m.notna().sum() < 13: return np.nan
    return m.iloc[-1] - m.iloc[-13:-1].min()


def rise_over_low(s, window, avg=1, log=False):
    """latest avg-period mean minus the lowest avg-period mean over the prior `window` periods (log points if log)"""
    x = np.log(s.dropna()) if log else s.dropna()
    m = x.rolling(avg).mean().dropna()
    if len(m) < window + 1: return np.nan
    return m.iloc[-1] - m.iloc[-window - 1:-1].min()


def fall_from_high(s, window, avg=1, log=True):
    x = np.log(s.dropna()) if log else s.dropna()
    m = x.rolling(avg).mean().dropna()
    if len(m) < window + 1: return np.nan
    return m.iloc[-window - 1:-1].max() - m.iloc[-1]


def change(s, k, log=False):
    x = np.log(s.dropna()) if log else s.dropna()
    if len(x) < k + 1: return np.nan
    return x.iloc[-1] - x.iloc[-1 - k]
