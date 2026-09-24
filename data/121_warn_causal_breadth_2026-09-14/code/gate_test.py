"""WOULD THE NESTED DESIGN KILL WARN BREADTH'S FALSE ALARMS?

WARN breadth beats the 2007 and 2024 deadlines and fires in five quiet periods - 2006, 2012, 2015, 2016
and 2026. The nested design Anthony's instruction implies is that a short-history source may only ever
ACCELERATE a call the core rule is already leaning towards; it may never open one by itself. If the core
was quiet in all five of those years, the gate removes all five and costs nothing at the three
recessions, and WARN becomes admissible as an accelerator.

The arming condition used here is the rule's own first ingredient rather than a new one: the Sahm gap,
the three-month average unemployment rate less its lowest three-month average of the preceding twelve
months, read on first prints. The rule's hub opens at 0.3667; armed is taken as a third of that, 0.12,
which is the smallest move that is not noise.
"""
import os, json, urllib.request, urllib.parse
import pandas as pd, numpy as np
ENV = os.path.expanduser('~/mnt/Onset Detector Data/onset-detector-new-2026-08-23/live_data/config/local.env')
if not os.path.exists(ENV):
    ENV = os.path.expanduser('~/Projects/Onset Detector Data/onset-detector-new-2026-08-23/live_data/config/local.env')
KEY = [l.split('=', 1)[1].strip().strip('"').strip("'") for l in open(ENV) if l.startswith('FRED_API_KEY=')][0]
q = urllib.parse.urlencode({'series_id': 'UNRATE', 'api_key': KEY, 'file_type': 'json'})
with urllib.request.urlopen(f'https://api.stlouisfed.org/fred/series/observations?{q}', timeout=120) as r:
    obs = json.loads(r.read())['observations']
u = pd.Series({pd.Timestamp(o['date']): float(o['value']) for o in obs if o['value'] != '.'}).sort_index()
m3 = u.rolling(3).mean()
sahm = m3 - m3.rolling(12).min()
ARM = 0.12
FA = ['2006-03-11', '2006-11-04', '2006-02-04', '2006-10-14', '2012-05-12', '2012-05-19', '2012-07-07',
      '2012-09-29', '2011-12-03', '2013-11-02', '2014-01-25', '2015-02-28', '2015-03-14', '2015-03-21',
      '2016-02-27', '2016-03-12', '2016-03-26', '2016-04-16', '2026-05-02', '2026-07-18']
HITS = {'2007-12': '2007-12-15', '2020-02': '2020-03-28', '2024-04': '2024-04-13'}
def gap_at(d):
    d = pd.Timestamp(d)
    # the latest month whose employment report was published on or before d: the month two before,
    # plus the first Friday convention, so month m is public in the first week of m+1
    prior = sahm[sahm.index <= d - pd.DateOffset(months=1)]
    return (prior.index[-1], float(prior.iloc[-1])) if len(prior) else (None, np.nan)
print('ARMING at a Sahm gap of', ARM, '(the hub opens at 0.3667)\n')
print('quiet-period firings:')
armed = 0
for d in sorted(set(FA)):
    mth, g = gap_at(d)
    a = g >= ARM
    armed += bool(a)
    print(f'  {d}  latest published month {mth.date() if mth is not None else "-"}  Sahm gap {g:+.2f}  {"ARMED" if a else "quiet - gate blocks"}')
print(f'\n  {armed} of {len(set(FA))} quiet firings survive the gate')
print('\nthe three recessions it catches:')
for pk, d in HITS.items():
    mth, g = gap_at(d)
    print(f'  {pk}  fires {d}  Sahm gap {g:+.2f}  {"ARMED - the gate lets it through" if g >= ARM else "BLOCKED - the gate would cost this call"}')
