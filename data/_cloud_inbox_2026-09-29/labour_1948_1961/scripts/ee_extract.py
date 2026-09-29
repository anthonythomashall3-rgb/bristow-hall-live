#!/usr/bin/env python3
"""Employment and Earnings (BLS): seasonally adjusted employment by industry division
(TOTAL nonagricultural, MANUFACTURING) and seasonally adjusted average weekly hours in
manufacturing, as printed. Three OCR readings per page (text layer, tesseract 300 dpi
de-ruled, tesseract 400 dpi), majority vote, identity TOTAL = sum of 8 divisions.

Pages come from out/ee_pages_index.csv (ee_find.py). Output: out/ee_fields_long.csv
(same columns as out/ei_fields_long.csv).  Sequential, run under nice.

Layouts handled
  industry rows x month columns (1954-09 .. mid-1956; hours table C-5 1960-07 ..):
      columns = [M-1, M-2, M-3, M-13] for employment (index group ignored; the
      thousands group is the right-hand block), [M-1, M-2, M-3, M-12, M-13] for hours,
      where M is the issue month; checked against the printed month headers.
  month rows x industry columns (Table 7, mid-1956 .. 1959): row labels give the month.
"""
import csv, os, re, sys
from collections import Counter
import pymupdf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eicore import group_lines, merge_numeric, clean_num, parse_value, tesseract_words, month_of, is_numish
from consensus import vote
import extract2

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
READERS = ['txt', 't300d', 't400']
DIV_ORDER = ['TOTAL', 'MINING', 'CONSTRUCTION', 'MANUFACTURING', 'TRANSPORTATION', 'TRADE', 'FINANCE', 'SERVICE',
             'GOVERNMENT']

def ym_add(y, m, k):
    t = y * 12 + (m - 1) + k
    return f'{t // 12}-{t % 12 + 1:02d}'

def readings(page, clip):
    out = {'txt': [w[:5] for w in page.get_text('words') if clip.y0 - 1 <= w[1] and w[3] <= clip.y1 + 1]}
    for tag, dpi, dr in (('t300d', 300, True), ('t400', 400, False)):
        try:
            out[tag] = [w[:5] for w in tesseract_words(page, clip, dpi=dpi, derule=dr)]
        except Exception:
            out[tag] = []
    return out

def ints_in_line(ws):
    toks = merge_numeric(ws)
    vals = []
    for t in toks:
        raw = t['raw']
        if not is_numish(raw.replace(' ', '')):
            continue
        c, _ = clean_num(raw)
        c = c.strip(',.')
        if re.fullmatch(r'\d{1,3}[,.]\d{3}', c) and ',' in c or re.fullmatch(r'\d{1,3},\d{3}', c):
            vals.append((t['x1'], int(c.replace(',', '').replace('.', '')), raw))
        elif re.fullmatch(r'\d{3}', c):
            vals.append((t['x1'], int(c), raw))
        elif re.fullmatch(r'\d{1,2}[.,]\d{3}', c):
            vals.append((t['x1'], int(re.sub(r'[,.]', '', c)), raw))
    return vals

def decs_in_line(ws):
    toks = merge_numeric(ws)
    vals = []
    for t in toks:
        c, _ = clean_num(t['raw'])
        m = re.fullmatch(r'(\d{2})[.,](\d)', c.strip(',.'))
        if m:
            vals.append((t['x1'], float(m.group(1) + '.' + m.group(2)), t['raw']))
    return vals

def stop_line(s):
    z = re.sub(r'\s+', '', s).lower()
    return bool(re.search(r'productionworkers|tab[lt]e7|tab[lt]e8|preliminary|^1/', z))

