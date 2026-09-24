"""Score the walked record of walk 94 (v3.55) on the calendar-month standard chosen by Anthony on 16 Sep 2026:
a call is on time if it falls in the peak month or in one of the two months before it; late if after the peak month.
Peaks: NBER 1969-2020; 2024 by Paper 1 (Hall & Bristow): peak April 2024."""
import json, pandas as pd, os
ROOT = os.path.expanduser('~/Projects/Onset Detector Data')
if not os.path.isdir(ROOT): ROOT = os.path.expanduser('~/mnt/Onset Detector Data')
rec = json.load(open(os.path.join(ROOT, '189_walk_from_1948_2026-09-16/out/v355/v355_record.json')))['walk94']
PEAKS = ['1969-12', '1973-11', '1980-01', '1981-07', '1990-07', '2001-03', '2007-12', '2020-02', '2024-04']
opens = [pd.Timestamp(d) for d, k, m, L in rec if k == 'OPEN']; legs = [L for d, k, m, L in rec if k == 'OPEN']
rows = []
for pk, d, L in zip(PEAKS, opens, legs):
    p = pd.Period(pk, 'M'); c = d.to_period('M'); months = (p - c).n
    days_end = (d - p.to_timestamp(how='end').normalize()).days
    days_start = (d - p.to_timestamp(how='start')).days
    rows.append(dict(peak=pk, call=d.strftime('%Y-%m-%d'), leg=L, months_early=months, days_to_month_end=days_end, days_to_month_start=days_start,
                     verdict=('LATE' if months < 0 else ('ok' if months <= 2 else 'TOO EARLY'))))
df = pd.DataFrame(rows); print(df.to_string(index=False))
n_late = int((df.months_early < 0).sum()); n_early = int((df.months_early > 2).sum())
print('\nlate calls:', n_late, '| calls more than two months early:', n_early, '| false alarms in the walked record: 0 (walk 94 diary, 1962-2026)')
df.to_csv(os.path.join(ROOT, '190_month_standard_and_hf_legs_2026-09-16/out/walk94_month_standard.csv'), index=False)
