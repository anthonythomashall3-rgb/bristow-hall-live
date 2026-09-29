#!/usr/bin/env python3
"""Extract month-row table cells from scanned FRASER tables with THREE readings:
the PDF text layer ('txt') and two tesseract renderings ('t300d' = 300 dpi with rule lines removed, 't400').
Rows are aligned across readings by vertical position (PDF points), columns by
right edge of numbers. Output one CSV per issue: out/<src>_cells/<src>_<issue>.csv

usage: extract2.py ei [issue-substrings...]
"""
import csv, glob, os, re, sys
from collections import Counter
import pymupdf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eicore import (month_of, year_of, is_numish, clean_num, parse_value, merge_numeric, group_lines,
                    cluster_1d, tesseract_words)
from ei_find import page_kind, ANCHORS

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESS = [('t300d', 300, True), ('t400', 400, False)]
READERS = ['txt'] + [t[0] for t in TESS]
ALLOWED = {'sample', 'area', 'definitions', 'definition', 'seasonally', 'adjusted', 'unadjusted',
           'basis', 'revised', 'monthly', 'average', 'unad', 'justed', 'seas', 'new', 'old'}
MONTHWORDS = {'january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september',
              'october', 'november', 'december'}

def line_text(l):
    return ' '.join(w[4] for w in l['w'])

def num_tokens(ws):
    toks = merge_numeric(ws)
    out = []
    for t in toks:
        if not is_numish(t['raw'].replace(' ', '')):
            continue
        c, fl = clean_num(t['raw'])
        v, k = parse_value(c)
        t['clean'] = c
        t['val'] = v
        t['kind'] = k
        t['footnote'] = (k == 'int' and v is not None and v < 10 and len(c) == 1)
        out.append(t)
    return out

def well_formed(t):
    c = t.get('clean') or ''
    if t['kind'] in ('dec1', 'dec2'):
        return True
    if t['kind'] == 'int':
        if re.fullmatch(r'\d{1,3}[,.]\d{3}', c.strip(',.')):
            return True
        if t['val'] is not None and t['val'] >= 100 and not t['raw'].rstrip().endswith((',', '.')):
            return True
    return False

def month_in_label(ws):
    for w in ws[:5]:
        if w[4][:1].isdigit():
            continue
        m = month_of(w[4])
        if m is not None:
            return m
    return None

def year_in_label(ws):
    for w in ws[:3]:
        y = year_of(w[4])
        if y is None:
            mm = re.match(r'^(19[4-6]\d)[:;*.,is]?$', w[4]) or re.match(r'^(19[4-6]\d)[:;*.,]', w[4])
            if mm:
                y = int(mm.group(1))
        if y is not None:
            return y
    return None

_WCACHE = {}

def page_words(page):
    """Text-layer words; for image-only pages (no text layer, e.g. EI Feb 1962) a full-page
    tesseract reading (300 dpi, psm 6) stands in for the text layer."""
    key = (page.parent.name, page.number)
    if key not in _WCACHE:
        ws = page.get_text('words')
        if sum(len(w[4]) for w in ws) < 300:
            ws = [w[:5] for w in tesseract_words(page, page.rect, dpi=300, derule=False, psm=6)]
        _WCACHE[key] = ws
    return _WCACHE[key]

def page_text_any(page):
    t = page.get_text()
    if len(t) < 300:
        ws = page_words(page)
        t = '\n'.join(' '.join(w[4] for w in l['w']) for l in group_lines(ws))
    return t

def find_region(page, kind):
    """Return (top, bottom) of the table body on this page (text layer), or None."""
    words = page_words(page)
    lines = group_lines(words)
    mrows = []
    for l in lines:
        ws = l['w']
        m = month_in_label(ws)
        if m is None:
            continue
        nt = [t for t in num_tokens(ws) if t['kind'] != 'bad' and not t['footnote']]
        if nt:
            mrows.append(l['yc'])
    anchors = []
    for l in lines:
        s = line_text(l)
        if ANCHORS[kind].search(s):
            if kind == 'HRS' and 'HOURS PER WEEK' in s and '[' not in s:
                continue
            if re.match(r'^\s*[\d«»*•]\s*(Includes|Number|Data|See)', s):
                continue  # footnote mentioning the unit
            anchors.append(l['yc'])
    cl = cluster_1d(mrows, 30)
    best = max(cl, key=len) if cl else []
    top = None
    if best:
        above = [a for a in anchors if a < best[0] and best[0] - a < 260]
        top = (max(above) + 3) if above else best[0] - 8
    elif anchors:
        cand = [a for a in anchors if a > page.rect.y1 * 0.35]
        if cand:
            top = cand[-1] + 3
    if top is None:
        return None
    # bottom: first footnote-ish text line below the last month row (or below top)
    start = best[-1] if best else top
    bot = page.rect.y1 - 30
    for l in lines:
        if l['yc'] <= start + 2:
            continue
        s = line_text(l)
        alpha = [a for a in re.findall(r'[A-Za-z]{4,}', s) if a.lower() not in ALLOWED and a.lower() not in MONTHWORDS]
        if len(alpha) >= 3 or re.search(r'Digitized|Source|NOTE', s):
            bot = l['yc'] - 3
            break
    if len(best) < 3 and not anchors:
        return None
    return top, bot

