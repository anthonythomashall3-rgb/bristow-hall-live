#!/usr/bin/env python3
"""Tidy the Survey of Professional Forecasters files (raw/spf) into CSVs under tidy/spf/.

spf_release_dates.csv        survey, true deadline, news release date (known from 1990:Q2 only)
spf_recess_mean.csv          mean probability of a decline in real GNP/GDP, current quarter (RECESS1) and
                             next four (RECESS2 = 'Anxious Index'), by survey, with release dates
spf_recess_individual.csv    every forecaster's RECESS1..5 (from SPFmicrodata.xlsx), long
spf_recess_median_n.csv      median, 75th pct, share of forecasters >= 50, n responses, computed from micro
spf_anxious_index_chart.csv  Philadelphia Fed's own anxious-index file (aligned to target quarter)
spf_{mean,median}_{level,growth}_long.csv   every variable/horizon in the mean/median files, long

Release timing. The Philadelphia Fed publishes true deadline and release dates only from 1990:Q2
(spf-release-dates.txt). For ASA/NBER surveys before that the timing is unknown; the documentation says
questionnaires went out after the advance NIPA report (end of first month of the quarter) and results
were probably released before the second report (end of second month). Columns:
  release_date              known date, else blank
  release_date_assumed      known date, else the last day of the survey quarter (conservative: later
                            than the probable end-of-second-month release, so a backtest using it cannot
                            read an ASA/NBER survey early)
"""
import os, re, calendar
import pandas as pd

W = '/tmp/claude-0/-home-user/49f76bce-ebc7-5769-b106-ce7685453d86/scratchpad/collect/new_candidates'
R = os.path.join(W, 'raw', 'spf'); O = os.path.join(W, 'tidy', 'spf'); os.makedirs(O, exist_ok=True)

# release dates
rows, yr = [], None
for ln in open(os.path.join(R, 'spf-release-dates.txt'), encoding='latin-1'):
    m = re.match(r'^\s*(\d{4})?\s+Q(\d)\s+(\d{1,2}/\d{1,2}/\d{2})(\**)\s+(\d{1,2}/\d{1,2}/\d{2})(\**)', ln)
    if not m: continue
    if m.group(1): yr = int(m.group(1))
    def d(s):
        mm, dd, yy = map(int, s.split('/'))
        return '%04d-%02d-%02d' % (1900 + yy if yy >= 50 else 2000 + yy, mm, dd)
    rows.append(dict(year=yr, quarter=int(m.group(2)), deadline=d(m.group(3)), release_date=d(m.group(5)),
                     flag=(m.group(4) or m.group(6) or '')))
rel = pd.DataFrame(rows)
rel.to_csv(os.path.join(O, 'spf_release_dates.csv'), index=False)

def qend(y, q):
    m = 3 * q
    return '%04d-%02d-%02d' % (y, m, calendar.monthrange(y, m)[1])

def add_dates(df):
    df = df.merge(rel[['year', 'quarter', 'deadline', 'release_date']], how='left',
                  left_on=['YEAR', 'QUARTER'], right_on=['year', 'quarter']).drop(columns=['year', 'quarter'])
    df['release_date_assumed'] = [r if isinstance(r, str) else qend(int(y), int(q))
                                  for r, y, q in zip(df['release_date'], df['YEAR'], df['QUARTER'])]
    return df

# mean RECESS (prob.xlsx, sheet RECESS)
x = pd.read_excel(os.path.join(R, 'prob.xlsx'), sheet_name='RECESS')
x = x.apply(pd.to_numeric, errors='coerce').dropna(subset=['YEAR'])
x[['YEAR', 'QUARTER']] = x[['YEAR', 'QUARTER']].astype(int)
add_dates(x).to_csv(os.path.join(O, 'spf_recess_mean.csv'), index=False)

# individual RECESS
mi = pd.read_excel(os.path.join(R, 'SPFmicrodata.xlsx'), sheet_name='RECESS')
mi = mi.apply(pd.to_numeric, errors='coerce').dropna(subset=['YEAR'])
mi[['YEAR', 'QUARTER', 'ID']] = mi[['YEAR', 'QUARTER', 'ID']].astype(int)
mi.to_csv(os.path.join(O, 'spf_recess_individual.csv'), index=False)
g = mi.groupby(['YEAR', 'QUARTER'])
agg = pd.DataFrame({'n_resp_RECESS1': g['RECESS1'].count(), 'n_resp_RECESS2': g['RECESS2'].count()})
for k in ['RECESS1', 'RECESS2', 'RECESS3']:
    agg['median_' + k] = g[k].median()
    agg['p75_' + k] = g[k].quantile(0.75)
    agg['share_ge50_' + k] = g[k].apply(lambda s: (s.dropna() >= 50).mean() if s.notna().any() else None)
agg = add_dates(agg.reset_index())
agg.to_csv(os.path.join(O, 'spf_recess_median_n.csv'), index=False)

# anxious index chart file
a = pd.read_excel(os.path.join(R, 'anxious_index_chart.xlsx'), sheet_name='Data', header=None)
hdr = a.index[a.iloc[:, 0].astype(str).str.contains('Obs Year')][0]
a = a.iloc[hdr + 1:, :4]; a.columns = ['target_year', 'target_quarter', 'anxious_index', 'RECESS_column_as_in_file']
a = a.dropna(subset=['target_year'])
a.to_csv(os.path.join(O, 'spf_anxious_index_chart.csv'), index=False)

# mean/median level & growth, every variable, long
for fn, tag in [('meanLevel.xlsx', 'mean_level'), ('medianLevel.xlsx', 'median_level'),
                ('meanGrowth.xlsx', 'mean_growth'), ('medianGrowth.xlsx', 'median_growth')]:
    out = []
    for sh, d in pd.read_excel(os.path.join(R, fn), sheet_name=None).items():
        d = d.apply(pd.to_numeric, errors='coerce').dropna(subset=['YEAR'])
        vc = [c for c in d.columns if c not in ('YEAR', 'QUARTER')]
        m = d.melt(id_vars=['YEAR', 'QUARTER'], value_vars=vc, var_name='field', value_name='value').dropna()
        m.insert(2, 'sheet', sh)
        out.append(m)
    o = pd.concat(out); o[['YEAR', 'QUARTER']] = o[['YEAR', 'QUARTER']].astype(int)
    o = add_dates(o)
    o.to_csv(os.path.join(O, 'spf_%s_long.csv' % tag), index=False)
    print(tag, len(o))
print('release dates', len(rel), rel.iloc[0].to_dict(), rel.iloc[-1].to_dict())
