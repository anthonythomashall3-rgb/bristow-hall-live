"""List weeks in the cloud first-print table (1975-2003) with no rate / no exact level / no claims first print.
Reads (read-only) the two cloud copies; writes gaps_all.csv and gaps_targeted.csv into the work dir."""
import pandas as pd, numpy as np, os
W = '/tmp/claude-0/-home-user/49f76bce-ebc7-5769-b106-ce7685453d86/scratchpad/collect/handoff_gaps'
B = '/home/user/bristow-hall-live/data/105_bristow_hall_system_2026-09-08/workspace'
early = pd.read_csv(f'{B}/s2/first_prints_early_1975_2002.csv')
live = pd.read_csv(f'{B}/cache/national_first_prints_1985_live.csv')
early['file'] = 's2/first_prints_early_1975_2002.csv'
live['file'] = 'cache/national_first_prints_1985_live.csv'
d = pd.concat([early, live[live.release_date > early.release_date.max()]], ignore_index=True)
d = d[d.release_date < '2004-01-15']
d['fills'] = d.fills.fillna('')

rows = []
start = pd.Timestamp('1975-07-26'); end = pd.Timestamp('2003-12-27')
weeks = pd.date_range(start, end, freq='W-SAT')
for w in weeks:
    ws = w.strftime('%Y-%m-%d')
    # claims
    c = d[d.ic_week_ended == ws]
    if w >= pd.Timestamp('1975-08-02'):
        if len(c) == 0 or c.icsa.isna().all():
            rows.append(('claims', ws, 'no row' if len(c) == 0 else 'icsa empty', ''))
        elif c.fills.str.contains('icsa from the current series').all():
            rows.append(('claims', ws, 'icsa from the current series (not a first print)', c.icsa.iloc[0]))
    u = d[d.iu_week_ended == ws]
    if w > pd.Timestamp('2003-12-20'):
        continue
    if len(u) == 0 or u.iur_sa.isna().all():
        rows.append(('rate', ws, 'no row' if len(u) == 0 else 'iur_sa empty', ''))
    if len(u) == 0 or u.iusa.isna().all():
        rows.append(('level', ws, 'no row' if len(u) == 0 else 'iusa empty', ''))
    else:
        uu = u[u.iusa.notna()]
        if uu.fills.str.contains('iusa from the current series').all():
            rows.append(('level', ws, 'iusa from the current series (not a first print)', uu.iusa.iloc[0]))
        elif (uu.iusa % 100000 == 0).all():
            rows.append(('level', ws, 'iusa a round 100,000 (rounded millions, not exact)', uu.iusa.iloc[0]))
        elif uu.fills.str.contains('the level is the print of|restatement').all():
            rows.append(('level_revised_only', ws, 'level is a later release\'s restatement, not the first print', uu.iusa.iloc[0]))
g = pd.DataFrame(rows, columns=['series', 'week_ended', 'why_gap', 'cloud_value'])
g['year'] = g.week_ended.str[:4].astype(int)
g.to_csv(f'{W}/gaps_all.csv', index=False)
print(g.groupby(['series', 'year']).size().unstack(0).fillna(0).astype(int).to_string())
print(g.series.value_counts())
