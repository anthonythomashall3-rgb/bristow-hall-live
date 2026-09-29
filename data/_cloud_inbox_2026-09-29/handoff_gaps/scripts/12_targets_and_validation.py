"""Build gaps_targeted.csv (every gap week hunted, why, priority, expected first-print release, status) and
validation.csv (every parsed candidate vs the cloud table and current FRED)."""
import pandas as pd, datetime as dt
W = '/tmp/claude-0/-home-user/49f76bce-ebc7-5769-b106-ce7685453d86/scratchpad/collect/handoff_gaps'
g = pd.read_csv(f'{W}/gaps_all.csv')
f = pd.read_csv(f'{W}/found_prints.csv')
def expected_release(series, w):
    w = dt.date.fromisoformat(w)
    lag = 12 if series == 'claims' else 19
    if w >= dt.date(1993, 3, 1): lag = 5 if series == 'claims' else 12
    if dt.date(1975, 7, 1) <= w <= dt.date(1978, 12, 31): lag = 9 if series == 'claims' else 16
    if dt.date(1995, 12, 9) <= w <= dt.date(1996, 1, 6): return '1996-01-18 (catch-up release after the shutdown)'
    return (w + dt.timedelta(lag)).isoformat() + ' (approx.)'
def priority(r):
    y = r.year; w = r.week_ended; s = r.series
    if s == 'claims' and w in ('1976-05-22', '1977-07-02', '1977-07-30'): return 'P1 claims (Mac list)'
    if s in ('rate', 'level') and '1995-12-09' <= w <= '1995-12-30': return 'P1 Dec-1995 shutdown (Mac list)'
    if s in ('rate', 'level') and 1984 <= y <= 1988: return 'P2 1984-88 (Mac list core)'
    if s == 'rate' and (1975 <= y <= 1976 or y in (1993, 1994, 2003)): return 'P3 rate (Mac list: 1975-76 6wk, 1993 1wk, 1994 1wk, 2003 1wk)'
    if s == 'level_revised_only': return 'P5 level held only as a later restatement'
    return 'P4 cloud-only gap (probably filled on the Mac)'
g['priority'] = g.apply(priority, axis=1)
g['expected_first_print_release'] = [expected_release(s if s != 'level_revised_only' else 'level', w) for s, w in zip(g.series, g.week_ended)]
fk = f[f.print_kind == 'advance'].set_index(['series', 'week_ended'])
g['status'] = ['FOUND first print' if (s, w) in fk.index else 'missing' for s, w in zip(g.series, g.week_ended)]
g['found_value'] = [fk.loc[(s, w), 'value'] if (s, w) in fk.index else '' for s, w in zip(g.series, g.week_ended)]
g['found_source'] = [fk.loc[(s, w), 'source_url'] if (s, w) in fk.index else '' for s, w in zip(g.series, g.week_ended)]
hold = f[f.print_kind != 'advance'].set_index(['series', 'week_ended'])
g['other_holding'] = [f"{hold.loc[(s, w), 'value']} ({hold.loc[(s, w), 'print_kind']})" if (s, w) in hold.index else '' for s, w in zip(g.series, g.week_ended)]
g = g.sort_values(['priority', 'series', 'week_ended'])
g.to_csv(f'{W}/gaps_targeted.csv', index=False)
print(g.groupby(['priority', 'series']).size().to_string())
print(g[g.status != 'missing'].to_string())
print(g[g.other_holding != ''][['series', 'week_ended', 'other_holding']].to_string())
c = pd.read_csv(f'{W}/candidates_all.csv')
c = c[c.week_ended.notna()].copy()
def cmp(r):
    if pd.isna(r.cloud_value) or r.cloud_value == '': return 'no cloud value'
    return 'match' if float(r.value) == float(r.cloud_value) else f'differs ({float(r.value) - float(r.cloud_value):+g})'
c['vs_cloud'] = c.apply(cmp, axis=1)
c['vs_fred'] = [('' if pd.isna(fv) or fv == '' else f'{float(v) - float(fv):+g}') for v, fv in zip(c.value, c.fred_value)]
c[['raw_file', 'source_url', 'pub_date', 'series', 'week_ended', 'value', 'role', 'week_how', 'is_gap', 'cloud_value', 'vs_cloud', 'fred_value', 'vs_fred', 'sentence']].to_csv(f'{W}/validation.csv', index=False)
print(c.groupby(['role', 'vs_cloud']).size())
