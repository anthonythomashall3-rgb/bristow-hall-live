"""Parse 'months-in-rows / series-in-columns' tables (BCD "Basic data" tables, 1961-1990) for a given series
column (46 help-wanted index, 60 ratio) using pdfplumber word coordinates.

extract_col(page, series='46') -> list of dicts (month, value, mark, doubtful, raw_token, ...)
"""
import re
import statistics
from hwi_common import month_index, clean_num, clean_hwi, ym

YEAR_RE = re.compile(r"^[\W_]*([1Il!|])([9])([4-9])(\d)[\W_]*$")


def _yc(w):
    return (w['top'] + w['bottom']) / 2


def _xc(w):
    return (w['x0'] + w['x1']) / 2


def year_of(text):
    t = text.strip().strip('.,:;*')
    t = t.replace('I', '1').replace('l', '1').replace('!', '1').replace('|', '1').replace('O', '0').replace('o', '0')
    m = re.match(r'^(19[4-9]\d)$', t)
    return int(m.group(1)) if m else None


def find_header(words, series, H, W):
    """Locate the column header for `series`: a word '46.' / '46' followed by Index/Help/wanted text."""
    pat = re.compile(r'^[\W_]*' + series + r'[.,:]?$')
    cands = []
    for w in words:
        if not pat.match(w['text']):
            continue
        if w['top'] > H * 0.6:
            continue
        # nearby descriptive words
        near = [v for v in words if 0 <= v['top'] - w['top'] < 45 and -5 < v['x0'] - w['x0'] < 90]
        txt = ' '.join(v['text'] for v in sorted(near, key=lambda v: (round(v['top']), v['x0'])))
        key = 'help|wanted|wonted|advert' if series == '46' else 'ratio|help|wanted'
        if re.search(key, txt, re.I):
            cands.append((w, txt))
    return cands


class WordsPage:
    """Minimal stand-in for a pdfplumber page built from saved word boxes (raw/fraser/cand/*.words.json.gz)."""
    def __init__(self, rec):
        self.width, self.height = rec['width'], rec['height']
        self._w = [dict(text=w['t'], x0=w['x0'], x1=w['x1'], top=w['top'], bottom=w['bottom']) for w in rec['words']]

    def extract_words(self, **kw):
        return self._w


