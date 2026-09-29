#!/usr/bin/env python3
"""Build MANIFEST.csv: one row per tidy series. first_obs/last_obs/n_obs are read from the VALUES
(non-missing), pct_repeated_values = % of observations equal to the immediately preceding observation
(in date order). Nothing here is typed by hand except source/URL/revision labels.
"""
import os, glob, csv
import pandas as pd

W = '/tmp/claude-0/-home-user/49f76bce-ebc7-5769-b106-ce7685453d86/scratchpad/collect/new_candidates'
T = os.path.join(W, 'tidy'); rows = []

def add(source, url, series, freq, dates, values, tidy_file, raw_file, revision, notes=''):
    if values is None:        # holdings without parsed values (e.g. PDFs): count dates only, no repeat stat
        s = pd.DataFrame({'d': sorted(set(pd.Series(dates).astype(str)))}); rep = float('nan')
    else:
        s = pd.DataFrame({'d': pd.Series(dates).astype(str).values,
                          'v': pd.to_numeric(pd.Series(values), errors='coerce').values}).dropna()
        s = s.sort_values('d')
        rep = float((s['v'].diff() == 0).sum()) / max(len(s) - 1, 1) * 100 if len(s) > 1 else float('nan')
    rows.append(dict(source=source, url=url, series=series, frequency=freq,
                     first_obs=s['d'].iloc[0] if len(s) else '', last_obs=s['d'].iloc[-1] if len(s) else '',
                     n_obs=len(s), pct_repeated_values=round(rep, 2), revision_status=revision,
                     tidy_file=os.path.relpath(tidy_file, W), raw_file=raw_file, notes=notes))

# --- SPF
PF = 'https://www.philadelphiafed.org/-/media/FRBP/Assets/Surveys-And-Data/survey-of-professional-forecasters/'
f = os.path.join(T, 'spf', 'spf_recess_mean.csv'); d = pd.read_csv(f)
q = d['YEAR'].astype(str) + 'Q' + d['QUARTER'].astype(str)
for k in ['RECESS1', 'RECESS2', 'RECESS3', 'RECESS4', 'RECESS5']:
    add('Philadelphia Fed SPF', PF + 'historical-data/prob.xlsx', 'mean ' + k + ' (prob. of real GNP/GDP decline)',
        'quarterly (survey)', q, d[k], f, 'raw/spf/prob.xlsx', 'real time by construction (survey, never revised)',
        'dated by survey quarter; release dates known from 1990Q2 (spf_release_dates.csv); earlier assumed quarter-end')
f = os.path.join(T, 'spf', 'spf_recess_median_n.csv'); d = pd.read_csv(f)
q = d['YEAR'].astype(str) + 'Q' + d['QUARTER'].astype(str)
for k in ['median_RECESS1', 'median_RECESS2', 'share_ge50_RECESS1', 'n_resp_RECESS1']:
    add('Philadelphia Fed SPF (computed from micro data)', PF + 'historical-data/SPFmicrodata.xlsx', k,
        'quarterly (survey)', q, d[k], f, 'raw/spf/SPFmicrodata.xlsx', 'real time by construction')
f = os.path.join(T, 'spf', 'spf_mean_level_long.csv'); d = pd.read_csv(f)
for sh in ['UNEMP', 'EMP', 'INDPROD', 'HOUSING', 'RGDP', 'CPROF']:
    x = d[(d['sheet'] == sh) & (d['field'] == sh + '2')]
    add('Philadelphia Fed SPF', PF + 'historical-data/meanLevel.xlsx', 'mean %s2 (current-quarter nowcast)' % sh,
        'quarterly (survey)', x['YEAR'].astype(str) + 'Q' + x['QUARTER'].astype(str), x['value'], f,
        'raw/spf/meanLevel.xlsx', 'real time by construction', 'all horizons 1-6/A-D in the long file')

