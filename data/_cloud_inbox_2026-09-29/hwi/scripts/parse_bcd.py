#!/usr/bin/env python3
"""Parse BCD candidate pages (raw/fraser/cand/*.words.json.gz) for series 46 (and 60) month-row tables.
Writes work/bcd_cells.csv."""
import os, re, glob, gzip, json, sys
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_coltable import WordsPage, extract_col

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAND = os.path.join(W, 'raw', 'fraser', 'cand')


def main():
    rows = []
    for f in sorted(glob.glob(os.path.join(CAND, '*.words.json.gz'))):
        b = os.path.basename(f)
        m = re.match(r'(\d{4}-\d{2})-01_(\d+)_p(\d+)\.words\.json\.gz', b)
        issue, item, pg = m.group(1), m.group(2), int(m.group(3))
        rec = json.load(gzip.open(f, 'rt'))
        page = WordsPage(rec)
        for series in ('46', '60'):
            try:
                ex = extract_col(page, series)
            except Exception as e:
                rows.append(dict(issue=issue, item=item, page=pg, series=series, error=repr(e))); continue
            for r in ex:
                rows.append(dict(issue=issue, item=item, page=pg, **{**r, 'series': series}))
    df = pd.DataFrame(rows)
    os.makedirs(os.path.join(W, 'work'), exist_ok=True)
    df.to_csv(os.path.join(W, 'work', 'bcd_cells.csv'), index=False)
    ok = df[df.month.notna()] if 'month' in df else df
    print(len(df), len(ok))
    print(ok.groupby('series').issue.nunique())


if __name__ == '__main__':
    main()
