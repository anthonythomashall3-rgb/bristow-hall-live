# -*- coding: utf-8 -*-
"""SECOND SOURCES FOR THE RULE'S FEEDS THAT HAD ONLY A CACHE BEHIND THEM (collection 1043, 11 November 2026; Anthony: "make sure
that all of our sources have backups wherever possible"). Each function reads the PUBLISHER ITSELF, not FRED:

  effr_monthly()        the effective federal funds rate, monthly average of the daily rate over every calendar day (a weekend or
                        holiday carries the last business day's rate: the H.15 convention FRED FEDFUNDS follows) - New York Fed
  treasury_monthly(c)   the 10-year / 1-year constant-maturity yield, monthly average of business days (FRED GS10 / GS1) - Treasury
  bls_series(sid)       the newest labour prints - the Bureau of Labor Statistics API

Nothing here is used while FRED answers. Standard library + pandas; transport is curl, as in the rest of the chain.
Tested equal to the primary on history by code/test_1043.py before any use."""
import io, json, subprocess, datetime
import pandas as pd

def _curl(url, m=40, post=None):
    cmd = ['curl', '-sSL', '--http1.1', '-m', str(m), '-A', 'Mozilla/5.0']
    if post is not None: cmd += ['-X', 'POST', '-H', 'Content-Type: application/json', '-d', post]
    r = subprocess.run(cmd + [url], capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip(): raise RuntimeError('curl rc %s for %s' % (r.returncode, url[:60]))
    return r.stdout

def effr_daily(start='2016-03-01', end=None):
    end = end or datetime.date.today().isoformat()
    d = json.loads(_curl('https://markets.newyorkfed.org/api/rates/unsecured/effr/search.json?startDate=%s&endDate=%s' % (start, end)))
    rows = {pd.Timestamp(x['effectiveDate']): float(x['percentRate']) for x in d['refRates'] if x.get('type') == 'EFFR' and x.get('percentRate') is not None}
    s = pd.Series(rows).sort_index()
    if len(s) < 20: raise RuntimeError('EFFR: too few days')
    return s

def effr_monthly(start='2016-03-01', asof=None):
    """complete months only: a month is complete once a business day of the NEXT month is in hand"""
    s = effr_daily(start)
    cal = s.reindex(pd.date_range(s.index[0], s.index[-1], freq='D')).ffill()
    m = cal.groupby(cal.index.to_period('M')).mean()
    cnt = cal.groupby(cal.index.to_period('M')).size()
    last = s.index[-1].to_period('M')
    full = [p for p in m.index if cnt[p] == p.days_in_month and p < last]
    out = m.loc[full].round(2); out.index = [p.to_timestamp() for p in out.index]
    return out

def treasury_daily(year):
    txt = _curl('https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/%d/all?type=daily_treasury_yield_curve&field_tdr_date_value=%d&page&_format=csv' % (year, year), m=60)
    df = pd.read_csv(io.StringIO(txt))
    if 'Date' not in df.columns or '10 Yr' not in df.columns or '1 Yr' not in df.columns: raise RuntimeError('Treasury: unexpected columns %s' % list(df.columns)[:6])
    df.index = pd.to_datetime(df['Date']); return df.sort_index()

def treasury_monthly(col, years):
    """col '10 Yr' or '1 Yr'; complete months only (a later month's day is in hand)"""
    d = pd.concat([treasury_daily(y) for y in years]); d = d[~d.index.duplicated()].sort_index()
    s = pd.to_numeric(d[col], errors='coerce').dropna()
    m = s.groupby(s.index.to_period('M')).mean()
    m = m[m.index < s.index[-1].to_period('M')].round(2); m.index = [p.to_timestamp() for p in m.index]
    return m

BLS_ID = {'UNRATE': 'LNS14000000', 'PAYEMS': 'CES0000000001', 'UNEMPLOY': 'LNS13000000', 'LNS13023621': 'LNS13023621', 'JTSJOL': 'JTS000000000000000JOL'}
def bls_series(sids, key=None, years=3):
    y = datetime.date.today().year
    body = {'seriesid': [BLS_ID[s] for s in sids], 'startyear': str(y - years + 1), 'endyear': str(y)}
    if key: body['registrationkey'] = key
    d = json.loads(_curl('https://api.bls.gov/publicAPI/v2/timeseries/data/', post=json.dumps(body)))
    if d.get('status') != 'REQUEST_SUCCEEDED': raise RuntimeError('BLS API: %s' % d.get('status'))
    inv = {v: k for k, v in BLS_ID.items()}; out = {}
    for srs in d['Results']['series']:
        obs = {}
        for o in srs['data']:
            if o['period'][:1] == 'M' and o['period'] != 'M13':
                try: obs[pd.Timestamp(int(o['year']), int(o['period'][1:]), 1)] = float(str(o['value']).replace(',', ''))
                except ValueError: pass
        if obs: out[inv[srs['seriesID']]] = pd.Series(obs).sort_index()
    return out

# ---------------------------------------------------------------- the two entry points the chain calls (only when FRED did not answer)
def monthly_second(series):
    """complete months of FEDFUNDS / GS10 / GS1 from the publisher; None for a series with no second publisher (Moody's Baa)"""
    t = datetime.date.today()
    if series == 'FEDFUNDS': return effr_monthly(start=(t - datetime.timedelta(days=500)).isoformat())
    if series in ('GS10', 'GS1'): return treasury_monthly('10 Yr' if series == 'GS10' else '1 Yr', [t.year - 1, t.year])
    return None

def extend_cache(series, cache_csv):
    """append to a c1021 monthly cache (columns date, v) the complete months it lacks; returns the months added"""
    m = monthly_second(series)
    if m is None: return []
    c = pd.read_csv(cache_csv, parse_dates=['date'])
    new = m[m.index > c['date'].max()]
    if not len(new): return []
    pd.concat([c, pd.DataFrame({'date': new.index, 'v': new.values})], ignore_index=True).to_csv(cache_csv, index=False)
    return [d.strftime('%Y-%m') for d in new.index]

def bls_vintage_column(old, b):
    """the newest vintage as the BLS publishes it today: the last vintage in hand, with every month the BLS returns overlaid"""
    new = old.reindex(old.index.union(b.index)).sort_index(); new.loc[b.index] = b.values
    return new

def append_bls_vintage(path, series, b, day, backup=None):
    """append <series>_<day> to an ALFRED all-vintages table when the BLS carries a month the table lacks; returns the column name or None.
    The column is named by the day it was read (never earlier than the release), so it can only be causal-late, never early."""
    tab = pd.read_csv(path, index_col=0); tab.index = pd.to_datetime(tab.index)
    old = pd.to_numeric(tab[tab.columns[-1]], errors='coerce').dropna()
    if b is None or not len(b) or b.index[-1] <= old.index[-1]: return None
    col = '%s_%s' % (series, str(day).replace('-', ''))
    if col in tab.columns: return None
    new = bls_vintage_column(old, b)
    if backup: backup(path)
    tab = tab.reindex(tab.index.union(new.index)).sort_index(); tab = pd.concat([tab, new.reindex(tab.index).rename(col)], axis=1)
    tab.index.name = 'date'; tab.to_csv(path, na_rep='')
    return col
