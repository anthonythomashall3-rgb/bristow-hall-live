"""Parse 'series-in-rows / months-in-columns' tables (SCB C-pages "Business Cycle Indicators",
SCB S-pages "Current Business Statistics") using pdfplumber word coordinates.

extract_rows(pdf_path, page_no=0) -> list of dicts:
   series ('46' or '60'), month (YYYY-MM or 'annual'), value, mark (r/p), doubtful, raw_token, col_dist
"""
import re
import pdfplumber
from hwi_common import month_index, clean_num, ym

YEAR_RE = re.compile(r"^[\W_]*(19[4-9]\d|20[0-2]\d)[\W_]*[pr]?$")


def _yc(w):
    return (w['top'] + w['bottom']) / 2


def _xc(w):
    return (w['x0'] + w['x1']) / 2


def _line(words, y, tol):
    return sorted([w for w in words if abs(_yc(w) - y) <= tol], key=lambda w: w['x0'])


def header(words, H, y_row):
    """Return (columns, info) where columns = sorted list of (xc, label) with label 'YYYY-MM' or 'annual'."""
    anchors = [w for w in words if re.match(r'^(Year|Annual|Series|no\.?)$', w['text']) and w['top'] < y_row]
    if anchors:
        # anchor nearest above the row
        top = max(a['top'] for a in anchors if a['top'] < y_row)
        cand = [a for a in anchors if abs(a['top'] - top) < 25]
        top = min(a['top'] for a in cand)
    else:
        top = 0
    zone = [w for w in words if top - 3 <= w['top'] <= top + 32 and w['bottom'] < y_row]
    months = [w for w in zone if month_index(w['text'])]
    years = [w for w in zone if YEAR_RE.match(w['text'])]
    if len(months) < 3:
        return None, 'no month header'
    months.sort(key=_xc)
    # dedupe same-x
    md = []
    for w in months:
        if md and abs(_xc(md[-1]) - _xc(w)) < 8:
            continue
        md.append(w)
    months = md
    first_x = _xc(months[0])
    annual = sorted({round(_xc(w)) for w in years if _xc(w) < first_x - 8})
    ann = []
    for x in annual:
        if ann and abs(ann[-1] - x) < 10:
            continue
        ann.append(x)
    span = [(_xc(w), int(YEAR_RE.match(w['text']).group(1))) for w in years if _xc(w) >= first_x - 8]
    if span:
        last_year = max(span)[1]
    elif years:
        last_year = max(int(YEAR_RE.match(w['text']).group(1)) for w in years)
    else:
        return None, 'no year labels'
    cols = []
    cur = last_year
    for w in reversed(months):
        m = month_index(w['text'])
        cols.append((_xc(w), ym(cur, m)))
        if m == 1:
            cur -= 1
    cols.reverse()
    consecutive = all((int(b[1][:4]) * 12 + int(b[1][5:])) - (int(a[1][:4]) * 12 + int(a[1][5:])) == 1
                      for a, b in zip(cols, cols[1:]))
    allc = sorted([(x, 'annual') for x in ann] + cols)
    return allc, dict(consecutive=consecutive, n_annual=len(ann), n_months=len(cols))


