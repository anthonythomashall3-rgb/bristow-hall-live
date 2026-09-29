#!/usr/bin/env python3
"""News reports of The Conference Board help-wanted advertising index: fetch (curl, >=1.5 s per host),
save raw HTML, extract article text + date, and extract index values with regular expressions.
Every value comes from a regex match in the saved HTML text; the matched sentence is stored as evidence.
Output: work/news_cells.csv (all matches) and work/news_long.csv (deliverable schema).
"""
import os, re, sys, time, csv, html, hashlib, subprocess, datetime as dt
from urllib.parse import urlparse
import pandas as pd

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(W, 'raw', 'news', 'html')
os.makedirs(RAW, exist_ok=True)
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
          'November', 'December']
MON_ABBR = {m[:3].lower(): i + 1 for i, m in enumerate(MONTHS)}
MRE = '(' + '|'.join(MONTHS) + ')'
NUM = r'(\d{2,3}(?:\.\d)?)'
NOTPCT = r'(?!\s*(?:%|percent|per cent|\.\d))'
WEEKDAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
last_hit = {}


def fetch(url):
    h = hashlib.sha1(url.encode()).hexdigest()[:12]
    host = urlparse(url).netloc
    dest = os.path.join(RAW, f"{host.replace('www.', '')}_{h}.html")
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        return dest, 'cached'
    gap = 4.0 if 'editorandpublisher' in host else 1.5
    for attempt in range(3):
        t = last_hit.get(host, 0)
        if time.time() - t < gap:
            time.sleep(gap - (time.time() - t))
        last_hit[host] = time.time()
        r = subprocess.run(['curl', '-sS', '-L', '--max-time', '60', '-o', dest, '-w', '%{http_code}', url],
                           capture_output=True, text=True)
        code = r.stdout.strip()
        if code == '200':
            return dest, code
        time.sleep(8 * (attempt + 1))
    if os.path.exists(dest):
        os.rename(dest, dest + f'.http{code}')
    return dest + f'.http{code}', code


def page_text(path):
    t = open(path, encoding='utf8', errors='replace').read()
    raw = t
    t = re.sub(r'<script.*?</script>|<style.*?</style>|<noscript.*?</noscript>', ' ', t, flags=re.S | re.I)
    t = re.sub(r'<(br|p|div|li|h\d)[^>]*>', '\n', t, flags=re.I)
    t = re.sub(r'<[^>]+>', ' ', t)
    t = html.unescape(t)
    t = re.sub(r'[ \t\r\f\v]+', ' ', t)
    t = re.sub(r'\n\s*\n+', '\n', t)
    return raw, t


def article_date(url, raw, text):
    """Return (date, basis)."""
    m = re.search(r'/Archives/(\d{4})/(\d{2})/(\d{2})/', url)
    if m:
        return dt.date(*map(int, m.groups())), 'url_date'
    m = re.search(r'/stories/(\d{4})/([a-z]{3})/(\d{1,2})/', url)
    if m:
        return dt.date(int(m.group(1)), MON_ABBR[m.group(2)], int(m.group(3))), 'url_date'
    m = re.search(r'/news/(\d{4})/([a-z]{3})/(\d{1,2})/', url)
    if m:
        return dt.date(int(m.group(1)), MON_ABBR[m.group(2)], int(m.group(3))), 'url_date'
    m = re.search(r'inman\.com/(\d{4})/(\d{2})/(\d{2})/', url)
    if m:
        return dt.date(*map(int, m.groups())), 'url_date'
    m = re.search(r'-(\d{4})-(\d{1,2})-(\d{1,2})$', url)
    if m:
        return dt.date(*map(int, m.groups())), 'url_date'
    m = re.search(r'Posted \w+day, ' + MRE + r' (\d{1,2}), (\d{4})', text)
    if m:
        return dt.date(int(m.group(3)), MONTHS.index(m.group(1)) + 1, int(m.group(2))), 'page_posted_date'
    m = re.search(r'"datePublished"\s*:\s*"(\d{4})-(\d{2})-(\d{2})', raw) or \
        re.search(r'article:published_time"\s+content="(\d{4})-(\d{2})-(\d{2})', raw)
    if m:
        return dt.date(*map(int, m.groups())), 'page_metadata_date'
    return None, ''


