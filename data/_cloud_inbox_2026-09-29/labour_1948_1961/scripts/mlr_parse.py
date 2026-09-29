#!/usr/bin/env python3
"""Monthly Labor Review (BLS) 1948 issues, 'Current Labor Statistics' text layer (single reading):
  Table A-1  civilian labor force, unemployment, employment (thousands, 14+, NSA): 13 month columns
  Table A-2  total nonagricultural wage and salary workers, manufacturing (thousands, NSA): 13 months
  Table C-1  average weekly hours, all manufacturing (NSA): month rows
Covers the months before Economic Indicators began (May 1948). Month columns are read from the printed
header (first month name = latest month). Output: out/mlr_fields_long.csv (same columns as EI fields).
"""
import csv, glob, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from eicore import month_of, clean_num

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def nums(tokens, n, kind='thou'):
    out = []
    for t in tokens:
        c, _ = clean_num(t)
        c = c.strip(',.')
        if kind == 'thou' and re.fullmatch(r'\d{1,2}[,.]\d{3}', c):
            out.append((int(re.sub(r'[,.]', '', c)), t))
        if len(out) == n:
            break
    return out

def header_months(block):
    """Month names in header order until the first data label."""
    ms = []
    for tok in re.findall(r'[A-Z][a-z]+(?:\s*[­-]\s*[a-z]+)?', block):
        w = re.sub(r'[­\-\s]', '', tok)
        m = month_of(w)
        if m and (not ms or ms[-1] != m or len(ms) > 11):
            ms.append(m)
    return ms

def refs_from(first_m, issue, n):
    iy, im = int(issue[:4]), int(issue[5:])
    y = iy if first_m < im else iy - 1
    out = []
    t = y * 12 + first_m - 1
    for k in range(n):
        out.append(f'{(t - k) // 12}-{(t - k) % 12 + 1:02d}')
    return out