def assign(nums, cols):
    xs = [_xc(w) for w in nums]
    cx = [c[0] for c in cols]
    best_off, best_cost = 0.0, 1e18
    for k in range(-40, 41):
        off = k * 0.5
        a = [min(range(len(cx)), key=lambda j: abs(cx[j] - (x - off))) for x in xs]
        cost = sum(abs(cx[j] - (x - off)) for j, x in zip(a, xs)) + 60 * (len(a) - len(set(a)))
        if cost < best_cost - 1e-9:
            best_cost, best_off = cost, off
    sp = sorted(b - a_ for a_, b in zip(cx, cx[1:]))
    spacing = sp[len(sp) // 2] if sp else 30
    out = []
    for w, x in zip(nums, xs):
        j = min(range(len(cx)), key=lambda j: abs(cx[j] - (x - best_off)))
        out.append((w, cols[j][1], abs(cx[j] - (x - best_off)), spacing, best_off))
    return out


def extract_rows(pdf_path, page_no=0):
    res = []
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_no]
        words = page.extract_words(keep_blank_chars=False, x_tolerance=1.5, y_tolerance=2)
        H, Wd = page.height, page.width
    anchors = [w for w in words if re.search(r'help|wanted|wonted', w['text'], re.I)]
    seen = set()
    for a in anchors:
        y = _yc(a)
        h = max(4.0, a['bottom'] - a['top'])
        line = _line(words, y, h * 0.6)
        txt = ' '.join(w['text'] for w in line)
        alpha = [w for w in line if re.search(r'[A-Za-z]{3,}', w['text'])]
        label_end = max(w['x1'] for w in alpha) if alpha else 0
        nums = [w for w in line if w['x0'] > label_end - 1 and clean_num(w['text']) and '=' not in w['text']]
        if len(nums) < 4:
            # S-page: heading "HELP-WANTED ADVERTISING", data on the following "Seasonally adjusted index" line
            ys = sorted({round(_yc(w), 1) for w in words if 0 < _yc(w) - y < 30})
            found = False
            for yb in ys:
                l2 = _line(words, yb, h * 0.6)
                t2 = ' '.join(w['text'] for w in l2)
                if re.search(r'season|adjusted|index', t2, re.I):
                    al2 = [w for w in l2 if re.search(r'[A-Za-z]{3,}', w['text'])]
                    le2 = max(w['x1'] for w in al2) if al2 else 0
                    n2 = [w for w in l2 if w['x0'] > le2 - 1 and clean_num(w['text']) and '=' not in w['text']]
                    if len(n2) >= 4:
                        line, txt, y, nums, found = l2, t2, yb, n2, True
                        break
            if not found:
                continue
        # drop base-year label pieces such as '1967' '100' or '1967—100' printed after the stub text
        while len(nums) >= 2 and re.match(r'^\(?19[4-9]\d(-\d\d)?$', nums[0]['text']) and re.match(r'^[=—-]?100\)?$', nums[1]['text']):
            nums = nums[2:]
        while nums and re.match(r'^\(?19[4-9]\d(-\d\d)?[=—-]+100\)?$', nums[0]['text']):
            nums = nums[1:]
        if round(y) in seen:
            continue
        seen.add(round(y))
        if re.search(r'ratio', txt, re.I):
            series = '60'
        elif re.search(r'display|executive', txt, re.I):
            continue
        else:
            series = '46'
        cols, info = header(words, H, y)
        if cols is None:
            res.append(dict(series=series, error=info, row=txt[:160],
                            tokens=[(round(_xc(w), 1), w['text']) for w in nums]))
            continue
        used = {}
        for w, lab, d, spacing, off in assign(nums, cols):
            v, mark, doubtful, s_ = clean_num(w['text'])
            rec = dict(series=series, month=lab, value=v, mark=mark, doubtful=doubtful, raw_token=w['text'],
                       col_dist=round(d, 1), offset=off, consecutive_header=info['consecutive'], row=txt[:160])
            if d > spacing * 0.35:
                rec['doubtful'] = True
                rec['note'] = 'far_from_column'
            if lab != 'annual' and lab in used:
                rec['doubtful'] = True
                rec['note'] = 'dup_column'
                used[lab]['doubtful'] = True
                used[lab]['note'] = 'dup_column'
            used[lab] = rec
            res.append(rec)
        filled = [k for k in used if k != 'annual']
        if len(filled) < info['n_months']:
            res.append(dict(series=series, warning=f"{info['n_months'] - len(filled)} of {info['n_months']} month cells empty",
                            row=txt[:160]))
    return res


if __name__ == '__main__':
    import sys, json
    for r in extract_rows(sys.argv[1]):
        print(json.dumps(r))
