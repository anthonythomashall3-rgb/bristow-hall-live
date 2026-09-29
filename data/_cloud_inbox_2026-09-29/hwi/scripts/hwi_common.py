"""Shared helpers for parsing printed help-wanted index tables (BCD / SCB)."""
import re

MONTHS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
MONTH_RE = re.compile(r'^[\W_]*(jan|feb|mar|apr|may|june?|july?|aug|sept?|oct|nov|dec)[a-z]*\.?[\W_]*$', re.I)

# OCR confusions for digits
SUBS = {'!': '1', 'l': '1', 'I': '1', '|': '1', 'i': '1', 'O': '0', 'o': '0', 'Q': '0', 'D': '0',
        'S': '5', 's': '5', 'B': '8', 'Z': '2', 'z': '2', 'g': '9', 'G': '6', '?': '7', 'J': '1', ']': '1', '[': '1'}


def month_index(tok):
    m = MONTH_RE.match(tok.strip())
    if not m:
        return None
    k = m.group(1).lower()[:3]
    return MONTHS.index(k) + 1


def clean_num(tok, allow_decimal=True):
    """Return (value, mark, doubtful, cleaned) or None when the token is not numeric-ish.
    mark: 'r' revised / 'p' preliminary (as printed superscripts, OCR'd as r, p, ', ", etc.)"""
    t = tok.strip()
    if not t:
        return None
    mark = ''
    doubtful = False
    # leading markers
    m = re.match(r"^([rRpP'\"`‘’“”*®©•♦@®]+)(.*)$", t)
    if m and m.group(2) and (m.group(2)[0].isdigit() or m.group(2)[0] in '!lI|.'):
        lead = m.group(1)
        if 'r' in lead.lower() or "'" in lead or '‘' in lead or '’' in lead:
            mark = 'r'
        if 'p' in lead.lower() or '"' in lead or '“' in lead or '”' in lead:
            mark = 'p'
        t = m.group(2)
    # trailing junk
    t = re.sub(r"[,;:'\"`’”)\]]+$", '', t)
    if not t:
        return None
    # must be mostly digits
    digits = sum(c.isdigit() for c in t)
    if digits == 0 or digits < len(t.replace('.', '')) - 1:
        return None
    out = []
    for c in t:
        if c.isdigit() or c == '.':
            out.append(c)
        elif c in SUBS:
            out.append(SUBS[c]); doubtful = True
        elif c == ',':
            continue
        else:
            return None
    s = ''.join(out)
    if s.count('.') > 1 or s in ('', '.'):
        return None
    if s.startswith('.'):
        s = '0' + s
    try:
        v = float(s)
    except ValueError:
        return None
    if not allow_decimal and '.' in s:
        doubtful = True
    return v, mark, doubtful, s


def ym(y, m):
    return f'{y:04d}-{m:02d}'


def clean_hwi(tok, max_int_digits=3):
    """Lenient cleaner for index values printed in BCD tables (OCR noise, circled high/low markers,
    r/p/e superscripts). Returns (value, mark, doubtful, cleaned) or None."""
    t = tok.strip()
    t = re.sub(r"[-—–.,;:'\"*`’”)\]}]+$", '', t)
    if not t:
        return None
    m = re.search(r"([rpeRP])?\s*([\d!lI|]{1,%d}(?:[.,]\d{1,3})?)$" % max_int_digits, t)
    if not m:
        m2 = re.search(r"([rpeRP])?\s*(\.\d{2,3})$", t)  # ratios like .688
        if not m2:
            return None
        m = m2
    mark = (m.group(1) or '').lower()
    core = m.group(2).replace(',', '.')
    prefix = t[:m.start()]
    doubtful = False
    digits = ''.join('1' if c in '!lI|' else c for c in core)
    if digits != core:
        doubtful = True
    if prefix:
        # junk before the number (circled high/low markers etc.); if prefix ends with a digit the number may be truncated
        if re.search(r'\d$', prefix):
            doubtful = True
        if re.search(r"[rR]$|'$|‘$|’$", prefix):
            mark = mark or 'r'
        if re.search(r'"$|“$|”$', prefix):
            mark = mark or 'p'
    if not re.search(r'\d', core):
        return None
    if core.startswith('.'):
        digits = '0' + digits
    try:
        v = float(digits)
    except ValueError:
        return None
    # the whole token must not be mostly letters
    letters = sum(c.isalpha() for c in t)
    if letters > 4:
        doubtful = True
    return v, mark, doubtful, digits