def industry_rows_emp(rd, issue):
    """Per reading: the 9 division rows of the SA table (TOTAL first, MANUFACTURING 4th).
    A data row is a line with >=3 index numbers (dd.d/ddd.d) or >=3 thousands numbers.
    Returns {reader: list of rows; each row = (label, [thousands ints, right-most 4])}."""
    res = {}
    for r, ws in rd.items():
        rows = []
        started = False
        for l in group_lines(ws):
            s = ' '.join(w[4] for w in l['w'])
            z = re.sub(r'\s+', '', s).lower()
            if not started and ('season' in z or 'seasona' in z) and ('division' in z or 'adju' in z):
                started = True
                continue
            if not started:
                continue
            if rows and stop_line(s):
                break
            toks = merge_numeric(l['w'])
            idx = [t for t in toks if re.fullmatch(r'\d{2,3}[.,]\d', clean_num(t['raw'])[0].strip(',.') or '')]
            v = ints_in_line(l['w'])
            if len(idx) >= 3 or len(v) >= 3:
                lab = z[:25]
                rows.append((lab, [x[1] for x in sorted(v)][-4:]))
            if len(rows) == 9:
                break
        res[r] = rows
    return res

def emp_industry_layout(page, clip, issue):
    rd = readings(page, clip)
    per = industry_rows_emp(rd, issue)
    y, m = int(issue[:4]), int(issue[5:])
    refs = [ym_add(y, m, -1), ym_add(y, m, -2), ym_add(y, m, -3), ym_add(y, m, -13)]
    out = []
    def row_of(rows, ri):
        # label-anchored where possible
        key = 'total' if ri == 0 else 'manuf'
        for k, (lab, v) in enumerate(rows):
            if key in lab:
                return v
        return rows[ri][1] if ri < len(rows) else []
    for ri, name in ((0, 'PAY'), (3, 'MFG')):
        for ci, ref in enumerate(refs):
            rds = []
            for r in READERS:
                v = row_of(per.get(r, []), ri)
                rds.append((r, v[ci] if len(v) == 4 else None, ''))
            best, nag, nval, alts = vote(rds)
            idok = None
            for r in READERS:
                rows = per.get(r, [])
                if len(rows) == 9 and all(len(x[1]) == 4 for x in rows):
                    tot = rows[0][1][ci]
                    sm = sum(rows[k][1][ci] for k in range(1, 9))
                    if abs(tot - sm) <= 12:
                        cand = rows[ri][1][ci]
                        if best is None or cand == best:
                            idok = True
                            best = cand
                            break
                        if idok is None:
                            idok = False
            out.append(dict(field=name, ref=ref, value=best, n_agree=nag, n_valid=nval, alts=alts, readings=rds,
                            identity={True: 'ok', False: 'FAIL', None: ''}[idok]))
    return out

def emp_month_layout(page, clip, issue):
    rd = readings(page, clip)
    y, m = int(issue[:4]), int(issue[5:])
    rows, cols = extract2.build_rows(rd, (y, m))
    out = []
    for r in rows:
        c0 = r['cells'].get(0, {})
        raws = [c0.get(k, {}).get('raw', '') if c0.get(k) else '' for k in READERS]
        if not any(re.search(r'\d[,.]\s?\d{3}', x) or re.fullmatch(r'\d{5}', x.replace(' ', '')) for x in raws):
            continue  # index-number block (1947-49=100), not thousands
        cells = r['cells']
        def reads(j):
            c = cells.get(j, {})
            rr = []
            for k in READERS:
                t = c.get(k)
                v = None
                if t:
                    cc, _ = clean_num(t['raw'])
                    cc = cc.strip(',.')
                    if re.fullmatch(r'\d{1,3}[,.]\d{3}', cc) or re.fullmatch(r'\d{3,5}', cc):
                        v = int(re.sub(r'[,.]', '', cc))
                rr.append((k, v, ''))
            return rr
        allv = {j: vote(reads(j)) for j in range(len(cols))}
        if len(cols) < 9:
            continue
        idok = None
        try:
            idok = abs(allv[0][0] - sum(allv[j][0] for j in range(1, 9))) <= 12
        except TypeError:
            pass
        for j, name in ((0, 'PAY'), (3, 'MFG')):
            best, nag, nval, alts = allv[j]
            out.append(dict(field=name, ref=r['ref'], value=best, n_agree=nag, n_valid=nval, alts=alts,
                            readings=reads(j), identity={True: 'ok', False: 'FAIL', None: ''}[idok],
                            month_inferred=int(bool(r.get('month_inferred')))))
    return out

