"""JOLTS AS PRINTED, 2004-2010 (29 September 2026, cloud session; Anthony: "make sure that we collect all data that is real
real-time data").

Before this file the vacancy object read every month before July 2010 from the level file (the Petrosky-Nadeau and Zhang
reconstruction, then JOLTS as now published): values revised as late as 2026, read on days they did not exist. ALFRED's
vintages of JTSJOL start on 11 August 2010. The months between are in the Bureau's own news releases, every one of them
still on bls.gov: Table 1 of each release prints total nonfarm job openings, seasonally adjusted, for the month a year
before and the last six months. This script reads those tables and writes one row per printed value.

  jolts_asprinted_2004_2010/jolts_asprinted_2004_2010.csv   release, month, level (thousands, SA), rate, prelim (1 = the release's own month)

The first seasonally adjusted release is 15 April 2004 (February 2004): before it JOLTS was published not seasonally
adjusted (from 30 July 2002; the Bureau: "comparisons between consecutive months should not be used"), so no vacancy
object of the rule's kind can be read from JOLTS before February 2004. The release of 11 August 2010 is ALFRED's first
vintage; its printed months match ALFRED to the thousand (checked at every run of this script).

NOT WIRED INTO ANY TOOL. code/staged_wiring_for_v376_NOT_APPLIED.diff shows one way (written against v3.76, collection 105,
and withdrawn from it: the handoff's rule is that 105 is never written): one vintage per release day, each month at its
latest print on or before that day, a month not yet printed carrying its first print, the vacancy gap read on them from
February 2004. Check against the Mac's vacancy as printed (collections 522/523) before any use.

Usage: python3 code/jolts_asprinted.py [--fetch]    (--fetch reads the releases from bls.gov into jolts_asprinted_2004_2010/raw/;
without it the cached texts are parsed). Standard library only.
"""
import csv, datetime as dt, html, os, re, sys, time, urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # the inbox folder
RAW = os.path.join(HERE, 'jolts_asprinted_2004_2010', 'raw')
OUT = os.path.join(HERE, 'jolts_asprinted_2004_2010', 'jolts_asprinted_2004_2010.csv')
INDEX = 'https://www.bls.gov/bls/news-release/jolts.htm'
LAST = '20100811'   # ALFRED's first vintage of JTSJOL; later releases are ALFRED's
UA = os.environ.get('BLS_UA', '')   # bls.gov answers 403 to a request without a contact in its User-Agent; --fetch needs BLS_UA set
MON = {m: i for i, m in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'], 1)}


def _get(url):
    for i in range(4):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=60).read()
        except Exception as e:
            if i == 3: raise
            time.sleep(2 ** (i + 1))


def fetch():
    """Every release on the Bureau's archive page up to LAST: the history .txt to 2008, the archive .htm after."""
    if '@' not in UA: raise SystemExit('set BLS_UA to a User-Agent carrying a contact address (bls.gov refuses others)')
    os.makedirs(RAW, exist_ok=True)
    idx = _get(INDEX).decode('utf-8', 'replace')
    got = {}
    for href, m, d, y in re.findall(r'href="(/news\.release/(?:history|archives)/jolts_(\d{2})(\d{2})(\d{4})\.(?:txt|htm))"', idx):
        ymd = y + m + d
        if ymd > LAST: continue
        if ymd not in got or href.endswith('.txt'): got[ymd] = href
    for ymd, href in sorted(got.items()):
        dst = os.path.join(RAW, 'jolts_%s%s' % (ymd, os.path.splitext(href)[1]))
        if os.path.exists(dst) and os.path.getsize(dst) > 20000: continue
        b = _get('https://www.bls.gov' + href)
        if len(b) < 20000 or b'Table 1.' not in b: raise SystemExit('not a release: %s (%d bytes)' % (href, len(b)))
        open(dst, 'wb').write(b); time.sleep(1.2)
    return len(got)


def parse():
    rows, skipped = [], []
    for f in sorted(os.listdir(RAW)):
        if not f.startswith('jolts_'): continue
        ymd = f[6:14]; rel = dt.date(int(ymd[:4]), int(ymd[4:6]), int(ymd[6:]))
        t = open(os.path.join(RAW, f), encoding='latin-1').read()
        if f.endswith('.htm'): t = html.unescape(re.sub(r'<[^>]+>', '', t))
        i = t.find('Table 1.')
        if i < 0 or 'seasonally adjusted' not in t[i:i + 200]:
            skipped.append(f); continue      # the releases before 15 April 2004 carry no seasonally adjusted table
        L = t[i:i + 2500].splitlines()
        k = next(k for k, l in enumerate(L) if 'region' in l.lower() and re.search(r'\b(Jan|Feb|Mar|Apr|May|June|July|Aug|Sept|Oct|Nov|Dec)\b', l))
        ms = re.findall(r'(Jan|Feb|Mar|Apr|May|June|July|Aug|Sept|Oct|Nov|Dec)\.?', L[k])
        ys = re.findall(r'(\d{4})(p?)', L[k + 1])
        tot = next(l for l in L if re.match(r'\s*Total\s*(\(\s*4\s*\))?\s*\.', l))
        nums = re.findall(r'[\d,]*\.?\d+', re.sub(r'^\s*Total\s*(\(\s*4\s*\))?\s*\.*', '', tot))
        n = len(ms) // 2
        assert len(ms) == 2 * n and len(ys) == 2 * n and len(nums) == 2 * n, (f, len(ms), len(ys), len(nums))
        for j in range(n):
            assert ms[j] == ms[n + j] and ys[j] == ys[n + j], (f, 'levels and rates name different months')
            rows.append(dict(release=rel.isoformat(), month=dt.date(int(ys[j][0]), MON[ms[j][:3].lower()], 1).isoformat(),
                             level=int(nums[j].replace(',', '')), rate=float(nums[n + j]), prelim=int(ys[j][1] == 'p')))
    return rows, skipped


def check_alfred(rows):
    """The last release read is ALFRED's first vintage: every month it prints must match ALFRED's value."""
    root = os.path.realpath(os.path.join(HERE, '..'))   # the data root (Onset Detector Data)
    p = os.path.join(root, 'onset-detector-new-2026-08-23', '27_realtime_vintages', 'alfred_all_vintages', 'JTSJOL_all_vintages.csv')
    if not os.path.exists(p): return 'ALFRED vintage table not found; not checked'
    r = list(csv.reader(open(p))); col = r[0].index('JTSJOL_' + LAST)
    al = {row[0][:10]: row[col] for row in r[1:]}
    last = [x for x in rows if x['release'].replace('-', '') == LAST]
    bad = [(x['month'], x['level'], al.get(x['month'])) for x in last if al.get(x['month']) in (None, '', '.') or float(al[x['month']]) != x['level']]
    assert last and not bad, 'the release of %s does not match ALFRED: %s' % (LAST, bad)
    return 'the %d months of the release of %s match ALFRED' % (len(last), LAST)


if __name__ == '__main__':
    if '--fetch' in sys.argv: print('releases on the archive page up to %s: %d' % (LAST, fetch()))
    rows, skipped = parse()
    rows.sort(key=lambda x: (x['release'], x['month']))
    with open(OUT, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['release', 'month', 'level', 'rate', 'prelim']); w.writeheader(); w.writerows(rows)
    rels = sorted({x['release'] for x in rows})
    print('jolts as printed: %d values from %d releases (%s to %s); %d earlier releases not seasonally adjusted; %s'
          % (len(rows), len(rels), rels[0], rels[-1], len(skipped), check_alfred(rows)))
