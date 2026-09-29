#!/usr/bin/env python3
"""Parse SCB pages (raw/bea/pages/*.pdf|txt) for series 46 (help-wanted index) and 60 (ratio).
 - C-pages / S-pages: series-in-rows tables via parse_rowtable.extract_rows (pdfplumber coordinates)
 - Historical-data pages (years in rows, months in columns): layout text lines after the '46.' heading
Writes work/scb_cells.csv
"""
import os, re, glob, json, sys
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parse_rowtable import extract_rows
from hwi_common import clean_num

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = os.path.join(W, 'raw', 'bea', 'pages')
OUT = os.path.join(W, 'work')
os.makedirs(OUT, exist_ok=True)
MON = {m: i for i, m in enumerate(['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august',
                                    'september', 'october', 'november', 'december'], 1)}


def issue_of(stem):
    m = re.match(r'scb-(\d{4})-([a-z]+)(?:-([a-z]+))?_p(\d+)', stem)
    y, m1, m2, pg = int(m.group(1)), m.group(2), m.group(3), int(m.group(4))
    return y, MON[m1], (MON[m2] if m2 else None), pg


def parse_hist(txt):
    """Historical table: heading line with '46.' + help-wanted (or '60.' ratio), then 'YYYY .... v1 .. v12 annual'."""
    out = []
    lines = txt.split('\n')
    cur = None
    for i, ln in enumerate(lines):
        if re.search(r'\b(46|60)\s*\.\s*(Index of |Ratio, )?help.?wanted', ln, re.I):
            cur = '60' if re.search(r'ratio', ln, re.I) else '46'
            continue
        if cur and re.search(r'^\s*\d{2,3}\s*\.\s+[A-Z]', ln) and not re.search(r'help.?wanted', ln, re.I):
            cur = None  # next series heading
            continue
        if not cur:
            continue
        m = re.match(r'^\s*(19[4-9]\d)\s*[.\s…]*(.*)$', ln)
        if not m:
            continue
        yr = int(m.group(1))
        toks = m.group(2).split()
        vals = [clean_num(t) for t in toks]
        vals = [v for v in vals if v]
        if len(vals) == 13:
            mv = vals[:12]; ann = vals[12]
        elif len(vals) == 12:
            mv = vals; ann = None
        else:
            out.append(dict(series=cur, year=yr, error=f'{len(vals)} values', line=ln.strip()[:200]))
            continue
        for k, v in enumerate(mv, 1):
            out.append(dict(series=cur, month=f'{yr}-{k:02d}', value=v[0], mark=v[1], doubtful=v[2], raw_token=v[3],
                            n_in_line=len(vals)))
    return out


def main():
    rows = []
    for pdfp in sorted(glob.glob(os.path.join(PAGES, 'scb-*_p*.pdf'))):
        stem = os.path.basename(pdfp)[:-4]
        y, m1, m2, pg = issue_of(stem)
        txt = open(os.path.join(PAGES, stem + '.txt')).read()
        base = dict(publication='SCB', issue=f'{y}-{m1:02d}' + (f'/{m2:02d}' if m2 else ''), file=stem, page=pg)
        # running head month (e.g. 'C-2 \u2022 May 1994') must match the issue month(s)
        head = ' '.join(txt.split('\n')[:3])
        mh = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)', head)
        misfiled = bool(mh) and MON[mh.group(1).lower()] not in (m1, m2)
        if misfiled:
            base['note'] = 'misfiled_page_running_head_' + mh.group(1)
        is_hist = bool(re.search(r'^\s*19[4-9]\d\s*\.{3,}', txt, re.M)) and re.search(r'\b46\s*\.\s*(Index of )?help.?wanted', txt, re.I)
        if is_hist:
            for r in parse_hist(txt):
                rows.append({**base, 'table': 'historical', **r})
        try:
            ex = extract_rows(pdfp)
        except Exception as e:
            rows.append({**base, 'table': 'row', 'error': repr(e)}); continue
        for r in ex:
            if r.get('error') == 'no month header' and r.get('tokens'):
                # fallback: C-page layout = 1 annual column + 14 months ending the month before the issue month
                toks = r['tokens']
                im = (m2 or m1)
                last = y * 12 + (im - 1) - 1  # month index of issue month - 1
                nm = 14
                vals = [(x, t, clean_num(t)) for x, t in toks]
                if len(vals) == nm + 1:
                    labs = ['annual'] + [f'{(last - nm + 1 + k) // 12}-{(last - nm + 1 + k) % 12 + 1:02d}' for k in range(nm)]
                    for (x, t, cn), lab in zip(vals, labs):
                        rows.append({**base, 'table': ('S-page' if re.search(r'season', r['row'], re.I) else 'C-page'), 'series': r['series'], 'month': lab, 'value': cn[0],
                                     'mark': cn[1], 'doubtful': cn[2], 'raw_token': t, 'row': r['row'],
                                     'note': (base.get('note', '') + ' no_header_ordinal_fallback').strip()})
                    continue
                r['error'] = f"no month header; {len(vals)} tokens"
            kind = 'C-page' if re.search(r'\(L,? ?L', r.get('row', '')) or 'Index of' in r.get('row', '') else 'S-page'
            rec = {**base, 'table': kind, **r}
            if base.get('note'):
                rec['note'] = (base['note'] + ' ' + str(r.get('note', '') or '')).strip()
            rows.append(rec)
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, 'scb_cells.csv'), index=False)
    print(df.groupby(['table', 'series']).size())
    print(df[df.get('error').notna()][['file', 'table', 'error']].to_string() if 'error' in df else '')


if __name__ == '__main__':
    main()