def parse_issue(fn, issue, w):
    txt = open(fn).read()
    # re-join thousands split by the text layer: '15, 852' / '60. 870' -> '15,852'
    txt = re.sub(r'(?<![\d,.])(\d{1,2})\s?[,.]\s+(\d{3})(?!\d)', r'\1,\2', txt)
    rows = []
    # ---------------- A-1
    m = re.search(r'Table A\s*-\s*[l1I]\s*:\s*Estimated Total Labor Force', txt)
    if m:
        seg = txt[m.end(): m.end() + 6000]
        hdr_end = seg.find('Total, both sexes')
        ms = header_months(seg[:hdr_end if hdr_end > 0 else 800])
        if ms:
            refs = refs_from(ms[0], issue, 13)
            for label, field in (('Civilian labor force', 'CLF'), ('Unemployment', 'UNEMP'), ('Employment', 'EMP')):
                k = seg.find(label, hdr_end if hdr_end > 0 else 0)
                if k < 0:
                    continue
                vals = nums(seg[k + len(label):].split(), 13)
                for ref, (v, raw) in zip(refs, vals):
                    rows.append(('LF', ref, field, v, raw))
    # ---------------- A-2
    m = re.search(r'Table A\s*-\s*2\s*:\s*Estimated Number of (?:Wage and Salary Workers|Employees) in Nonagricultural', txt)
    if m:
        seg = txt[m.end(): m.end() + 4000]
        k0 = seg.find('Total estimated')
        ms = header_months(seg[:k0 if k0 > 0 else 600])
        if ms and k0 > 0:
            refs = refs_from(ms[0], issue, 13)
            for label, field in (('Total estimated employment', 'PAY'), ('anufacturing', 'MFG')):
                k = seg.find(label, k0 - 5)
                if k < 0:
                    continue
                vals = nums(seg[k + len(label):].split(), 13)
                for ref, (v, raw) in zip(refs, vals):
                    rows.append(('EMP', ref, field, v, raw))
    # ---------------- C-1 (month rows; all manufacturing = first earnings/hours/hourly triple)
    m = re.search(r'Table C\s*-\s*[l1I]\s*:\s*(?:Hours and Gross Earnings|Average Earnings and Hours|Flours)', txt)
    if m:
        seg = txt[m.end(): m.end() + 8000]
        lines = seg.split('\n')
        year = None
        prev_m = None
        for i, ln in enumerate(lines):
            s = ln.strip()
            my = re.match(r'^(19[34]\d)\s*:\s*(.*)$', s)
            if my:
                year = int(my.group(1))
                s = my.group(2)
            mm = re.match(r'^([A-Z][a-z]+)\.?[\s_.\-]*(\$?\s*\d.*)?$', s)
            if not mm:
                continue
            mo = month_of(mm.group(1))
            if not mo or year is None or 'verage' in s[:12] or year < 1946:
                continue
            if prev_m is not None and mo <= prev_m and not my:
                year += 1
            prev_m = mo
            rest = (mm.group(2) or '') + ' ' + ' '.join(lines[i + 1:i + 3])
            toks = re.findall(r'\$?\s?\d+[.,]\s?\d+', rest)
            if len(toks) >= 2:
                h = clean_num(toks[1])[0].replace(',', '.')
                try:
                    hv = float(h)
                except ValueError:
                    continue
                ref = f'{year}-{mo:02d}'
                iy, im = int(issue[:4]), int(issue[5:])
                if 36 <= hv <= 45 and ref < issue and ref >= f'{iy - 2}-01':
                    rows.append(('HRS', ref, 'HRS_MFG', hv, toks[1]))
    # identity check CLF = EMP + UNEMP
    by = {}
    for t, ref, f, v, raw in rows:
        by.setdefault((t, ref), {})[f] = v
    for t, ref, f, v, raw in rows:
        d = by[(t, ref)]
        idn = ''
        if t == 'LF' and all(k in d for k in ('CLF', 'EMP', 'UNEMP')):
            idn = 'ok' if abs(d['CLF'] - d['EMP'] - d['UNEMP']) <= 3 else 'FAIL'
        w.writerow(dict(issue=issue, table=t, page='', ref=ref, occ=1, row_basis_label='MLR text layer',
                        month_inferred=0, field=f, basis='NSA', unit='hours' if t == 'HRS' else 'thousands', value=v,
                        n_agree=1, n_valid=1, alts='', readings=f'txt={v}', identity=idn, flags='single_reading_mlr',
                        derived=''))
    for (t, ref), d in by.items():
        if t == 'LF' and 'CLF' in d and 'UNEMP' in d and abs(d['CLF'] - d.get('EMP', 0) - d['UNEMP']) <= 3:
            w.writerow(dict(issue=issue, table='LF', page='', ref=ref, occ=1, row_basis_label='MLR text layer',
                            month_inferred=0, field='UR', basis='NSA', unit='percent',
                            value=round(100.0 * d['UNEMP'] / d['CLF'], 1), n_agree='', n_valid='', alts='',
                            readings='', identity='', flags='', derived='100*UNEMP/CLF (rate not printed)'))
    return len(rows)

FIELDS = ['issue', 'table', 'page', 'ref', 'occ', 'row_basis_label', 'month_inferred', 'field', 'basis', 'unit', 'value',
          'n_agree', 'n_valid', 'alts', 'readings', 'identity', 'flags', 'derived']

def main():
    fn = os.path.join(W, 'out', 'mlr_fields_long.csv')
    with open(fn, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for t in sorted(glob.glob(os.path.join(W, 'raw', 'mlr_pages', 'mlr_*_sectionsAC.txt'))):
            issue = re.search(r'(\d{4}-\d{2})', t).group(1)
            if issue > '1948-06':
                continue
            n = parse_issue(t, issue, w)
            print(issue, n)

if __name__ == '__main__':
    main()
