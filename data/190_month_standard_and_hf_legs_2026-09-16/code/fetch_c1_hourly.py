#!/usr/bin/env python3
"""Extend EIA930DEMAND back to July 2015 from the hourly US48 demand (the daily table begins 2019-01-01): hourly
values summed to days; days with fewer than 20 hours reported are dropped. Joined to the daily table from 2019."""
import os, re, json, time, urllib.request, pandas as pd
ROOT = os.path.expanduser('~/Projects/Onset Detector Data')
if not os.path.isdir(ROOT): ROOT = os.path.expanduser('~/mnt/Onset Detector Data')
ENV = os.path.join(ROOT, 'onset-detector-new-2026-08-23/live_data/config/local.env')
KEY = re.search(r'^EIA_API_KEY=([^\r\n]+)', open(ENV).read(), re.M).group(1).strip().strip('"').strip("'")
OUT = os.path.join(ROOT, '190_month_standard_and_hf_legs_2026-09-16/data')
rows, off = [], 0
while True:
    u = ('https://api.eia.gov/v2/electricity/rto/region-data/data/?api_key=%s&frequency=hourly&data[0]=value&facets[respondent][]=US48'
         '&facets[type][]=D&start=2015-07-01T00&end=2019-01-01T05&sort[0][column]=period&sort[0][direction]=asc&length=5000&offset=%d' % (KEY, off))
    req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0 (research collector)'})
    with urllib.request.urlopen(req, timeout=120) as r: d = json.load(r)
    chunk = d.get('response', {}).get('data', []); rows += chunk
    print('offset', off, 'got', len(chunk), flush=True)
    if len(chunk) < 5000: break
    off += 5000; time.sleep(0.5)
h = pd.Series([float(r['value']) if r['value'] is not None else float('nan') for r in rows], index=pd.to_datetime([r['period'] for r in rows], utc=True)).sort_index()
h = h[~h.index.duplicated(keep='last')].dropna()
# EIA hourly periods are UTC; the daily table is Eastern-day; convert to US/Eastern before summing
h.index = h.index.tz_convert('US/Eastern')
day = h.groupby(h.index.date).agg(['sum', 'count']); day.index = pd.to_datetime(day.index)
day = day[day['count'] >= 20]['sum']
old = pd.read_csv(os.path.join(OUT, 'EIA930DEMAND.csv')); o = pd.Series(old.value.values, index=pd.to_datetime(old.date))
ov = day.index.intersection(o.index)
print('overlap days', len(ov), 'mean ratio hourly-sum/daily-table', float((day[ov] / o[ov]).mean()) if len(ov) else None)
s = pd.concat([day[day.index < o.index.min()], o]).sort_index()
def w(name, x):
    x = x.dropna(); pd.DataFrame({'date': x.index.strftime('%Y-%m-%d'), 'value': x.values}).to_csv(os.path.join(OUT, name + '.csv'), index=False)
    print(name, x.index.min().date(), '->', x.index.max().date(), len(x))
w('EIA930DEMAND', s); w('EIA930DEMAND_S7', s.rolling(7).sum()); w('EIA930DEMAND_S28', s.rolling(28).sum())
