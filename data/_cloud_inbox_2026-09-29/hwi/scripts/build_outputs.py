#!/usr/bin/env python3
"""Merge parsed cells from all sources into the deliverables:
  hwi_asprinted_long.csv, hwi_asprinted_wide_vintages.csv, MANIFEST.csv
Inputs (whatever exists): work/scb_cells.csv, work/bcd_cells.csv, work/news_cells.csv, work/bcd_release_dates.csv
"""
import os, re, calendar
import pandas as pd

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WK = os.path.join(W, 'work')
LONG_COLS = ['publication', 'issue', 'publication_date', 'date_basis', 'month', 'value', 'base', 'sa_flag', 'series',
             'table', 'mark', 'ocr_doubtful', 'raw_token', 'source_url', 'page', 'note']


def month_end(ym):
    y, m = int(ym[:4]), int(ym[5:7])
    return f'{y:04d}-{m:02d}-{calendar.monthrange(y, m)[1]:02d}'


def scb_long():
    p = os.path.join(WK, 'scb_cells.csv')
    if not os.path.exists(p):
        return pd.DataFrame(columns=LONG_COLS)
    d = pd.read_csv(p, dtype={'series': str})
    d = d[d.month.notna() & (d.month != 'annual') & d.value.notna()]
    d = d[d.table.isin(['C-page', 'S-page', 'historical'])]
    # misfiled pages (running head of another issue) are flagged in the parse step via 'misfiled' note
    iss = d.issue.astype(str)
    out = pd.DataFrame({'issue': iss.values})
    out['publication'] = 'Survey of Current Business (BEA)'
    # SCB states no release date; use the last day of the cover month (the latest month printed in the
    # C-pages is always cover month - 1, released by The Conference Board near the end of the cover month)
    out['publication_date'] = [month_end(i[:7]) if '/' not in i else month_end(i[:4] + '-' + i[-2:]) for i in iss]
    out['date_basis'] = 'cover_month_end_estimate'
    out['month'] = d.month.values
    out['value'] = d.value.values
    out['base'] = '1967=100'
    out['sa_flag'] = 'SA'
    out['series'] = d.series.values
    out['table'] = d.table.values
    out['mark'] = d.mark.fillna('').values
    out['ocr_doubtful'] = d.doubtful.fillna(False).astype(bool).values
    out['raw_token'] = d.raw_token.astype(str).values
    stem = d.file.str.replace(r'_p\d+$', '', regex=True)
    yr = stem.str.slice(4, 8)
    out['source_url'] = ('https://apps.bea.gov/scb/issues/' + yr + '/' + stem + '.pdf').values
    out['page'] = d.page.values
    out['note'] = d.note.fillna('').values if 'note' in d else ''
    return out


def load_extra(name):
    p = os.path.join(WK, name)
    if os.path.exists(p):
        d = pd.read_csv(p, dtype=str)
        for c in LONG_COLS:
            if c not in d:
                d[c] = ''
        d['value'] = pd.to_numeric(d['value'], errors='coerce')
        return d[LONG_COLS]
    return pd.DataFrame(columns=LONG_COLS)


def main():
    parts = [scb_long(), load_extra('bcd_long.csv'), load_extra('neei_long.csv'), load_extra('news_long.csv')]
    L = pd.concat([p for p in parts if len(p)], ignore_index=True)
    # news before 1996 used the 1967=100 index (BEA/TCB); from 1996 TCB published 1987=100
    nw = ~L.publication.str.contains('Survey|Business C|New England', regex=True)
    L.loc[nw & (L.publication_date.astype(str) < '1996-01-01'), 'base'] = '1967=100'
    L['ocr_doubtful'] = L.ocr_doubtful.astype(str).str.lower().isin(['true', '1'])
    # SCB Sep 1994 PDF carries the May 1994 C-2 page: not a Sep 1994 print, drop
    L = L[~L.note.astype(str).str.contains('misfiled_page')]
    L['value'] = pd.to_numeric(L.value, errors='coerce')
    L = L[L.value.notna()]
    L = L[LONG_COLS].sort_values(['series', 'publication_date', 'publication', 'table', 'month'])
    L.to_csv(os.path.join(W, 'hwi_asprinted_long.csv'), index=False)
    # wide as-of table: one column per publication date (series 46; S-pages and news "other" rows excluded)
    s = L[(L.series.astype(str) == '46') & (~L.table.isin(['S-page', 'news_other']))].copy()

    def tag(x):
        if 'Business Cycle Developments' in x or 'Business Conditions Digest' in x:
            return 'BCD'
        if 'Survey' in x:
            return 'SCB'
        if 'New England' in x:
            return 'NEEI'
        return re.sub(r'[^A-Za-z]', '', x)[:8].upper()
    s['src'] = s.publication.map(tag) + s.table.map(lambda t: 'HIST' if t == 'historical' else '')
    s['date8'] = s.publication_date.astype(str).str.replace('-', '')
    s['col'] = 'HWI_' + s.date8
    multi = s.groupby('col').src.nunique()
    s.loc[s.col.map(multi) > 1, 'col'] = s.col + '_' + s.src
    s = s.sort_values(['col', 'ocr_doubtful']).drop_duplicates(['col', 'month'])
    wide = s.pivot(index='month', columns='col', values='value')
    wide = wide[sorted(wide.columns)]
    wide.to_csv(os.path.join(W, 'hwi_asprinted_wide_vintages.csv'))
    meta = s.groupby('col').agg(publication=('publication', 'first'), issue=('issue', 'first'),
                                publication_date=('publication_date', 'first'), date_basis=('date_basis', 'first'),
                                base=('base', 'first'), n=('value', 'size'), first_month=('month', 'min'),
                                last_month=('month', 'max'), n_ocr_doubtful=('ocr_doubtful', 'sum'),
                                source_url=('source_url', 'first'))
    meta.to_csv(os.path.join(W, 'hwi_asprinted_wide_columns.csv'))
    print(L.groupby(['publication', 'table', 'series']).agg(n=('value', 'size'), first=('month', 'min'),
                                                             last=('month', 'max')).to_string())
    print('wide', wide.shape)


if __name__ == '__main__':
    main()
