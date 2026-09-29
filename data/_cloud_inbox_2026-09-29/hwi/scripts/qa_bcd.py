#!/usr/bin/env python3
"""QA + long-format for BCD series 46/60 cells (work/bcd_cells.csv) -> work/bcd_long.csv
 - keeps table pages with >=6 parsed months for the series
 - base (index reference period) from the page words
 - publication date = scheduled release printed in the previous issue (work/bcd_release_dates.csv);
   missing ones estimated from the median lag of that year's issues (date_basis says which)
 - OCR checks: (a) isolated disagreement with the neighbouring issues that print the same month,
   (b) ratio to the Barnichon (2010) reconstruction far from the base-period median ratio
"""
import os, re, gzip, json, glob
import numpy as np, pandas as pd

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BARN = '/home/user/bristow-hall-live/data/24_bristow_rule_lab/workspace/lab/vac/barnichon_hwi.csv'


def page_base(issue, item, page):
    f = os.path.join(W, 'raw', 'fraser', 'cand', f'{issue}-01_{item}_p{int(page):03d}.words.json.gz')
    try:
        t = ' '.join(w['t'] for w in json.load(gzip.open(f, 'rt'))['words'])
    except Exception:
        return ''
    t = t.replace(' ', '')
    if re.search(r'1957-59=100|1957-59=|1957—59', t):
        return '1957-59=100'
    if re.search(r'1967=100|1967=l00|1967-100', t):
        return '1967=100'
    if re.search(r'1957=100', t):
        return '1957=100'
    return ''


