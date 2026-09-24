# -*- coding: utf-8 -*-
"""THE DATA CENSUS (plan Step 5 item 15, Step 6 R1; 23 September 2026, collection 337). Every input the live tool reads, in one table:
the series, the publisher and the primary route, the backup route or substitute, the release schedule as the site carries it (day and
hour), what is in hand and through when, the vintage class, and whether a format check guards it. Compiled from the built state
(feeds, channels, the calendar the ops machinery publishes) and the tool's own declared substitutes; nothing is fetched. Run after the
build: python3 s2/data_census.py -> out/data_census.json and out/DATA-CENSUS.md. A row with no backup, no next day or no format check
is printed as a gap - the quarterly census is reading this list and closing the gaps."""
import os, sys, json, datetime
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKUPS = {   # the backup route or substitute for each feed, as declared in the tool (E5 channel rules, collections 329, 330, 336; the ops calendar rules)
    'Initial claims': "the states' ETA 539 weekly file with the Bureau's seasonal factors (s2/claims_substitute.py, exact where tested; collection 329)",
    'State insured': 'the advance state table of the weekly release PDF while the archive catches up',
    'Unemployment rate, factory': 'the Chicago Fed real-time unemployment forecast; ADP private payrolls (LSEG first prints) - declared, not automated',
    'Job openings': 'the Indeed Hiring Lab postings index, at most two months (s2/vacancy_bridge.py; collection 330)',
    'Housing starts': 'building permits beside starts (the pair reads either); the Census calendar',
    'Commercial paper': 'FRED DCPN30, DCPF1M and DTB3 (the Federal Reserve is not shut in a shutdown)',
    'S&P 500': 'the official FRED SP500 close when the chart feed fails (two independent quotes)',
    'Industrial production': 'the FRED current file of INDPRO (flagged: revised values), then the G.17 release text',
    'Federal funds target': 'the FOMC statement on federalreserve.gov (the rate carried from the last reading until then)',
    'State continued weeks': 'the ETA 5159 monthly report (slower), then the last month read',
    'State unemployment rates': "the states' ETA 539 insured-rate acceleration, at most two months (collection 336)",
    'Sahm rule': 'computed from the unemployment rate first prints if FRED SAHMREALTIME lapses',
    'Real GDP': 'GDPNow for the unprinted quarter; the BEA release text',
    'GDPNow': 'the Atlanta Fed page; the last printed quarter carried',
    'Search week': 'the claims week alone at any cell looser than (35, 20) (E34c); a second search source is not yet declared (R2)',
}
FORMAT_CHECKS = {   # where a changed format fails the build or is caught (q41, the loaders' own assertions)
    'Initial claims': 'q41 feed checks; the claims loader asserts the release week columns (45)', 'Job openings': 'walk39 asserts the vacancy first prints are not stale (>150 rows, within 8 months)',
    'Unemployment rate, factory': 'q41: the tile and the readings recomputed from the fetched files', 'State unemployment rates': 'state_breadth.py: 45-state coverage guard; q41 v3.72 checks',
    'S&P 500': 'q41: reading matches the readings table; two sources compared', 'Commercial paper': 'q41: the paper rates and their last printed day',
    'Real GDP': 'damage_dimensions.py: the vintage table read by column name; q41 v3.73 checks', 'GDPNow': 'the vintage appender names each vintage by its FRED date',
    'Industrial production': 'activity_opener.py: the vintage history appended and checked', 'Housing starts': 'q41 feed checks', 'Federal funds target': 'activity_opener.py: the FOMC calendar end alert (watchdog)',
    'State continued weeks': 'state539_live.py: the 539 file columns asserted', 'State insured': 'the page-8 parse validated against the advance table', 'Sahm rule': 'q41: the speed panel', 'Search week': "the collector's anchored window and the R2 shape guard (108/scripts/trends_live.py: a re-fetched window whose overlap deviates over 15 per cent is not appended; pull_log.csv)",
}
def main():
    S = json.load(open(os.path.join(HERE, 'out', 'bhs_state.json')))
    rows = []; gaps = []
    for f in S.get('feeds', []):
        key = next((k for k in BACKUPS if f['name'].startswith(k)), None)
        row = dict(feed=f['name'], series=f.get('ids'), source=f.get('source'), every=f.get('every'), through=f.get('through'), next=f.get('next'), link=f.get('url'),
                   value=f.get('value'), backup=BACKUPS.get(key), format_check=FORMAT_CHECKS.get(key), auto=f.get('auto'))
        for what, ok in (('backup', row['backup']), ('next release day', row['next']), ('format check', row['format_check']), ('link', row['link'])):
            if not ok: gaps.append('%s: no %s' % (f['name'][:50], what))
        rows.append(row)
    ch = [dict(channel=c['channel'], status=c['status'], last=c.get('last'), limit_days=c.get('limit_days'), substitute=c.get('substitute')) for c in S.get('channels', [])]
    out = dict(built_at=S.get('built_at'), version=S.get('version'), census_date=datetime.date.today().isoformat(), feeds=rows, channels=ch, gaps=gaps,
               note='every input the live tool reads, with its backup, schedule, holdings and format guard; the quarterly census reads this and closes the gaps (plan item 15, R1)')
    json.dump(out, open(os.path.join(HERE, 'out', 'data_census.json'), 'w'), indent=1)
    md = ['# The data census - %s (the tool %s, built %s)' % (out['census_date'], S.get('version'), S.get('built_at')), '',
          'Every input the live tool reads: the publisher and route, the backup or substitute, the schedule, what is in hand, and the guard on its format. Gaps are listed at the end.', '',
          '| feed | series | source | every | in hand through | next | backup or substitute | format guard |', '|---|---|---|---|---|---|---|---|']
    for r in rows: md.append('| %s | %s | %s | %s | %s | %s | %s | %s |' % (r['feed'][:70], r['series'], (r['source'] or '')[:80], (r['every'] or '')[:60], r['through'], r['next'], (r['backup'] or 'NONE')[:110], (r['format_check'] or 'NONE')[:90]))
    md += ['', '## The channels (E5: current, stale, substitute, dark)', '', '| channel | status | last | limit (days) | substitute |', '|---|---|---|---|---|']
    for c in ch: md.append('| %s | %s | %s | %s | %s |' % (c['channel'][:70], c['status'], c['last'], c['limit_days'], (c['substitute'] or '')[:100]))
    md += ['', '## Gaps', ''] + (['- ' + g for g in gaps] or ['- none'])
    open(os.path.join(HERE, 'out', 'DATA-CENSUS.md'), 'w').write('\n'.join(md) + '\n')
    print('data census: %d feeds, %d channels, %d gaps%s' % (len(rows), len(ch), len(gaps), (': ' + '; '.join(gaps)) if gaps else ''))
    return 0
if __name__ == '__main__': sys.exit(main())
