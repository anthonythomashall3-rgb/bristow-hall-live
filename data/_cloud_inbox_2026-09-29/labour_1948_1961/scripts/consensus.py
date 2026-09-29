"""Cell-level consensus across OCR readings (text layer + tesseract variants).

Each reading's raw string is re-normalised for the column's type:
  'thou'  integer thousands (e.g. 61,296)
  'dec'   one-decimal number in [lo, hi] (rates, hours, millions)
Common scan/OCR defects handled deterministically (and flagged):
  missing decimal point  '44' -> 4.4 ; '399' -> 39.9
  rule-line artefact     '7,8761' -> 7,876 ; '3.71' -> 3.7
"""
import re
from collections import Counter
from eicore import clean_num

READERS = ['txt', 't300d', 't400']

def norm_reading(raw, ctype, lo=None, hi=None):
    """Return (value or None, flag)."""
    if raw is None or (isinstance(raw, float)) or str(raw).strip() == '' or str(raw) == 'nan':
        return None, ''
    c, fl = clean_num(str(raw))
    if not c or '?' in c:
        return None, 'unreadable'
    if ctype == 'thou' and re.match(r'^[,.]\d{3}$', c):
        return None, 'lost_leading_digit'
    c = c.strip(',.')
    if ctype == 'thou':
        if re.fullmatch(r'\d{1,3}[,.]\d{3}', c):
            return int(re.sub(r'[,.]', '', c)), ''
        if re.fullmatch(r'\d{1,3}', c):
            return int(c), ''
        if re.fullmatch(r'\d{4,5}', c):
            return int(c), 'no_sep'
        m = re.fullmatch(r'(\d{1,3})[,.](\d{3})\d', c)
        if m:
            return int(m.group(1) + m.group(2)), 'trail_digit_dropped'
        return None, 'unparsed'
    # decimal column
    m = re.fullmatch(r'(\d{1,3})[.,](\d)\d?', c)
    if m:
        v = float(m.group(1) + '.' + m.group(2))
        f = '' if len(c.split('.')[-1].split(',')[-1]) == 1 else 'trail_digit_dropped'
        if lo is not None and not (lo <= v <= hi):
            return None, 'out_of_range'
        return v, f
    m = re.fullmatch(r'\d{2,4}', c)
    if m:
        v = int(c) / 10.0
        if lo is not None and lo <= v <= hi:
            return v, 'decimal_point_inserted'
        # trailing rule artefact: '491' -> 4.9
        v2 = int(c[:-1]) / 10.0 if len(c) >= 3 else None
        if v2 is not None and lo is not None and lo <= v2 <= hi:
            return v2, 'decimal_point_inserted+trail_dropped'
        return None, 'out_of_range'
    if re.fullmatch(r'\d', c):
        return None, 'single_digit'
    return None, 'unparsed'

def vote(values):
    """values: list of (reader, value, flag). Return (best, n_agree, n_valid, alts)."""
    vals = [(r, v, f) for r, v, f in values if v is not None]
    if not vals:
        return None, 0, 0, []
    cnt = Counter(v for _, v, _ in vals)
    top = max(cnt.values())
    cands = [v for v, n in cnt.items() if n == top]
    if len(cands) > 1:
        # tie-break: text layer reading if among candidates
        txtv = [v for r, v, _ in vals if r == 'txt']
        best = txtv[0] if txtv and txtv[0] in cands else cands[0]
    else:
        best = cands[0]
    alts = sorted(set(v for _, v, _ in vals if v != best))
    return best, cnt[best], len(vals), alts
