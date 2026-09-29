#!/usr/bin/env python3
"""MANIFEST.csv: one row per source x table x series in hwi_asprinted_long.csv."""
import os
import numpy as np, pandas as pd

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
L = pd.read_csv(os.path.join(W, 'hwi_asprinted_long.csv'), dtype={'series': str})
URL = {
    'Business Cycle Developments (Census)': 'https://fraser.stlouisfed.org/title/business-conditions-digest-43',
    'Business Conditions Digest (Census/BEA)': 'https://fraser.stlouisfed.org/title/business-conditions-digest-43',
    'Survey of Current Business (BEA)': 'https://apps.bea.gov/scb/issues.htm',
    'New England Economic Indicators (FRB Boston)': 'https://www.bostonfed.org/-/media/Documents/neei/reports/<mon><yy>.pdf',
}
rows = []
for (pub, tab, ser), g in L.groupby(['publication', 'table', 'series']):
    # repeated values: share of cells equal to the previous month's cell in the same issue
    rep = []
    for iss, h in g.sort_values('month').groupby('issue'):
        v = h.drop_duplicates('month').value.values
        if len(v) > 1:
            rep.extend(list(v[1:] == v[:-1]))
    rows.append(dict(source=pub, table=tab, series=('46 help-wanted index' if ser == '46' else '60 ratio HWI/unemployed'),
                     url=URL.get(pub, g.source_url.iloc[0]), frequency='monthly',
                     n_publications=g.issue.nunique(), first_publication=g.publication_date.min(),
                     last_publication=g.publication_date.max(), first_obs=g.month.min(), last_obs=g.month.max(),
                     n_obs=len(g), n_distinct_months=g.month.nunique(),
                     pct_repeated_values=round(100 * np.mean(rep), 1) if rep else None,
                     pct_ocr_doubtful=round(100 * g.ocr_doubtful.astype(str).str.lower().eq('true').mean(), 1),
                     bases=';'.join(sorted(g.base.astype(str).unique())),
                     date_basis=';'.join(sorted(g.date_basis.astype(str).unique()))))
m = pd.DataFrame(rows)
m.to_csv(os.path.join(W, 'MANIFEST.csv'), index=False)
print(m[['source', 'table', 'series', 'n_publications', 'first_obs', 'last_obs', 'n_obs', 'pct_repeated_values', 'pct_ocr_doubtful']].to_string())