# --- RTDSM first prints
RB = 'https://www.philadelphiafed.org/-/media/FRBP/Assets/Surveys-And-Data/real-time-data/data-files/xlsx/'
sm = pd.read_csv(os.path.join(T, 'rtdsm', 'rtdsm_vintage_summary.csv'))
for _, r in sm.iterrows():
    f = os.path.join(T, 'rtdsm', '%s_%s_firstprint.csv' % (r['variable'], r['kind']))
    d = pd.read_csv(f)
    g = d[~d['is_backfill']]
    add('Philadelphia Fed RTDSM', RB + os.path.basename(r['file']), '%s first print (%s)' % (r['variable'], r['kind']),
        'monthly obs' if r['kind'].endswith('Md') else 'quarterly obs', g['obs'], g['first_value'], f, r['file'],
        'full vintage history (%d vintages %s-%s)' % (r['n_vintages'], r['first_vintage'], r['last_vintage']),
        'genuine first prints only (first published within 130/200 days of obs); full matrix in %s_%s_long.csv.gz; '
        'deep history in first vintage from %s' % (r['variable'], r['kind'], r['first_obs']))

# --- UMich
U = 'https://data.sca.isr.umich.edu/data-archive/mine.php (POST table=all, qorm=M|Q, format=CSV)'
f = os.path.join(T, 'umich', 'umich_monthly_1978on_key.csv'); d = pd.read_csv(f)
for k in ['ics_all', 'icc_all', 'ice_all', 'umex_r_all', 'umex_u_all', 'bus12_r_all', 'bexp_r_all', 'news_u_all',
          'pjob_mean_all']:
    if k in d: add('Univ. of Michigan Surveys of Consumers', U, k, 'monthly', d['date'], d[k], f,
                   'raw/umich/sca_all_tables_M.csv', 'final values not revised (prelim->final only; ALFRED UMCSENT vintages from 1998)')
f = os.path.join(T, 'umich', 'umich_quarterly_1960on_key.csv'); d = pd.read_csv(f)
for k in ['ics_all', 'umex_r_all', 'umex_u_all', 'bus12_r_all', 'news_u_all']:
    if k in d: add('Univ. of Michigan Surveys of Consumers', U, k + ' (quarterly)', 'quarterly', d['date'], d[k], f,
                   'raw/umich/sca_all_tables_Q.csv', 'not revised', 'quarterly surveys 1960-1977; averages of monthly from 1978')
f = os.path.join(T, 'umich', 'umich_ics_1952on_irregular.csv'); d = pd.read_csv(f)
add('Univ. of Michigan Surveys of Consumers', 'https://www.sca.isr.umich.edu/files/tbmics.csv', 'ICS_ALL (irregular 1952-77, monthly 1978-)',
    'irregular->monthly', d['date'], d['ICS_ALL'], f, 'raw/umich/tbmics.csv', 'not revised')

# --- EIA
for f in sorted(glob.glob(os.path.join(T, 'eia_wpsr', '*_weekly.csv'))):
    d = pd.read_csv(f); sid = d['series'].iloc[0]
    add('EIA Weekly Petroleum Status Report', 'https://www.eia.gov/dnav/pet/hist_xls/%sw.xls' % sid,
        '%s %s' % (sid, d['name'].iloc[0]), 'weekly', d['week_ending'], d['value'], f, 'raw/eia_wpsr/%s.xls' % sid,
        'weekly estimates not generally revised (EIA)', 'asof_assumed = week end + 5 days')

# --- ALFRED
for f in sorted(glob.glob(os.path.join(T, 'alfred', '*_firstprint.csv'))):
    sid = os.path.basename(f).replace('_firstprint.csv', '')
    d = pd.read_csv(f); g = d[~d['is_backfill']]
    add('ALFRED (keyless downloaddata form)', 'https://alfred.stlouisfed.org/series/downloaddata?seid=' + sid,
        sid + ' first print', 'see series', g['date'], g['first_value'], f, 'raw/alfred/%s_alfred.zip' % sid,
        'full vintage history (realtime periods file)', 'back-filled obs (first published in the first ALFRED vintage) excluded here')