def extract_col(page, series='46', debug=False):
    words = page.extract_words(keep_blank_chars=False, x_tolerance=1.5, y_tolerance=2)
    H, W = page.height, page.width
    heads = find_header(words, series, H, W)
    out = []
    for hw, htxt in heads:
        # other column headers on the same header line: words like '47.' '45.' '41.'
        same = [w for w in words if abs(w['top'] - hw['top']) < 6 and re.match(r'^[\W_]*\d{1,3}[.,]$', w['text'])]
        xs = sorted(w['x0'] for w in same)
        right = [x for x in xs if x > hw['x0'] + 5]
        left = [x for x in xs if x < hw['x0'] - 5]
        if right:
            x_next = right[0]
        elif left:
            x_next = hw['x0'] + (hw['x0'] - left[-1])
        else:
            x_next = hw['x0'] + 60
        width = x_next - hw['x0']
        x_prev = left[-1] if left else hw['x0'] - width
        # stub: region left of the first column header
        stub_right = (xs[0] if xs else hw['x0']) - 2
        body = [w for w in words if w['top'] > hw['bottom'] + 10]
        years = sorted([(w, year_of(w['text'])) for w in body if w['x1'] < stub_right + 5 and year_of(w['text'])],
                       key=lambda t: t[0]['top'])
        if not years:
            out.append(dict(error='no year labels', header=htxt[:80]))
            continue
        # month labels in stub
        mlabs = [(w, month_index(w['text'])) for w in body if w['x1'] < stub_right + 5 and month_index(w['text'])]
        # blocks
        blocks = []
        for i, (yw, yr) in enumerate(years):
            y0 = _yc(yw)
            y1 = _yc(years[i + 1][0]) if i + 1 < len(years) else H
            ml = [(m, _yc(w)) for w, m in mlabs if y0 < _yc(w) < y1]
            blocks.append(dict(year=yr, y0=y0, y1=y1, ml=ml))
        # global pitch from month labels
        pitches = []
        offs = []
        for b in blocks:
            if len(b['ml']) >= 2:
                ms = [m for m, _ in b['ml']]; ys = [y for _, y in b['ml']]
                if len(set(ms)) >= 2:
                    mb = statistics.mean(ms); yb = statistics.mean(ys)
                    slope = sum((m - mb) * (y - yb) for m, y in b['ml']) / sum((m - mb) ** 2 for m in ms)
                    if slope > 0:
                        pitches.append(slope)
        pitch = statistics.median(pitches) if pitches else 9.0
        for b in blocks:
            if b['ml']:
                a = statistics.median([y - pitch * m for m, y in b['ml']])
            else:
                a = None
            b['a'] = a
            if a is not None:
                offs.append(a - b['y0'])
        off = statistics.median(offs) if offs else 0.0
        for b in blocks:
            if b['a'] is None:
                b['a'] = b['y0'] + off
        # row clusters from all numeric-looking tokens right of the stub
        numtoks = sorted(_yc(w) for w in body if w['x0'] > stub_right - 2 and clean_hwi(w['text']))
        clusters = []
        for y in numtoks:
            if clusters and y - clusters[-1][-1] < pitch * 0.45:
                clusters[-1].append(y)
            else:
                clusters.append([y])
        rows = [statistics.median(c) for c in clusters]
        rowmap = {}
        for b in blocks:
            rb = [y for y in rows if b['y0'] + pitch * 0.3 < y < b['y1'] - pitch * 0.3]
            # labelled rows
            lab = {}
            for m, yl in b['ml']:
                if rb:
                    j = min(range(len(rb)), key=lambda j: abs(rb[j] - yl))
                    if abs(rb[j] - yl) < pitch * 0.45:
                        lab[j] = m
            for j, y in enumerate(rb):
                if j in lab:
                    m = lab[j]; how = 'label'
                elif lab:
                    k = min(lab, key=lambda k: abs(k - j))
                    m_ord = lab[k] + (j - k)
                    m_geo = int(round((y - b['a']) / pitch))
                    m = m_ord if m_ord == m_geo else m_geo
                    how = 'ordinal' if m_ord == m_geo else 'geometry'
                else:
                    m = int(round((y - b['a']) / pitch)); how = 'geometry_nolabel'
                if 1 <= m <= 12:
                    rowmap[y] = (b['year'], m, how)
        lo = hw['x0'] - 0.25 * width
        hi = x_next - 0.12 * width
        toks = [w for w in body if lo <= _xc(w) <= hi]
        used = {}
        for w in toks:
            cn = clean_hwi(w['text'])
            if not cn:
                continue
            y = _yc(w)
            if not rowmap:
                continue
            ry = min(rowmap, key=lambda r: abs(r - y))
            if abs(ry - y) > pitch * 0.45:
                continue
            yr, m, how = rowmap[ry]
            v, mark, doubtful, s_ = cn
            tt = w['text']
            if re.match(r'^[\W_]*e', tt):
                mark = 'e'
            rec = dict(series=series, month=ym(yr, m), value=v, mark=mark, doubtful=doubtful or how.startswith('geometry'),
                       raw_token=tt, rowhow=how, header=htxt[:60], x=round(_xc(w)), y=round(y))
            k = rec['month']
            if k in used:
                rec['doubtful'] = True; used[k]['doubtful'] = True
                rec['note'] = 'dup_month'; used[k]['note'] = 'dup_month'
            used[k] = rec
            out.append(rec)
    return out


if __name__ == '__main__':
    import sys, json, pdfplumber
    with pdfplumber.open(sys.argv[1]) as pdf:
        for pn in sys.argv[2:]:
            for r in extract_col(pdf.pages[int(pn) - 1], sys.argv[3] if False else '46'):
                print(json.dumps(r))