def release_date(adate, text):
    """Infer the Conference Board release date from wording relative to the article date."""
    if adate is None:
        return None, ''
    t = text.lower()
    m = re.search(r'conference board[^.]{0,120}?\b(said|reported|announced|says|reports)\s+\(?(yesterday|today|'
                  + '|'.join(WEEKDAYS) + r')', t)
    if not m:
        m = re.search(r'\b(said|reported|announced)\s+(yesterday|today|' + '|'.join(WEEKDAYS) + r')[^.]{0,80}conference board', t)
    if not m:
        return None, ''
    w = m.group(2)
    if w == 'yesterday':
        return adate - dt.timedelta(days=1), 'text_yesterday'
    if w == 'today':
        return adate, 'text_today'
    k = WEEKDAYS.index(w)
    d = adate
    while d.weekday() != k:
        d -= dt.timedelta(days=1)
    return d, f'text_{w}'


def ref_month(month_name, adate):
    """Most recent month with this name ending before the article date."""
    mi = MONTHS.index(month_name) + 1
    y = adate.year
    if mi >= adate.month:
        y -= 1
    return f'{y:04d}-{mi:02d}'


PATTERNS = [
    ('current', re.compile(r'\b(?:to|at)\s+' + NUM + NOTPCT + r'\s*(?:points?\s*)?(?:in|for|during)\s+' + MRE + r'(?!\s+\d{4})', re.I), (2, 1)),
    ('current', re.compile(r'\b(?:in|for|during)\s+(?:the\s+month\s+of\s+)?' + MRE + r'(?:\s*,)?\s+to\s+' + NUM + NOTPCT, re.I), (1, 2)),
    ('current', re.compile(r'\bfor\s+the\s+month\s+of\s+' + MRE + r'\s+to\s+' + NUM + NOTPCT, re.I), (1, 2)),
    ('current', re.compile(MRE + r'\s+(?:index|reading|level)\s+(?:was|of|at|stood at)\s+' + NUM + NOTPCT, re.I), (1, 2)),
    ('current', re.compile(r'\bindex\b[^.]{0,60}?\b(?:unchanged|steady|flat)\s+at\s+' + NUM + NOTPCT + r'[^.]{0,40}?\bin\s+' + MRE, re.I), (2, 1)),
    ('current', re.compile(r'\bin\s+' + MRE + r'[^.]{0,60}?\b(?:unchanged|steady|flat)\s+at\s+' + NUM + NOTPCT, re.I), (1, 2)),
    ('current', re.compile(r'\b(?:unchanged|steady|flat)\s+in\s+' + MRE + r'\s+at\s+' + NUM + NOTPCT, re.I), (1, 2)),
    ('current', re.compile(r'\b(?:was|is|at|stood at|registered|reached|hit)\s+' + NUM + NOTPCT + r'\s+in\s+' + MRE + r'(?!\s+\d{4})', re.I), (2, 1)),
    ('current', re.compile(r'^\s*In\s+' + MRE + r',\s+[^.]{0,60}?\b(?:stood at|was|rose to|fell to|climbed to|dropped to)\s+' + NUM + NOTPCT, re.I), (1, 2)),
    ('current', re.compile(r'\bto\s+' + NUM + r'\s+percent\s+in\s+' + MRE, re.I), (2, 1)),  # 1990s UPI style "to 91 percent in April"
    ('prior', re.compile(r'\bfrom\s+(?:a\s+(?:revised\s+)?)?' + NUM + NOTPCT + r'\s+(?:points?\s+)?in\s+' + MRE + r'(?!\s+\d{4})', re.I), (2, 1)),
    ('prior', re.compile(r'\bfrom\s+a\s+revised\s+' + NUM + r'\s+percent\s+reading\s+in\s+' + MRE, re.I), (2, 1)),
    ('prior', re.compile(r'\bfrom\s+' + MRE + r"'s\s+(?:revised\s+)?" + NUM + NOTPCT, re.I), (1, 2)),
    ('prior', re.compile(r'\bindex\s+for\s+' + MRE + r'\s+was\s+' + NUM + NOTPCT, re.I), (1, 2)),
    ('prior', re.compile(r'\b' + MRE + r"'s\s+(?:revised\s+)?index\s+(?:stood at|was|of)\s+" + NUM + NOTPCT, re.I), (1, 2)),
    ('prior', re.compile(r'\b' + MRE + r"(?:'s)?\s+(?:revised\s+)?(?:index\s+)?(?:figure|reading|level)?\s*(?:of|was)\s+" + NUM + NOTPCT, re.I), (1, 2)),
    ('other', re.compile(r'\b(?:of|and)\s+' + NUM + NOTPCT + r'\s+in\s+' + MRE + r'(?!\s+\d{4})', re.I), (2, 1)),
]
# explicit month + year:  "was at 47 in December 2001", "the 41 of February 2003", "stood at 89 in July 1998"
EXPLICIT = re.compile(r'\b(?:at|was|of|to|the)\s+' + NUM + NOTPCT + r'\s+(?:in|of)\s+' + MRE + r'\s+(\d{4})', re.I)
LASTMONTH = re.compile(r'\b(?:at|to)\s+' + NUM + NOTPCT + r'\s+last\s+month', re.I)
PREVNAMED = re.compile(r'\b(?:at|was)\s+' + NUM + NOTPCT + r'\s+(?:for|in)\s+the\s+previous\s+' + MRE, re.I)
YEARAGO = [re.compile(r'\b(?:a|one)\s+year\s+(?:ago|earlier)[^.]{0,70}?\b(?:it\s+)?(?:was|at|stood at|of|registered|hovering at)\s+' + NUM + NOTPCT, re.I),
           re.compile(r'\b' + NUM + NOTPCT + r'\s+(?:a|one)\s+year\s+(?:ago|earlier)', re.I),
           re.compile(r'\b(?:from|compared with|versus|vs\.?)\s+' + NUM + NOTPCT + r'\s+(?:a|one)\s+year\s+(?:ago|earlier)', re.I),
           re.compile(r'\b' + NUM + NOTPCT + r'\s+(?:during|for|in)\s+the\s+same\s+month\s+(?:last|a)\s+year', re.I),
           re.compile(r'\bsame\s+(?:period|month)\s+last\s+year,?\s+the\s+index\s+(?:stood at|was)\s+' + NUM + NOTPCT, re.I),
           re.compile(r'\b' + NUM + r'\s+percent\s+reading\s+(?:reading\s+)?recorded\s+during\s+the\s+same\s+month\s+a\s+year\s+earlier', re.I),
           re.compile(r'\bat\s+' + NUM + NOTPCT + r',?\s+the\s+same\s+as\s+(?:a|one)\s+year\s+ago', re.I),
           re.compile(r'\bsame\s+level\s+it\s+was\s+the\s+year\s+before', re.I)]


