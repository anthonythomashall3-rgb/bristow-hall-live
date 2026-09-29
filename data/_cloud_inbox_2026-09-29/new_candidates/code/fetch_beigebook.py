#!/usr/bin/env python3
"""Fetch every Beige Book NATIONAL SUMMARY 1970-present from the Minneapolis Fed archive
(https://www.minneapolisfed.org/beige-book-reports/YYYY/YYYY-MM-su), probing every month (editions
are 8-12 a year and not on a fixed calendar). Keeps the extracted text and the publication date
printed on the page ('Beige Book <Month D, YYYY>'). Real time by construction: text is never revised.
A month with no edition returns 404 or a page without 'National Summary: <Month YYYY>' (soft 404).
Output: raw/beigebook/national_summaries.jsonl. >= 1.2 s between requests. Resume-safe.
"""
import os, re, json, time, html, datetime, urllib.request

W = '/tmp/claude-0/-home-user/49f76bce-ebc7-5769-b106-ce7685453d86/scratchpad/collect/new_candidates'
D = os.path.join(W, 'raw', 'beigebook'); os.makedirs(D, exist_ok=True)
OUT = os.path.join(D, 'national_summaries.jsonl')
MN = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
      'November', 'December']
done = set()
if os.path.exists(OUT):
    for ln in open(OUT):
        done.add(json.loads(ln)['slug'])
_last = [0.0]

def get(url):
    wait = 1.2 - (time.time() - _last[0])
    if wait > 0: time.sleep(wait)
    try:
        with urllib.request.urlopen(url, timeout=90) as r:
            return r.getcode(), r.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        return e.code, ''
    except Exception as e:
        return 0, ''
    finally:
        _last[0] = time.time()

today = datetime.date.today()
f = open(OUT, 'a')
for y in range(1970, today.year + 1):
    for m in range(1, 13):
        if (y, m) > (today.year, today.month): break
        slug = '%d-%02d-su' % (y, m)
        if slug in done: continue
        url = 'https://www.minneapolisfed.org/beige-book-reports/%d/%s' % (y, slug)
        c, t = get(url)
        if c != 200 or ('National Summary: %s %d' % (MN[m - 1], y)) not in t:
            f.write(json.dumps(dict(slug=slug, url=url, status=c, edition=False)) + '\n'); f.flush()
            continue
        body = re.sub(r'<script.*?</script>|<style.*?</style>', '', t, flags=re.S)
        s = html.unescape(re.sub(r'<[^>]+>', ' ', body)); s = re.sub(r'\s+', ' ', s)
        pd = re.search(r'Beige Book\s+((?:%s) \d{1,2}, \d{4})' % '|'.join(MN), s)
        i = s.find('National Summary: %s %d' % (MN[m - 1], y))
        end = s.find('Federal Reserve Bank of Minneapolis', i + 200)
        text = s[i:end if end > 0 else None]
        f.write(json.dumps(dict(slug=slug, url=url, status=c, edition=True,
                                pub_date=pd.group(1) if pd else '', n_chars=len(text), text=text)) + '\n')
        f.flush(); print(slug, pd.group(1) if pd else '?', len(text), flush=True)
