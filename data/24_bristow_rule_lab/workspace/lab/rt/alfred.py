"""ALFRED wide-vintage files (date x vintage) as they stood on any given day.

Files are the harvest's `<ID>_all_vintages.csv`: first column `date` (observation month),
then one column per vintage named `<ID>_YYYYMMDD` holding the value of every observation as
that vintage reported it.  `asof(id, day)` returns the series the latest vintage on or before
`day` carried - a true first-print history with no later revision in it.
"""
import os, glob, functools
import numpy as np, pandas as pd

VINT = '/home/claude/lab/rt/vint'   # ALFRED wide vintages, copied 2026-09-02 from the Mac harvest _v4_staging/vint

@functools.lru_cache(maxsize=None)
def wide(sid):
    p = f'{VINT}/{sid}_all_vintages.csv'
    df = pd.read_csv(p, index_col=0, parse_dates=True, low_memory=False)
    df = df.apply(pd.to_numeric, errors='coerce')
    vd = pd.to_datetime([c.split('_')[-1] for c in df.columns], format='%Y%m%d')
    df.columns = vd
    df = df.sort_index(axis=1)
    return df

def vintages(sid):
    return list(wide(sid).columns)

def asof(sid, day):
    """Series as the latest vintage dated <= `day` reported it (NaN rows dropped)."""
    df = wide(sid); day = pd.Timestamp(day)
    cols = df.columns[df.columns <= day]
    if len(cols) == 0: return None
    s = df[cols[-1]].dropna()
    s.index = pd.DatetimeIndex([pd.Timestamp(d.year, d.month, 1) for d in s.index])
    return s

def first_prints(sid):
    """The first-published value of every observation month (one number per month)."""
    df = wide(sid)
    out = {}
    for c in df.columns:
        col = df[c].dropna()
        for d, v in col.items():
            if d not in out: out[d] = v
    s = pd.Series(out).sort_index()
    s.index = pd.DatetimeIndex([pd.Timestamp(d.year, d.month, 1) for d in s.index])
    return s

def month_end(y, m):
    return pd.Timestamp(y, m, 1) + pd.offsets.MonthEnd(0)

if __name__ == '__main__':
    for sid in ('INDPRO', 'PAYEMS', 'UNRATE', 'PCEC96', 'MANEMP', 'AWHMAN', 'UNEMPLOY'):
        v = vintages(sid); s = asof(sid, '1975-06-30')
        print(sid, len(v), v[0].date(), v[-1].date(), 'asof 1975-06-30:', None if s is None else (s.index[-1].date(), round(float(s.iloc[-1]),2)))