def extract(text, adate):
    out = []
    # restrict to the article body: sentences mentioning the index (or adjacent)
    sents = re.split(r'(?<=[.!?])\s+|\n', text)
    for i, s in enumerate(sents):
        if not re.search(r'help[- ]wanted|index|advertising', s, re.I):
            continue
        if re.search(r'online|internet|web[- ]based|HWOL', s, re.I) and not re.search(r'print|newspaper', s, re.I):
            continue  # Help Wanted OnLine figures, not the newspaper index
        for role, pat, (gm, gv) in PATTERNS:
            for m in pat.finditer(s):
                mon, val = m.group(gm), float(m.group(gv))
                if not 20 <= val <= 200:
                    continue
                out.append(dict(role=role, month=ref_month(mon[0].upper() + mon[1:].lower(), adate), value=val,
                                evidence=s.strip()[:400]))
        for m in EXPLICIT.finditer(s):
            val = float(m.group(1))
            if 20 <= val <= 200:
                mon = m.group(2)[0].upper() + m.group(2)[1:].lower()
                out.append(dict(role='explicit', month=f'{int(m.group(3)):04d}-{MONTHS.index(mon) + 1:02d}', value=val,
                                evidence=s.strip()[:400]))
        for m in LASTMONTH.finditer(s):
            val = float(m.group(1))
            if 20 <= val <= 200:
                y, mo = adate.year, adate.month - 1
                if mo == 0:
                    y, mo = y - 1, 12
                out.append(dict(role='current', month=f'{y:04d}-{mo:02d}', value=val, evidence=s.strip()[:400]))
        for m in PREVNAMED.finditer(s):
            val = float(m.group(1))
            if 20 <= val <= 200:
                out.append(dict(role='year_ago', month=None, value=val, evidence=s.strip()[:400]))
        for pat in YEARAGO:
            for m in pat.finditer(s):
                if not m.groups():
                    continue
                val = float(m.group(1))
                if 20 <= val <= 200:
                    out.append(dict(role='year_ago', month=None, value=val, evidence=s.strip()[:400]))
    # year-ago month = current month - 12
    cur = [o for o in out if o['role'] == 'current']
    if cur:
        y, mo = map(int, cur[0]['month'].split('-'))
        for o in out:
            if o['role'] == 'year_ago':
                o['month'] = f'{y - 1:04d}-{mo:02d}'
    out = [o for o in out if o['month']]
    # de-duplicate identical (role, month, value)
    seen, res = set(), []
    for o in out:
        k = (o['role'], o['month'], o['value'])
        if k not in seen:
            seen.add(k); res.append(o)
    return res