def hours_layout(page, clip, issue):
    """C-5 (1960-07 on): first data row = MANUFACTURING, 5 columns [M-1, M-2, M-3, M-13, M-14]."""
    rd = readings(page, clip)
    y, m = int(issue[:4]), int(issue[5:])
    refs = [ym_add(y, m, -1), ym_add(y, m, -2), ym_add(y, m, -3), ym_add(y, m, -13), ym_add(y, m, -14)]
    per = {}
    for r, ws in rd.items():
        rows = []
        for l in group_lines(ws):
            v = decs_in_line(l['w'])
            v = [x for x in v if 30 <= x[1] <= 50]
            if len(v) >= 4:
                rows.append([x[1] for x in sorted(v)])
            if len(rows) == 3:
                break
        per[r] = rows
    out = []
    for ri, name in ((0, 'HRS_MFG'), (1, 'HRS_DUR'), (2, 'HRS_NDUR')):
        for ci, ref in enumerate(refs):
            rds = []
            for r in READERS:
                rows = per.get(r, [])
                v = rows[ri][ci] if ri < len(rows) and len(rows[ri]) == 5 else None
                rds.append((r, v, ''))
            best, nag, nval, alts = vote(rds)
            idok = None
            try:
                a = [per[r][0][ci] for r in READERS if len(per.get(r, [])) >= 3 and len(per[r][0]) == 5]
            except (IndexError, KeyError):
                a = []
            out.append(dict(field=name, ref=ref, value=best, n_agree=nag, n_valid=nval, alts=alts, readings=rds,
                            identity=''))
    # identity: total manufacturing between durable and nondurable
    by = {}
    for o in out:
        by.setdefault(o['ref'], {})[o['field']] = o
    for ref, d in by.items():
        try:
            okh = min(d['HRS_DUR']['value'], d['HRS_NDUR']['value']) - 0.05 <= d['HRS_MFG']['value'] <= \
                max(d['HRS_DUR']['value'], d['HRS_NDUR']['value']) + 0.05
            for f in d:
                d[f]['identity'] = 'ok' if okh else 'FAIL'
        except (TypeError, KeyError):
            pass
    return out

def find_c5_pages(doc):
    pages = []
    for pi, page in enumerate(doc):
        z = re.sub(r'\s+', '', page.get_text()).lower()
        if re.search(r'c-5[:;.]?averageweeklyhours,?seasona', z) and 'contents' not in z[:600]:
            pages.append(pi)
    return pages

FIELDS = ['issue', 'table', 'page', 'ref', 'occ', 'row_basis_label', 'month_inferred', 'field', 'basis', 'unit', 'value',
          'n_agree', 'n_valid', 'alts', 'readings', 'identity', 'flags', 'derived']