def readings_for(page, clip):
    out = {}
    words = [w for w in page.get_text('words') if w[1] >= clip.y0 - 1 and w[3] <= clip.y1 + 1]
    words = [w for w in page_words(page) if w[1] >= clip.y0 - 1 and w[3] <= clip.y1 + 1]
    out['txt'] = words
    for tag, dpi, dr in TESS:
        try:
            out[tag] = tesseract_words(page, clip, dpi=dpi, derule=dr)
        except Exception:
            out[tag] = []
    return out

def build_rows(readings, issue_ym, colgap=9.0):
    iy, im = issue_ym
    # per reading lines
    RL = {r: group_lines([w[:5] for w in ws]) for r, ws in readings.items()}
    # month-word right edges (label zone)
    mx = []
    for r, lines in RL.items():
        for l in lines:
            for w in l['w'][:5]:
                if not w[4][:1].isdigit() and month_of(w[4]) is not None:
                    mx.append(w[0])
                    break
    base = (sorted(mx)[len(mx) // 2] + 15) if mx else 0
    # numeric token right edges
    xs = []
    nlines = 0
    for r, lines in RL.items():
        for l in lines:
            nt = [t for t in num_tokens(l['w']) if t['x0'] > base + 2 and well_formed(t)]
            if len(nt) >= 2:
                nlines += 1
                xs += [t['x1'] for t in nt]
    cl = cluster_1d(xs, colgap)
    thr = max(2, 0.25 * nlines)
    cols = [sum(c) / len(c) for c in cl if len(c) >= thr]
    if not cols:
        return [], []
    # data_x: left edge of the first data column
    first = cols[0]
    x0s = []
    for r, lines in RL.items():
        for l in lines:
            for t in num_tokens(l['w']):
                if abs(t['x1'] - first) <= colgap * 1.6 and t['kind'] != 'bad':
                    x0s.append(t['x0'])
    data_x = (sorted(x0s)[max(0, len(x0s) // 20)] - 4) if x0s else first - 40
    # row backbone: y clusters of lines having data tokens
    ent = []  # (yc, reader, label_words, data_tokens)
    labels_only = []
    for r, lines in RL.items():
        for l in lines:
            lab = [w for w in l['w'] if w[2] <= data_x + 2]
            dat = [t for t in num_tokens([w for w in l['w'] if w[0] >= data_x - 1]) if not t['footnote']]
            dat = [t for t in dat if t['x0'] >= data_x - 1]
            if dat:
                ent.append((l['yc'], r, lab, dat))
            elif lab:
                labels_only.append((l['yc'], r, lab))
    ys = cluster_1d([e[0] for e in ent], 3.6)
    rows = []
    for yc_list in ys:
        lo, hi = min(yc_list) - 0.01, max(yc_list) + 0.01
        mem = [e for e in ent if lo <= e[0] <= hi]
        yc = sum(yc_list) / len(yc_list)
        per = {}
        for e in mem:
            per.setdefault(e[1], {'lab': [], 'dat': []})
            per[e[1]]['lab'] += e[2]
            per[e[1]]['dat'] += e[3]
        # label votes
        mv, yv, annual = Counter(), Counter(), 0
        for r, d in per.items():
            ws = sorted(d['lab'], key=lambda w: w[0])
            m = month_in_label(ws)
            y = year_in_label(ws)
            if m:
                mv[m] += 1
            if y:
                yv[y] += 1
            s = ' '.join(w[4] for w in ws).lower()
            if 'average' in s or ('monthly' in s and not m):
                annual += 1
        rows.append(dict(yc=yc, per=per, mvotes=mv, month=mv.most_common(1)[0][0] if mv else None,
                         year=yv.most_common(1)[0][0] if yv else None, annual=annual,
                         label=' '.join(w[4] for w in sorted(per.get('txt', {'lab': []})['lab'], key=lambda w: w[0]))
                         or ' '.join(w[4] for w in sorted(next(iter(per.values()))['lab'], key=lambda w: w[0]))))
    rows.sort(key=lambda r: r['yc'])
    # attach label-only lines (wrapped rows: label line above numbers line)
    for yc, r, lab in labels_only:
        m = month_in_label(sorted(lab, key=lambda w: w[0]))
        if not m:
            continue
        below = [row for row in rows if (-5 <= row['yc'] - yc <= 14) and row['month'] is None]
        below.sort(key=lambda row: abs(row['yc'] - yc))
        if below:
            below[0]['month'] = m
            y = year_in_label(sorted(lab, key=lambda w: w[0]))
            if y:
                below[0]['year'] = y
    # basis / section labels
    sect = []
    for yc, r, lab in labels_only:
        s = ' '.join(w[4] for w in sorted(lab, key=lambda w: w[0]))
        if re.search(r'sample|definition|[Ss]easonally|[Uu]nadjusted|adjusted', s):
            sect.append((yc, r, s))
    # column assignment per reading
    for row in rows:
        row['cells'] = {}
        for r, d in row['per'].items():
            for t in d['dat']:
                j = min(range(len(cols)), key=lambda q: abs(cols[q] - t['x1']))
                if abs(cols[j] - t['x1']) > colgap * 1.6:
                    continue
                cur = row['cells'].setdefault(j, {})
                if r in cur and abs(cols[j] - cur[r]['x1']) <= abs(cols[j] - t['x1']):
                    continue
                cur[r] = t
    # merge split rows: a row without month whose columns are disjoint from the previous row
    merged = []
    for row in rows:
        if merged and row['month'] is None and not row['year'] and 0 < row['yc'] - merged[-1]['yc'] <= 13:
            prev = merged[-1]
            if not (set(row['cells']) & set(prev['cells'])):
                for j, c in row['cells'].items():
                    prev['cells'][j] = c
                continue
        merged.append(row)
    rows = merged
    # resolve month-label ties / conflicts in favour of the sequence (previous month + 1)
    for i, row in enumerate(rows):
        mv = row.get('mvotes') or Counter()
        if i == 0 or not mv or len(mv) < 2:
            continue
        prev = rows[i - 1].get('month')
        if prev is None:
            continue
        want = prev % 12 + 1
        top = mv.most_common(1)[0][1]
        if row['month'] != want and mv.get(want, 0) >= max(1, top - 1):
            row['month'] = want
    # classify rows: annual vs monthly
    for row in rows:
        row['kind'] = 'annual' if (row['annual'] or (row['year'] and not row['month'])) else (
            'month' if row['month'] else 'unknown')
    # fill unknown months from neighbours
    for i, row in enumerate(rows):
        if row['kind'] != 'unknown':
            continue
        p = next((rows[j] for j in range(i - 1, -1, -1) if rows[j]['kind'] == 'month'), None)
        n = next((rows[j] for j in range(i + 1, len(rows)) if rows[j]['kind'] == 'month'), None)
        if p and n and i > 0 and rows[i - 1]['kind'] == 'month' and i + 1 < len(rows) and rows[i + 1]['kind'] == 'month':
            if (p['month'] % 12) + 1 == ((n['month'] - 2) % 12) + 1:
                row['month'] = (p['month'] % 12) + 1
                row['kind'] = 'month'
                row['month_inferred'] = True
        elif p and i > 0 and rows[i - 1] is p and not n:
            row['month'] = (p['month'] % 12) + 1
            row['kind'] = 'month'
            row['month_inferred'] = True
    # a month row directly under an annual row with a year label (e.g. '1950 monthly average' / 'June')
    for i, row in enumerate(rows):
        if row['kind'] == 'month' and not row['year'] and i > 0 and rows[i - 1]['kind'] == 'annual' \
                and rows[i - 1]['year'] and 1939 <= rows[i - 1]['year'] <= iy:
            row['year'] = rows[i - 1]['year']
    # keep only the final block of monthly rows (after the last annual row); isolated
    # reference months printed among the annual averages are dropped
    last_ann = max([i for i, r in enumerate(rows) if r['kind'] == 'annual'], default=-1)
    # years
    mrows = [r for i, r in enumerate(rows) if r['kind'] == 'month' and i > last_ann]
    prev = None
    for r in mrows:
        if r['year'] and iy - 2 <= r['year'] <= iy:
            r['yy'] = r['year']
        elif prev:
            r['yy'] = prev['yy'] + (1 if r['month'] <= prev['month'] else 0)
        else:
            r['yy'] = None
        prev = r if r.get('yy') else prev
    if mrows and mrows[-1].get('yy') is None:
        mrows[-1]['yy'] = iy if mrows[-1]['month'] < im else iy - 1
    for i in range(len(mrows) - 2, -1, -1):
        if mrows[i].get('yy') is None and mrows[i + 1].get('yy'):
            mrows[i]['yy'] = mrows[i + 1]['yy'] - (1 if mrows[i]['month'] >= mrows[i + 1]['month'] else 0)
    lim_hi = iy * 12 + im - 1          # reference month must precede the issue month
    lim_lo = lim_hi - 48
    mrows = [r for r in mrows if r.get('yy') and lim_lo <= r['yy'] * 12 + r['month'] - 1 < lim_hi]
    occ = Counter()
    for r in mrows:
        r['ref'] = f"{r['yy']}-{r['month']:02d}" if r.get('yy') else None
        occ[r['ref']] += 1
        r['occ'] = occ[r['ref']]
        above = [s for s in sect if s[0] < r['yc']]
        r['basis'] = above[-1][2] if above else ''
    return mrows, cols

FIELDS = ['issue', 'kind', 'page', 'row', 'yc', 'occ', 'ref', 'month_inferred', 'basis', 'label', 'col', 'col_x']
for _r in READERS:
    FIELDS += [_r + '_raw']

def do_issue(args):
    src, pdf, outdir, kinds = args
    issue = re.search(r'(\d{4}-\d{2})', os.path.basename(pdf)).group(1)
    iy, im = int(issue[:4]), int(issue[5:])
    fn = os.path.join(outdir, f'{src}_{issue}.csv')
    doc = pymupdf.open(pdf)
    out = []
    pagedir = os.path.join(W, 'raw', f'{src}_pages')
    os.makedirs(pagedir, exist_ok=True)
    for pi, page in enumerate(doc):
        text = page.get_text()
        if len(text) < 300:
            if pi < 5 or pi > 25:
                continue  # image-only issue: OCR only the labour-section pages
            text = page_text_any(page)
        ks = [k for k in page_kind(text) if k in kinds]
        for kind in ks:
            reg = find_region(page, kind)
            if not reg:
                continue
            top, bot = reg
            if bot - top < 25:
                continue
            clip = pymupdf.Rect(page.rect.x0, top, page.rect.x1, bot)
            rd = readings_for(page, clip)
            rows, cols = build_rows(rd, (iy, im))
            # a skewed tesseract reading can scramble row alignment: fall back to subsets
            base_n = len(build_rows({'txt': rd['txt']}, (iy, im))[0]) if rd.get('txt') else 0
            if len(rows) < base_n - 1:
                for sub in (('txt', 't400'), ('txt', 't300d'), ('txt',)):
                    r2, c2 = build_rows({k: rd[k] for k in sub if k in rd}, (iy, im))
                    if len(r2) >= base_n - 1:
                        rows, cols = r2, c2
                        break
            if len(rows) < 3:
                continue
            base = os.path.join(pagedir, f'{src}_{issue}_{kind}_p{pi+1:02d}')
            if not os.path.exists(base + '.pdf'):
                nd = pymupdf.open()
                nd.insert_pdf(doc, from_page=pi, to_page=pi)
                nd.save(base + '.pdf', garbage=3, deflate=True)
                with open(base + '.txt', 'w') as f:
                    f.write(text)
            for ri, r in enumerate(rows):
                for j in sorted(r['cells']):
                    rec = dict(issue=issue, kind=kind, page=pi + 1, row=ri, yc=round(r['yc'], 1), occ=r['occ'],
                               ref=r['ref'], month_inferred=int(bool(r.get('month_inferred'))),
                               basis=r['basis'][:60], label=r['label'][:40], col=j, col_x=round(cols[j], 1))
                    for rr in READERS:
                        t = r['cells'][j].get(rr)
                        rec[rr + '_raw'] = t['raw'] if t else ''
                    out.append(rec)
    with open(fn, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out)
    return issue, len(out)

def main():
    src = sys.argv[1]
    pats = sys.argv[2:]
    pdfs = sorted(glob.glob(os.path.join(W, 'raw', src, f'{src}_*.pdf')))
    if pats:
        pdfs = [p for p in pdfs if any(a in p for a in pats)]
    outdir = os.path.join(W, 'out', f'{src}_cells')
    os.makedirs(outdir, exist_ok=True)
    todo = [p for p in pdfs if pats or not os.path.exists(
        os.path.join(outdir, f"{src}_{re.search(r'(\d{4}-\d{2})', os.path.basename(p)).group(1)}.csv"))]
    kinds = ('LF', 'EMP', 'HRS')
    for p in todo:  # sequential: one heavy process at a time
        issue, n = do_issue((src, p, outdir, kinds))
        print(issue, n, flush=True)

if __name__ == '__main__':
    main()