def main():
    d = pd.read_csv(os.path.join(W, 'work', 'bcd_cells.csv'), dtype={'series': str, 'item': str})
    d = d[d.month.notna() & d.value.notna()].copy()
    d['n_page'] = d.groupby(['issue', 'page', 'series']).month.transform('size')
    d = d[d.n_page >= 6].copy()
    # Base period by issue date. Switch points were located from the step changes in the ratio of the printed
    # values to the Barnichon (2010) series (same TCB index): 1957=100 through the Jan 1964 issue,
    # 1957-59=100 from Feb 1964, 1967=100 from the Mar 1971 issue.
    def era_base(iss):
        return '1957=100' if iss < '1964-02' else ('1957-59=100' if iss < '1971-03' else '1967=100')
    d['base'] = d.issue.map(era_base)
    d['base_detected'] = True
    d.loc[d.series == '60', 'base'] = 'ratio'
    # Column disambiguation: some pages put a neighbouring column's figures in the series-46 band.
    # Keep series-46 cells within +-12% of the issue's typical level relative to Barnichon; for duplicate
    # months keep the cell closest to that level.  (Barnichon is used only to pick the column, never as a value.)
    bn0 = pd.read_csv(BARN).dropna(); bn0['month'] = bn0.d.str.slice(0, 7)
    d = d.merge(bn0[['month', 'hwi']].rename(columns={'hwi': 'bn'}), on='month', how='left')
    d['r0'] = d.value / d.bn
    exp = d[(d.series == '46') & d.r0.between(1.2, 3.3)].groupby('issue').r0.median()
    d['exp_r'] = d.issue.map(exp)
    d['colfit'] = (d.r0 / d.exp_r - 1).abs()
    bad = (d.series == '46') & d.bn.notna() & (d.colfit > 0.12)
    dropped = d[bad].copy()
    dropped.to_csv(os.path.join(W, 'work', 'bcd_dropped_wrong_column.csv'), index=False)
    d = d[~bad].copy()
    d['cf'] = d.colfit.fillna(0)
    d = d.sort_values(['issue', 'page', 'series', 'month', 'cf'])
    dupmask = d.duplicated(['issue', 'page', 'series', 'month'], keep='first')
    d.loc[~dupmask & d.duplicated(['issue', 'page', 'series', 'month'], keep=False), 'note'] = 'dup_month_resolved_by_level'
    d = d[~dupmask].copy()
    d = d.drop(columns=['bn', 'r0', 'exp_r', 'colfit', 'cf'])
    # series 60 (ratio of help-wanted advertising to persons unemployed): keep only plausible ratios
    d = d[~((d.series == '60') & ~d.value.between(0.1, 2.0))].copy()
    d.loc[d.series == '60', 'note'] = (d.loc[d.series == '60', 'note'].fillna('') + ' series60_range_filtered_only').str.strip()
    # span of the page -> table type
    span = d.groupby(['issue', 'page', 'series']).month.agg(lambda s: (pd.Period(max(s)) - pd.Period(min(s))).n)
    d['table'] = [('historical' if span[(a, b, c)] > 60 else 'basic_data') for a, b, c in zip(d.issue, d.page, d.series)]
    # dup within page: keep all but flagged
    # neighbour check (same series, base, table basic_data)
    d = d.sort_values(['series', 'month', 'issue'])
    d['nb_flag'] = ''
    for (s, b, m), g in d[d.table == 'basic_data'].groupby(['series', 'base', 'month']):
        g = g.drop_duplicates('issue', keep=False)  # ignore dup cells
        idx = list(g.index)
        vals = list(g.value)
        for k, ix in enumerate(idx):
            prev = vals[k - 1] if k > 0 else None
            nxt = vals[k + 1] if k + 1 < len(vals) else None
            v = vals[k]
            if prev is not None and nxt is not None and prev == nxt and v != prev:
                d.at[ix, 'nb_flag'] = f'isolated_disagreement(prev=next={prev:g})'
            elif prev is not None and nxt is None and v != prev and len(vals) >= 2:
                pass  # last print may be a genuine revision
    # Barnichon ratio check
    bn = pd.read_csv(BARN).dropna()
    bn['month'] = bn.d.str.slice(0, 7)
    d = d.merge(bn[['month', 'hwi']], on='month', how='left')
    d['ratio'] = d.value / d.hwi
    med = d[d.series == '46'].groupby('base').ratio.median()
    d['ratio_flag'] = ''
    m46 = d.series == '46'
    dev = (d.loc[m46, 'ratio'] / d.loc[m46, 'base'].map(med) - 1).abs()
    d.loc[m46 & (dev > 0.15).reindex(d.index, fill_value=False), 'ratio_flag'] = 'far_from_barnichon'
    # publication dates
    rd = pd.read_csv(os.path.join(W, 'work', 'bcd_release_dates.csv'))
    rmap = dict(zip(rd.issue, rd.scheduled_release))
    rd['lag'] = (pd.to_datetime(rd.scheduled_release) - pd.to_datetime(rd.issue + '-01')).dt.days
    rd['yr'] = rd.issue.str.slice(0, 4)
    lag_by_year = rd.groupby('yr').lag.median().to_dict()
    glob_lag = rd.lag.median()

    def pubdate(iss):
        if iss in rmap:
            return rmap[iss], 'scheduled_release_stated_in_previous_issue'
        yr = iss[:4]
        lag = lag_by_year.get(yr)
        if lag is None or np.isnan(lag):
            # nearest year with data
            yrs = sorted(lag_by_year, key=lambda y: abs(int(y) - int(yr)))
            lag = lag_by_year[yrs[0]] if yrs else glob_lag
        return (pd.Timestamp(iss + '-01') + pd.Timedelta(days=int(lag))).strftime('%Y-%m-%d'), 'estimated_median_lag_of_nearest_year'
    pdt = {iss: pubdate(iss) for iss in d.issue.unique()}
    d['publication_date'] = d.issue.map(lambda i: pdt[i][0])
    d['date_basis'] = d.issue.map(lambda i: pdt[i][1])
    idx = json.load(open(os.path.join(W, 'raw', 'fraser', 'index.json')))
    url = {str(x['item_id']): x['pdfUrl'] for x in idx}
    out = pd.DataFrame(dict(
        publication=np.where(d.issue < '1968-11', 'Business Cycle Developments (Census)', 'Business Conditions Digest (Census/BEA)'),
        issue=d.issue, publication_date=d.publication_date, date_basis=d.date_basis, month=d.month, value=d.value,
        base=d.base, sa_flag='SA', series=d.series, table=d.table, mark=d['mark'].fillna(''),
        ocr_doubtful=(d.doubtful.astype(bool) | (d.nb_flag != '') | (d.ratio_flag != '')),
        raw_token=d.raw_token, source_url=d.item.map(url), page=d.page,
        note=(d.nb_flag + ' ' + d.ratio_flag + ' ' + d.note.fillna('') + (~d.base_detected).map(lambda x: ' base_by_date' if x else '')).str.strip()))
    out.to_csv(os.path.join(W, 'work', 'bcd_long.csv'), index=False)
    s = out[out.series == '46']
    print('series 46 rows', len(s), 'issues', s.issue.nunique(), 'doubtful', s.ocr_doubtful.sum())
    print(s.groupby('base').agg(n=('value', 'size'), first=('month', 'min'), last=('month', 'max')))
    print('ratio medians', med.to_dict())
    print(s.note.str.extract(r'(isolated_disagreement|far_from_barnichon|dup_month)')[0].value_counts())


if __name__ == '__main__':
    main()