def main():
    urls = list(csv.DictReader(open(os.path.join(W, 'scripts', 'news_urls.csv'))))
    rows, log = [], []
    for u in urls:
        path, status = fetch(u['url'])
        if not os.path.exists(path):
            log.append(dict(outlet=u['outlet'], url=u['url'], http=status, file='', is_hwi=False)); continue
        raw, text = page_text(path)
        is_hwi = bool(re.search(r'conference board', text, re.I) and re.search(r'help[- ]wanted', text, re.I))
        adate, dbasis = article_date(u['url'], raw, text)
        rdate, rbasis = release_date(adate, text) if is_hwi else (None, '')
        ex = extract(text, adate) if (is_hwi and adate) else []
        log.append(dict(outlet=u['outlet'], url=u['url'], http=status, file=os.path.basename(path), is_hwi=is_hwi,
                        article_date=adate, date_basis=dbasis, release_date=rdate, release_basis=rbasis, n=len(ex)))
        for e in ex:
            rows.append(dict(outlet=u['outlet'], url=u['url'], file=os.path.basename(path), article_date=adate,
                             article_date_basis=dbasis, release_date=rdate, release_basis=rbasis, **e))
        print(u['outlet'], adate, rdate, status, len(ex), flush=True)
    os.makedirs(os.path.join(W, 'work'), exist_ok=True)
    pd.DataFrame(log).to_csv(os.path.join(W, 'work', 'news_fetch_log.csv'), index=False)
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(W, 'work', 'news_cells.csv'), index=False)
    # IndustryWeek archive pages carry a 2005-01-13 import date, not the original date: the reference year of
    # month names cannot be resolved, so they are kept in news_cells.csv only.
    df = df[df.outlet != 'IndustryWeek'].copy()
    # one value per (article, month): prefer current > explicit > prior > year_ago > other
    rank = {'current': 0, 'explicit': 1, 'prior': 2, 'year_ago': 3, 'other': 4}
    df['r'] = df.role.map(rank)
    df = df.sort_values(['url', 'month', 'r']).drop_duplicates(['url', 'month'])
    if len(df):
        L = pd.DataFrame(dict(
            publication=df.outlet, issue=df.article_date.astype(str),
            publication_date=[(r if isinstance(r, dt.date) else a) for r, a in zip(df.release_date, df.article_date)],
            date_basis=[('conference_board_release_' + b) if isinstance(r, dt.date) else ('article_' + ab)
                        for r, b, ab in zip(df.release_date, df.release_basis, df.article_date_basis)],
            month=df.month, value=df.value, base='1987=100', sa_flag='SA', series='46', table='news_' + df.role,
            mark='', ocr_doubtful=False, raw_token=df.value.astype(str), source_url=df.url, page='',
            note='article_date ' + df.article_date.astype(str) + '; evidence: ' + df.evidence.str.slice(0, 200)))
        L['publication_date'] = L.publication_date.astype(str)
        L.to_csv(os.path.join(W, 'work', 'news_long.csv'), index=False)


if __name__ == '__main__':
    main()
