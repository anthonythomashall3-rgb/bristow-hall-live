"""Core helpers for parsing scanned statistical tables (Economic Indicators,
Employment and Earnings, MLR) from FRASER PDFs.

Two independent readings of every table row are produced:
  * 'txt'  : the PDF's own OCR text layer (FRASER, c. 2004), read with word boxes
  * 'tess' : a fresh tesseract OCR of the table region rendered at 450 dpi
Rows are keyed by reference month; numeric cells by x-position (right edge),
clustered into columns.
"""
import os, re, subprocess, tempfile
import pymupdf

MONTHS = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'mav': 5, 'jun': 6, 'juu': 6,
          'jul': 7, 'jui': 7, 'jnl': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}

FULLMONTHS = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august',
              'september', 'october', 'november', 'december']

def month_of(word):
    """Month number from an OCR'd month label word (tolerant), else None."""
    import difflib
    w = re.sub(r'[^a-z]', '', word.lower())
    # strip trailing dot-leader residue like 'ooo', 'eee', 'cena'
    if len(w) < 3:
        return None
    k = w[:3]
    if k in MONTHS:
        m = MONTHS[k]
        f = FULLMONTHS[m - 1]
        if len(w) <= len(f) + 3 and (len(w) <= 4 or f.startswith(w[:4]) or
                                     difflib.SequenceMatcher(None, w[:len(f)], f).ratio() >= 0.6):
            return m
        # long garbage after a month prefix: accept if the month name is a prefix
        if w.startswith(FULLMONTHS[m - 1][:4]):
            return m
    best, bm = 0.0, None
    for i, f in enumerate(FULLMONTHS):
        cand = w[:len(f) + 1]
        r = difflib.SequenceMatcher(None, cand, f).ratio()
        if r > best:
            best, bm = r, i + 1
    if best >= 0.75 and len(w) >= 4:
        return bm
    return None

YEAR_RE = re.compile(r'^(19[4-6][0-9OoSlI])\s*[:;*.,\-_]*\d?$')

def year_of(word):
    m = YEAR_RE.match(word.strip())
    if not m:
        return None
    y = m.group(1)
    y = y.replace('O', '0').replace('o', '0').replace('S', '5').replace('l', '1').replace('I', '1')
    try:
        return int(y)
    except ValueError:
        return None

OCR_MAP = str.maketrans({'O': '0', 'o': '0', 'Q': '0', 'D': '0', 'l': '1', 'I': '1', 'i': '1', '|': '1',
                         '!': '1', ']': '1', '[': '1', 'Z': '2', 'z': '2', 'B': '8', 'G': '6', 'b': '6',
                         'g': '9', 'q': '9', 'T': '7', '£': '5'})
AMBIG = set('Ss$')  # 3 or 5 or 8 -> ambiguous

def clean_num(raw):
    """Return (normalised string, flags). Keeps digits and , . separators."""
    flags = []
    s = raw.strip()
    s = s.strip('*•"\'`^~_-»«()—–:;')
    if any(c in AMBIG for c in s):
        flags.append('ambig_char')
        s = re.sub(r'[Ss$]', '?', s)
    s2 = s.translate(OCR_MAP)
    if s2 != s:
        flags.append('ocr_char_fix')
    s2 = s2.replace(' ', '')
    s2 = re.sub(r'[^0-9,.?*]', '', s2)
    s2 = s2.replace('*', ',')
    return s2, flags

def parse_value(s):
    """Classify a cleaned numeric string.
    Returns (value, kind) kind in {'int','dec1','dec2','bad'}; '?' -> bad."""
    if not s or '?' in s:
        return None, 'bad'
    s = s.strip(',.')
    if re.fullmatch(r'\d{1,3}[,.]\d{3}', s):
        return int(re.sub(r'[,.]', '', s)), 'int'
    if re.fullmatch(r'\d+', s):
        return int(s), 'int'
    if re.fullmatch(r'\d+[.,]\d', s):
        return float(s.replace(',', '.')), 'dec1'
    if re.fullmatch(r'\d+[.,]\d\d', s):
        return float(s.replace(',', '.')), 'dec2'
    return None, 'bad'

NUMISH = re.compile(r'^[\dOoQlI|!,.\-*•\'"`^~_()SsBZG$£]*\d[\dOoQlI|!,.\-*•\'"`^~_()SsBZG$£]*$')

def is_numish(t):
    return bool(NUMISH.match(t))

