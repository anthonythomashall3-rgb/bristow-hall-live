"""Locate LF / EMP / HRS tables in an Economic Indicators issue and return the
table body region (page index, top y, bottom y)."""
import re
import pymupdf
from eicore import group_lines, month_of

def page_kind(text):
    n = re.sub(r'\s+', ' ', text).lower()
    kinds = []
    if (('persons 14 years' in n or 'persons, 14 years' in n or 'persons 14 years of age' in n
         or re.search(r'(thousands|millions) of persons', n))
            and ('labor force' in n) and ('unemploy' in n)):
        kinds.append('LF')
    if ((('wage and salary' in n) or ('thousands of employees' in n) or ('number of employees' in n))
            and 'manu' in n and ('thousands' in n or 'durable' in n or 'nonagri' in n) and 'hours per week' not in n):
        kinds.append('EMP')
    if re.search(r'hours per week', n) and ('manufactur' in n or 'manu-' in n or 'manu ' in n):
        kinds.append('HRS')
    return kinds

ANCHORS = {
    'LF': re.compile(r'(thousands|millions)\s+of\s+persons', re.I),
    'EMP': re.compile(r'(thousands\s+of\s+(wage|employees))|(wage\s+and\s+salary\s+workers)', re.I),
    'HRS': re.compile(r'hours\s+per\s+week', re.I),
}

def find_tables(doc):
    """Return dict kind -> list of (page_index, top, bottom)."""
    out = {}
    for pi, page in enumerate(doc):
        text = page.get_text()
        ks = page_kind(text)
        if not ks:
            continue
        words = page.get_text('words')
        lines = group_lines(words)
        monthy = []
        for l in lines:
            for w in l['w'][:4]:
                if month_of(w[4]) is not None and not re.search(r'\d', w[4][:1]):
                    monthy.append(l['yc'])
                    break
        for k in ks:
            cands = []
            for i, l in enumerate(lines):
                s = ' '.join(w[4] for w in l['w'])
                if ANCHORS[k].search(s):
                    if k == 'HRS' and 'HOURS PER WEEK' in s and '[' not in s:
                        continue  # chart axis label
                    cands.append(l['yc'])
            best = None
            for j, yc in enumerate(cands):
                nxt = cands[j + 1] if j + 1 < len(cands) else 1e9
                n = sum(1 for my in monthy if yc < my < nxt)
                if n >= 3 and (best is None or n > best[0]):
                    best = (n, yc)
            if best is None:
                continue
            out.setdefault(k, []).append((pi, best[1] + 2, page.rect.y1))
    return out
