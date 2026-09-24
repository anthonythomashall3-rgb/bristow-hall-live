#!/usr/bin/env python3
"""C1 (cyber / grid / payment outage) physical channel: EIA-930 daily electricity demand, lower-48 total, from 2015-07.
Published next day by the EIA (hourly operating data from balancing authorities), never revised in the sense a
survey is. Written as EIA930DEMAND (MWh/day) + a 7-day sum S7 and 28-day sum S28."""
import os, re, json, time, urllib.request, urllib.parse, pandas as pd
ROOT = os.path.expanduser('~/Projects/Onset Detector Data')
if not os.path.isdir(ROOT): ROOT = os.path.expanduser('~/mnt/Onset Detector Data')
ENV = os.path.join(ROOT, 'onset-detector-new-2026-08-23/live_data/config/local.env')
KEY = re.search(r'^EIA_API_KEY=([^\r\n]+)', open(ENV).read(), re.M).group(1).strip().strip('"').strip("'")
OUT = os.path.join(ROOT, '190_month_standard_and_hf_legs_2026-09-16/data')
rows, off = [], 0
while True:
    u = ('https://api.eia.gov/v2/electricity/rto/daily-region-data/data/?api_key=%s&frequency=daily&data[0]=value'
         '&facets[respondent][]=US48&facets[type][]=D&facets[timezone][]=Eastern&sort[0][column]=period&sort[0][direction]=asc&length=5000&offset=%d' % (KEY, off))
    req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0 (research collector)'})
    with urllib.request.urlopen(req, timeout=120) as r: d = json.load(r)
    chunk = d.get('response', {}).get('data', []); rows += chunk
    print('offset', off, 'got', len(chunk), flush=True)
    if len(chunk) < 5000: break
    off += 5000; time.sleep(1)
s = pd.Series([float(r['value']) for r in rows], index=pd.to_datetime([r['period'] for r in rows])).sort_index()
s = s[~s.index.duplicated(keep='last')]
def w(name, x):
    x = x.dropna(); pd.DataFrame({'date': x.index.strftime('%Y-%m-%d'), 'value': x.values}).to_csv(os.path.join(OUT, name + '.csv'), index=False)
    print(name, x.index.min().date(), '->', x.index.max().date(), len(x))
w('EIA930DEMAND', s); w('EIA930DEMAND_S7', s.rolling(7).sum()); w('EIA930DEMAND_S28', s.rolling(28).sum())