def merge_numeric(words, gap=7.5):
    """words: list of (x0,y0,x1,y1,text) sorted by x in one line.
    Merge 'NN,' + 'NNN' and 'N.' + 'N' fragments. Returns list of tokens
    dict(x0,x1,raw,text)."""
    toks = []
    for w in words:
        x0, y0, x1, y1, t = w[:5]
        if toks:
            p = toks[-1]
            g = x0 - p['x1']
            pr = p['raw']
            if g < gap and is_numish(t) and is_numish(pr):
                # merge when previous ends with separator or next starts with separator,
                # or thousands pattern 'd{1,3}' + 'ddd'
                prc, _ = clean_num(pr)
                tc, _ = clean_num(t)
                if (pr.rstrip()[-1:] in ',.' or t[:1] in ',.' or
                        (re.fullmatch(r'\d{1,2}', prc or '') and re.fullmatch(r'\d{3}', tc or '')) or
                        (re.fullmatch(r'\d{1,3}[,.]?', prc or '') and re.fullmatch(r'\d{3}', tc or '') and g < 4.5)):
                    p['raw'] = pr + ' ' + t
                    p['x1'] = x1
                    continue
        toks.append(dict(x0=x0, x1=x1, raw=t, y0=y0, y1=y1))
    return toks

def group_lines(words, ytol=3.2):
    ws = sorted(words, key=lambda w: ((w[1] + w[3]) / 2, w[0]))
    lines = []
    for w in ws:
        yc = (w[1] + w[3]) / 2
        if lines and abs(lines[-1]['yc'] - yc) <= ytol:
            lines[-1]['w'].append(w)
            n = len(lines[-1]['w'])
            lines[-1]['yc'] = (lines[-1]['yc'] * (n - 1) + yc) / n
        else:
            lines.append({'yc': yc, 'w': [w]})
    for l in lines:
        l['w'].sort(key=lambda w: w[0])
    return lines

def tesseract_words(page, clip, dpi=450, psm=6, derule=True):
    """OCR the clip region of a pymupdf page. Returns words in PDF coords."""
    pix = page.get_pixmap(dpi=dpi, clip=clip, colorspace=pymupdf.csGRAY)
    scale = dpi / 72.0
    with tempfile.TemporaryDirectory() as td:
        fn = os.path.join(td, 'p.png')
        if derule:
            import numpy as np
            from PIL import Image
            a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width).copy()
            dark = a < 128
            minrun = int(dpi * 0.2)  # 0.2 inch vertical run = rule line, not a glyph
            # vertical rules
            h, w = dark.shape
            run = np.zeros(w, dtype=np.int32)
            start = np.zeros(w, dtype=np.int32)
            for yy in range(h):
                row = dark[yy]
                run = np.where(row, run + 1, 0)
                # when a run ends (or at bottom) and is long, whiten it
                ended = (~row) & (prev_run >= minrun) if yy else np.zeros(w, bool)
                if yy:
                    for xx in np.nonzero(ended)[0]:
                        a[yy - prev_run[xx]:yy, max(0, xx - 1):xx + 2] = 255
                prev_run = run.copy()
            for xx in np.nonzero(prev_run >= minrun)[0]:
                a[h - prev_run[xx]:h, max(0, xx - 1):xx + 2] = 255
            Image.fromarray(a).save(fn)
        else:
            pix.save(fn)
        env = dict(os.environ, OMP_THREAD_LIMIT='1')
        out = subprocess.run(['tesseract', fn, 'stdout', '--psm', str(psm), '-c',
                              'preserve_interword_spaces=1', 'tsv'], capture_output=True, text=True,
                             env=env, timeout=300).stdout
    words = []
    for ln in out.splitlines()[1:]:
        parts = ln.split('\t')
        if len(parts) < 12 or parts[0] != '5':
            continue
        t = parts[11].strip()
        if not t:
            continue
        l, tp, w, h = [int(v) for v in parts[6:10]]
        x0 = clip.x0 + l / scale
        y0 = clip.y0 + tp / scale
        words.append((x0, y0, x0 + w / scale, y0 + h / scale, t, float(parts[10])))
    return words

def cluster_1d(xs, gap):
    xs = sorted(xs)
    cl = []
    for x in xs:
        if cl and x - cl[-1][-1] <= gap:
            cl[-1].append(x)
        else:
            cl.append([x])
    return cl