# --- Philly BOS
BU = 'https://www.philadelphiafed.org/-/media/FRBP/Assets/Surveys-And-Data/MBOS/Historical-Data/'
f = os.path.join(T, 'philly_bos', 'bos_history_tidy.csv'); d = pd.read_csv(f)
for k in ['gacdfna', 'nocdfna', 'shcdfna', 'necdfna', 'awcdfna', 'gafdfna', 'gacdfsa', 'nocdfsa', 'necdfsa']:
    if k in d: add('Philadelphia Fed Manufacturing Business Outlook Survey', BU + 'Data-Series/bos_history.csv', k,
                   'monthly', d['date'], d[k], f, 'raw/philly_bos/bos_history.csv',
                   'NSA: survey tabulation (no revision process documented); SA (..sa): revised every January' if k.endswith('na')
                   else 'SA revised every January (current file = latest seasonal factors)')

# --- Livingston
LU = 'https://www.philadelphiafed.org/-/media/FRBP/Assets/Surveys-And-Data/livingston-survey/historical-data/means.xlsx'
f = os.path.join(T, 'livingston', 'livingston_means_long.csv'); d = pd.read_csv(f)
for v, fld in [('IP', 'IP_BP'), ('IP', 'IP_6M'), ('IP', 'IP_12M'), ('UNPR', 'UNPR_BP'), ('UNPR', 'UNPR_12M'),
               ('RGDPX', 'RGDPX_12M'), ('CPI', 'CPI_12M')]:
    x = d[(d['variable'] == v) & (d['field'] == fld)]
    add('Philadelphia Fed Livingston Survey', LU, 'mean ' + fld, 'semiannual (Jun/Dec)', x['survey'], x['value'], f,
        'raw/livingston/means.xlsx', 'real time by construction; _BP = base-period value as known to forecasters',
        'release dates (exact or not-after) in livingston_release_dates.csv')

# --- FRED Moody's
for s in ['BAA', 'AAA', 'DBAA', 'DAAA']:
    f = os.path.join(T, 'fred', s + '.csv'); d = pd.read_csv(f)
    add('FRED (Moody\'s)', 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=' + s, s,
        'daily' if s.startswith('D') else 'monthly', d['date'], d['value'], f, 'raw/fred/%s.csv' % s,
        'market yields, not revised')

# --- Beige Book
f = os.path.join(T, 'beigebook', 'editions.csv')
if os.path.exists(f):
    d = pd.read_csv(f)
    for k in ['n_words', 'n_neg_listed', 'n_pos_listed', 'n_recession']:
        add('Minneapolis Fed Beige Book archive (national summaries)',
            'https://www.minneapolisfed.org/beige-book-reports/YYYY/YYYY-MM-su', k, '8-12 per year',
            d['pub_date'], d[k], f, 'raw/beigebook/national_summaries.jsonl', 'text never revised',
            'plain counts of a pre-declared word list (tidy_beigebook.py); not an index')

# --- FRASER SCB weekly (issues held)
f = os.path.join(T, 'fraser_scb_weekly', 'row_lines.csv')
if os.path.exists(f):
    d = pd.read_csv(f)
    for k, g in d.groupby('key'):
        g = g.drop_duplicates('issue_date')
        add('FRASER Survey of Current Business weekly supplement (title 57)',
            'https://fraser.stlouisfed.org/title/survey-current-business-business-statistics-weekly-supplement-57',
            k + ' (issues with a matched row; values NOT yet mapped to weeks)', 'weekly (issue)',
            g['issue_date'], None, f, 'raw/fraser/scb_weekly_pdf/', 'as printed (never revised)',
            'n_obs = issues in which the row was found; raw lines only, no values parsed yet')

pd.DataFrame(rows).to_csv(os.path.join(W, 'MANIFEST.csv'), index=False)
print(len(rows), 'manifest rows')
