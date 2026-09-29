"""Generic month-row table extraction from word boxes (text layer or tesseract)."""
import re
from eicore import (month_of, year_of, is_numish, clean_num, parse_value, merge_numeric,
                    group_lines, cluster_1d)

ALLOWED = {'sample', 'area', 'definitions', 'definition', 'seasonally', 'adjusted', 'unadjusted',
           'basis', 'revised', 'monthly', 'average', 'unad', 'justed', 'seas'}

STOPWORDS_END = re.compile(r'^(includes|source|sources|note|preliminary|data|see|revised|weekly|'
                           r'excludes|beginning|not|digitized|seasonally|for|all|estimate|based|'
                           r'total|pertains|shown|monthly)', re.I)

def label_info(words, data_x):
    """words sorted by x. Returns (year, month, label_text, rest_words)."""
    lab = [w for w in words if w[0] < data_x]
    rest = [w for w in words if w[0] >= data_x]
    y = m = None
    for w in lab[:4]:
        t = w[4]
        if y is None:
            yy = year_of(t)
            if yy is None:
                mm_ = re.match(r'^(19[4-6]\d)[:;*.]', t)
                if mm_:
                    yy = int(mm_.group(1))
            if yy is not None:
                y = yy
                continue
        if m is None:
            mm = month_of(t)
            if mm is not None:
                m = mm
                break
    return y, m, ' '.join(w[4] for w in lab), rest

def extract_rows(words, issue_ym, body_top=None, body_bot=None, x_min=None, x_max=None,
                 min_data_x=None, gap=7.5):
    """Extract month rows.

    words: list of (x0,y0,x1,y1,text[,conf]).
    Returns dict with rows [{ref, basis, yc, label, toks:[tok]}], data_x.
    """
    ws = [w for w in words
          if (body_top is None or w[1] >= body_top) and (body_bot is None or w[3] <= body_bot)
          and (x_min is None or w[0] >= x_min) and (x_max is None or w[2] <= x_max)]
    lines = group_lines(ws)
    # candidate month lines: a month word within the first 3 words
    cand = []
    for i, l in enumerate(lines):
        for w in l['w'][:4]:
            if month_of(w[4]) is not None and not is_numish(w[4]):
                cand.append(i)
                break
    if not cand:
        return {'rows': [], 'data_x': None, 'lines': lines}
    # data_x: left edge of numeric data. Month word right edge + margin
    mx = []
    for i in cand:
        l = lines[i]
        for w in l['w'][:4]:
            if month_of(w[4]) is not None:
                mx.append(w[2])
                break
    base = sorted(mx)[len(mx) // 2]
    # numeric tokens right of base on month lines
    nx = []
    for i in cand:
        toks = merge_numeric([w for w in lines[i]['w'] if w[0] > base + 2], gap=gap)
        for t in toks:
            c, _ = clean_num(t['raw'])
            v, k = parse_value(c)
            if k != 'bad' and not (k == 'int' and v < 10 and ',' not in t['raw']):
                nx.append(t['x0'])
    data_x = (min(nx) - 3) if nx else base + 30
    # footnote markers directly after month word: data_x should be at least base+12
    if min_data_x is not None:
        data_x = max(data_x, min_data_x)
    # restrict: footnote markers that sit far left are excluded since they are < data_x
    rows = []
    cur_year = None
    basis = ''
    last_row = None
    for i, l in enumerate(lines):
        y, m, lab, rest = label_info(l['w'], data_x)
        labl = lab.lower()
        if m is None:
            # section headings / basis labels
            if re.search(r'sample|definition|adjusted|unadjusted', labl) and not rest:
                basis = lab.strip(' :')
            if y is not None and ('average' in labl or rest):
                last_row = None  # annual row
                cur_year = cur_year  # do not change
                continue
            # numeric-only continuation line
            if last_row is not None and rest and not lab.strip(' ._-—'):
                toks = merge_numeric(rest, gap=gap)
                last_row['cont'] += toks
                continue
            alpha = [w for w in re.findall(r'[A-Za-z]{4,}', ' '.join(w[4] for w in l['w']))
                     if w.lower() not in ALLOWED]
            if rows and len(alpha) >= 2:
                break  # end of table body (footnotes / next table)
            if last_row is not None and lab and STOPWORDS_END.match(lab.strip(' 0123456789*•')):
                last_row = None
            continue
        if y is not None:
            cur_year = y
        row = dict(y=y, m=m, label=lab, basis=basis, yc=l['yc'], toks=merge_numeric(rest, gap=gap), cont=[],
                   words=l['w'])
        rows.append(row)
        last_row = row
    # infer years
    iy, im = issue_ym
    # forward pass using explicit years
    prev = None
    for r in rows:
        if r['y'] is not None and 1945 <= r['y'] <= iy:
            prev = (r['y'], r['m'])
            r['yy'] = r['y']
        elif prev is not None:
            yy = prev[0] + (1 if r['m'] <= prev[1] else 0)
            r['yy'] = yy
            prev = (yy, r['m'])
        else:
            r['yy'] = None
    # anchor from the end when no explicit year
    if rows and all(r['yy'] is None for r in rows):
        # last row: latest month before issue
        yy = iy if rows[-1]['m'] < im else iy - 1
        rows[-1]['yy'] = yy
        for j in range(len(rows) - 2, -1, -1):
            nxt = rows[j + 1]
            rows[j]['yy'] = nxt['yy'] - (1 if rows[j]['m'] >= nxt['m'] else 0)
    elif rows and rows[0]['yy'] is None:
        # fill leading rows backwards from first known
        k = next(j for j, r in enumerate(rows) if r['yy'] is not None)
        for j in range(k - 1, -1, -1):
            nxt = rows[j + 1]
            rows[j]['yy'] = nxt['yy'] - (1 if rows[j]['m'] >= nxt['m'] else 0)
    for r in rows:
        r['ref'] = f"{r['yy']}-{r['m']:02d}" if r['yy'] else None
    return {'rows': rows, 'data_x': data_x, 'lines': lines}

def assign_columns(rows, colgap=9.0, min_frac=0.25):
    """Cluster token right-edges across rows into columns; returns list of centers
    and sets row['cells'] = {col: tok}."""
    xs = []
    for r in rows:
        for t in r['toks'] + r['cont']:
            c, _ = clean_num(t['raw'])
            v, k = parse_value(c)
            if k == 'bad' and not re.search(r'\d', t['raw']):
                continue
            if k == 'int' and v is not None and v < 10 and len(c) == 1:
                continue  # footnote marker
            xs.append(t['x1'])
    cl = cluster_1d(xs, colgap)
    n = max(1, len(rows))
    cols = [sum(c) / len(c) for c in cl if len(c) >= max(2, min_frac * n)]
    for r in rows:
        cells = {}
        for src in ('toks', 'cont'):
            for t in r[src]:
                c, fl = clean_num(t['raw'])
                v, k = parse_value(c)
                if k == 'int' and v is not None and v < 10 and len(c) == 1:
                    continue
                if not cols:
                    continue
                j = min(range(len(cols)), key=lambda q: abs(cols[q] - t['x1']))
                if abs(cols[j] - t['x1']) > colgap * 1.6:
                    continue
                if src == 'cont' and j in cells:
                    continue
                if j in cells:
                    # two tokens in one column: keep the one nearer
                    if abs(cols[j] - t['x1']) >= abs(cols[j] - cells[j]['x1']):
                        continue
                tt = dict(t)
                tt['clean'] = c
                tt['val'] = v
                tt['kind'] = k
                tt['flags'] = fl
                cells[j] = tt
        r['cells'] = cells
    return cols