def main():
    idx = list(csv.DictReader(open(os.path.join(W, 'out', 'ee_pages_index.csv'))))
    fn = os.path.join(W, 'out', 'ee_fields_long.csv')
    done = set()
    if os.path.exists(fn):
        for r in csv.DictReader(open(fn)):
            done.add((r['issue'], r['table']))
    f = open(fn, 'a', newline='')
    w = csv.DictWriter(f, fieldnames=FIELDS)
    if not done:
        w.writeheader()
    lo, hi = (sys.argv[1], sys.argv[2]) if len(sys.argv) > 2 else ('1954-09', '1957-06')
    # employment
    for issue in sorted({r['issue'] for r in idx if r['table'] == 'EMP_SA' and lo <= r['issue'] <= hi}):
        if (issue, 'EMP') in done:
            continue
        doc = pymupdf.open(os.path.join(W, 'raw', 'ee', f'ee_{issue}.pdf'))
        pages = [int(r['page']) - 1 for r in idx if r['issue'] == issue and r['table'] == 'EMP_SA']
        best = None
        for pi in pages:
            page = doc[pi]
            txt = page.get_text()
            if len(re.findall(r'\d', txt)) < 60:
                continue
            clip = page.rect
            lines = group_lines(page.get_text('words'))
            nmonth = sum(1 for l in lines if l['w'] and month_of(l['w'][0][4]) and len(ints_in_line(l['w'])) >= 3)
            try:
                res = emp_month_layout(page, clip, issue) if nmonth >= 3 else emp_industry_layout(page, clip, issue)
            except Exception as e:
                res = []
            nok = sum(1 for o in res if o['identity'] == 'ok')
            if res and (best is None or nok > best[0]):
                best = (nok, pi, res, 'month_rows' if nmonth >= 3 else 'industry_rows')
        if best:
            _, pi, res, lay = best
            base = os.path.join(W, 'raw', 'ee_pages', f'ee_{issue}_EMPSA_p{pi+1:02d}')
            os.makedirs(os.path.dirname(base), exist_ok=True)
            nd = pymupdf.open(); nd.insert_pdf(doc, from_page=pi, to_page=pi); nd.save(base + '.pdf', garbage=3, deflate=True)
            open(base + '.txt', 'w').write(doc[pi].get_text())
            for o in res:
                if o['value'] is None:
                    continue
                w.writerow(dict(issue=issue, table='EMP', page=pi + 1, ref=o['ref'], occ=1, row_basis_label=lay,
                                month_inferred=o.get('month_inferred', 0), field=o['field'], basis='SA', unit='thousands',
                                value=o['value'], n_agree=o['n_agree'], n_valid=o['n_valid'],
                                alts=';'.join(str(a) for a in o['alts']),
                                readings='|'.join(f"{k}={'' if v is None else v}" for k, v, _ in o['readings']),
                                identity=o['identity'], flags='', derived=''))
            f.flush()
        print(issue, 'EMP', best[3] if best else None, best[0] if best else 0, flush=True)
    # hours
    lo2, hi2 = (sys.argv[3], sys.argv[4]) if len(sys.argv) > 4 else ('1960-07', '1962-02')
    for issue in sorted({r['issue'] for r in idx}):
        pass
    import glob
    for pdf in sorted(glob.glob(os.path.join(W, 'raw', 'ee', 'ee_*.pdf'))):
        issue = re.search(r'(\d{4}-\d{2})', pdf).group(1)
        if not (lo2 <= issue <= hi2) or (issue, 'HRS') in done:
            continue
        doc = pymupdf.open(pdf)
        pages = find_c5_pages(doc)
        best = None
        for pi in pages:
            page = doc[pi]
            words = page.get_text('words')
            # region: from the C-5 title line down to the next 'NOTE' / table title
            lines = group_lines(words)
            top = None
            bot = page.rect.y1
            for l in lines:
                z = re.sub(r'\s+', '', ' '.join(w[4] for w in l['w'])).lower()
                if top is None and re.search(r'c-5', z) and 'hours' in z:
                    top = l['yc'] - 5
                elif top is not None and l['yc'] > top + 30 and re.search(r'^note|^table|^1', z) and 'c-5' not in z:
                    bot = l['yc'] - 2
                    break
            if top is None:
                continue
            clip = pymupdf.Rect(page.rect.x0, top, page.rect.x1, bot)
            res = hours_layout(page, clip, issue)
            nok = sum(1 for o in res if o['identity'] == 'ok')
            if res and (best is None or nok > best[0]):
                best = (nok, pi, res)
        if best:
            _, pi, res = best
            base = os.path.join(W, 'raw', 'ee_pages', f'ee_{issue}_HRSSA_p{pi+1:02d}')
            nd = pymupdf.open(); nd.insert_pdf(doc, from_page=pi, to_page=pi); nd.save(base + '.pdf', garbage=3, deflate=True)
            open(base + '.txt', 'w').write(doc[pi].get_text())
            for o in res:
                if o['value'] is None:
                    continue
                w.writerow(dict(issue=issue, table='HRS', page=pi + 1, ref=o['ref'], occ=1, row_basis_label='C-5',
                                month_inferred=0, field=o['field'], basis='SA', unit='hours', value=o['value'],
                                n_agree=o['n_agree'], n_valid=o['n_valid'], alts=';'.join(str(a) for a in o['alts']),
                                readings='|'.join(f"{k}={'' if v is None else v}" for k, v, _ in o['readings']),
                                identity=o['identity'], flags='', derived=''))
            f.flush()
        print(issue, 'HRS', len(best[2]) if best else 0, best[0] if best else 0, flush=True)
    f.close()

if __name__ == '__main__':
    main()
