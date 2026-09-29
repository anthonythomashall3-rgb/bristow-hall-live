#!/usr/bin/env python3
"""First-print tables and MANIFEST.csv from out/asprinted_long.csv and out/vintages/*.csv."""
import glob, os
import pandas as pd
import numpy as np

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(W, 'out')

DESC = {
    'UNRATE': 'Unemployment rate, seasonally adjusted, % of civilian labor force (14+), as printed',
    'UNRATENSA': 'Unemployment rate, not seasonally adjusted, % (printed from Feb-1950 EI; earlier = 100*UNEMP/CLF from printed levels)',
    'CLF14NSA': 'Civilian labor force 14+, NSA, thousands (EI 1961 issues print millions)',
    'CLF14SA': 'Civilian labor force 14+, SA, thousands (printed in millions, EI Nov-1960 on)',
    'UNEMPLOY14NSA': 'Unemployed 14+, NSA, thousands',
    'UNEMPLOY14SA': 'Unemployed 14+, SA, thousands (printed in millions, EI Nov-1960 on)',
    'CE14NSA': 'Civilian employment 14+, NSA, thousands',
    'CE14SA': 'Civilian employment 14+, SA, thousands (printed in millions)',
    'MANEMP': 'Manufacturing employees, SA, thousands (EI Jul-1957 on; E&E Sep-1954 on)',
    'MANEMPNSA': 'Manufacturing employees, NSA, thousands (1948-12..1949-09 = durable+nondurable)',
    'NDMANEMP': 'Nondurable goods manufacturing employees, SA, thousands (EI Jul-1957 on)',
    'NDMANEMPNSA': 'Nondurable goods manufacturing employees, NSA, thousands (EI Dec-1948 on)',
    'DMANEMP': 'Durable goods manufacturing employees, SA, thousands',
    'DMANEMPNSA': 'Durable goods manufacturing employees, NSA, thousands',
    'PAYEMS': 'Employees in nonagricultural establishments, SA, thousands (EI Dec-1954 on; E&E Sep-1954 on)',
    'PAYEMS_XAKHI': 'Nonagricultural employees, SA, excluding Alaska and Hawaii (EI 1960-61)',
    'PAYNSA': 'Employees in nonagricultural establishments, NSA, thousands (1948-12..1954-07 = sum of printed divisions)',
    'AWHMAN': 'Average weekly hours, production workers, manufacturing, SA (EI Nov-1960 on; E&E Jul-1960 on)',
    'AWHMANNSA': 'Average weekly hours, production workers, manufacturing, NSA',
    'AWHDURNSA': 'Average weekly hours, durable goods manufacturing, NSA',
    'AWHNONDURNSA': 'Average weekly hours, nondurable goods manufacturing, NSA',
}
URL = {'EI': 'https://fraser.stlouisfed.org/files/docs/publications/ei/<YYYY>/<MM>-<YYYY>.pdf (or EI_<MM><YYYY>.pdf)',
       'EE': 'https://fraser.stlouisfed.org/files/docs/publications/employment/emp_<YYYY><MM>.pdf | employment/1960s/empl_<MM><YYYY>.pdf',
       'MLR': 'https://fraser.stlouisfed.org/files/docs/publications/bls_mlr/bls_mlr_<YYYY><MM>.pdf'}

def main():
    l = pd.read_csv(os.path.join(OUT, 'asprinted_long.csv'), dtype={'issue': str, 'pub_date': str})
    c = l[(l.is_current) & (l.doubt.isna())].copy()
    # first prints
    fp = c.sort_values(['series', 'ref_month', 'pub_date', 'source']).groupby(['series', 'ref_month']).first().reset_index()
    fp = fp[['series', 'ref_month', 'value', 'source', 'issue', 'pub_date', 'basis', 'cps_basis', 'derived']]
    fp.to_csv(os.path.join(OUT, 'first_prints.csv'), index=False)
    rows = []
    for fn in sorted(glob.glob(os.path.join(OUT, 'vintages', '*_asprinted_vintages.csv'))):
        s = os.path.basename(fn).replace('_asprinted_vintages.csv', '')
        w = pd.read_csv(fn, index_col=0)
        has = w.notna().any(axis=1)
        refs = w.index[has]
        f1 = fp[fp.series == s].sort_values('ref_month')
        vals = f1.value.values
        rep = float(np.mean(vals[1:] == vals[:-1])) * 100 if len(vals) > 1 else np.nan
        srcs = sorted(set(l[l.series == s].source))
        rows.append(dict(file=os.path.relpath(fn, W), series=s, description=DESC.get(s, ''),
                         source='; '.join({'EI': 'CEA Economic Indicators (FRASER)', 'EE': 'BLS Employment and Earnings (FRASER)', 'MLR': 'BLS Monthly Labor Review (FRASER)'}[x] for x in srcs),
                         url=' | '.join(URL[x] for x in srcs), frequency='monthly (one column per publication)',
                         first_obs=refs.min()[:7] if len(refs) else '', last_obs=refs.max()[:7] if len(refs) else '',
                         n_publications=w.shape[1], n_obs=int(w.notna().sum().sum()), n_ref_months=int(has.sum()),
                         first_pub=w.columns[0][-8:] if w.shape[1] else '', last_pub=w.columns[-1][-8:] if w.shape[1] else '',
                         pct_repeated_values=round(rep, 1)))
    for name, desc in (('out/asprinted_long.csv', 'tidy long: every parsed print (incl. doubtful, old-basis duplicates), with OCR readings and flags'),
                       ('out/first_prints.csv', 'first non-doubtful print per series and reference month'),
                       ('out/doubtful_cells.csv', 'cells withheld from wide tables'),
                       ('out/alfred_validation.csv', 'print vs ALFRED vintage comparison, 1960-62 overlap')):
        rows.append(dict(file=name, series='all', description=desc, source='EI; E&E', url='', frequency='monthly'))
    m = pd.DataFrame(rows)
    m.to_csv(os.path.join(W, 'MANIFEST.csv'), index=False)
    print(m[['series', 'first_obs', 'last_obs', 'n_publications', 'n_obs', 'pct_repeated_values']].to_string())

if __name__ == '__main__':
    main()
