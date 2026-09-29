#!/usr/bin/env python3
"""Crawl every Philadelphia Fed Real-Time Data Set (RTDSM) variable page, record every data-file
link, and download the vintage matrices whose OBSERVATIONS are monthly (…MvMd.xlsx, …QvMd.xlsx),
plus first/second/third-release files, release-date files and per-variable documentation.
Quarterly-observation variables are logged (links in rtdsm_links.csv) but only ROUTPUT's matrix is
downloaded (real GNP/GDP, as a reference). Plain urllib UA, >=1.2 s between requests.
"""
import os, re, csv, time, html, urllib.request, urllib.parse

W = '/tmp/claude-0/-home-user/49f76bce-ebc7-5769-b106-ce7685453d86/scratchpad/collect/new_candidates'
D = os.path.join(W, 'raw', 'rtdsm'); P = os.path.join(D, 'pages'); F = os.path.join(D, 'files')
os.makedirs(P, exist_ok=True); os.makedirs(F, exist_ok=True)
BASE = 'https://www.philadelphiafed.org'
IDX = BASE + '/surveys-and-data/real-time-data-research/real-time-data-set-full-time-series-history'
SKIP = {'ads', 'atsix', 'gdpplus', 'livingston-survey', 'real-time-data-set-for-macroeconomists',
        'real-time-data-set-full-time-series-history'}
_last = [0.0]

def get(url, timeout=180):
    wait = 1.2 - (time.time() - _last[0])
    if wait > 0: time.sleep(wait)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.getcode(), r.read()
    except urllib.error.HTTPError as e:
        return e.code, b''
    except Exception as e:
        return 0, repr(e).encode()
    finally:
        _last[0] = time.time()

def page(slug):
    p = os.path.join(P, slug + '.html')
    if os.path.exists(p) and os.path.getsize(p) > 5000:
        return open(p, encoding='utf-8', errors='replace').read()
    code, b = get(BASE + '/surveys-and-data/real-time-data-research/' + slug)
    open(p, 'wb').write(b)
    return b.decode('utf-8', 'replace')

idx = page('real-time-data-set-full-time-series-history')
slugs = []
for m in re.finditer(r'real-time-data-research/([a-z0-9_-]+)', idx):
    s = m.group(1)
    if s not in slugs and s not in SKIP: slugs.append(s)

rows = []
for s in slugs:
    t = page(s)
    txt = html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', t)))
    title = re.search(r'Data Files - Real-Time Data Set \(([^)]+)\)\s+(.*?)\(\1\)', txt)
    name = title.group(2).strip() if title else ''
    vint = re.search(r'Vintages\s+(\d{4}:[MQ]\d+)\s+to present', txt)
    for m in re.finditer(r'href="([^"]+\.(?:xlsx|xls|pdf|txt|zip|csv))(\?[^"]*)?"', t, re.I):
        href = html.unescape(m.group(1))
        url = urllib.parse.urljoin(BASE + '/', href)
        fn = os.path.basename(href)
        kind = ('MvMd' if 'MvMd' in fn else 'QvMd' if 'QvMd' in fn else 'QvQd' if 'QvQd' in fn else
                'first_second_third' if 'first_second_third' in fn else
                'release_dates' if 'release' in fn.lower() else 'doc' if fn.lower().endswith('.pdf') else 'other')
        rows.append(dict(slug=s, name=name, first_vintage=vint.group(1) if vint else '', kind=kind,
                         file=fn, url=url))
    print(s, name, vint.group(1) if vint else '', flush=True)

seen = set(); uniq = []
for r in rows:
    if r['url'] in seen: continue
    seen.add(r['url']); uniq.append(r)
with open(os.path.join(D, 'rtdsm_links.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(uniq[0].keys())); w.writeheader(); w.writerows(uniq)

monthly_slugs = {r['slug'] for r in uniq if r['kind'] in ('MvMd', 'QvMd')}
log = open(os.path.join(D, 'download_log.csv'), 'a')
for r in uniq:
    want = (r['kind'] in ('MvMd', 'QvMd', 'release_dates') or
            (r['slug'] in monthly_slugs and r['kind'] in ('first_second_third', 'doc')) or
            (r['slug'] == 'routput' and r['kind'] in ('QvQd', 'first_second_third', 'doc')))
    if not want: continue
    sub = os.path.join(F, r['slug']); os.makedirs(sub, exist_ok=True)
    out = os.path.join(sub, r['file'])
    if os.path.exists(out) and os.path.getsize(out) > 1000: continue
    code, b = get(r['url'])
    ok = code == 200 and (b[:2] == b'PK' or b[:4] == b'%PDF' or b[:8] == bytes.fromhex('d0cf11e0a1b11ae1'))
    if ok: open(out, 'wb').write(b)
    log.write('%s,%s,%s,%d,%s\n' % (r['slug'], r['file'], code, len(b), 'ok' if ok else 'NOT_DATA'))
    log.flush(); print(code, len(b), r['slug'], r['file'], flush=True)

# Addendum run 2026-09-29: monthly vintages of quarterly real GNP/GDP (routputMvQd.xlsx), fetched by hand
# with curl after the crawl because the crawl's filter only took ROUTPUT's QvQd matrix:
#   curl -o raw/rtdsm/files/routput/routputMvQd.xlsx <url of routputMvQd.xlsx in rtdsm_links.csv>
