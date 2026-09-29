#!/usr/bin/env python3
"""Spokesman-Review archive: monthly story sitemaps (robots.txt-listed, Claude-User allowed) -> candidate
help-wanted stories -> raw HTML saved. Plain urllib, >=1.5 s between requests."""
import os, re, sys, time, json, urllib.request

W = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(W, 'raw', 'news', 'spokesman')
os.makedirs(os.path.join(D, 'sitemaps'), exist_ok=True)
os.makedirs(os.path.join(D, 'articles'), exist_ok=True)
last = [0.0]
CAND = re.compile(r'help-?wanted|want-?ads?|jobs?-ads?|classified-ads?-(for|jobs)|conference-board|job-market-(index|ads)|'
                  r'ads-for-workers|hiring-ads|employment-ads|job-advertis', re.I)


def get(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return open(dest, 'rb').read()
    dt = time.time() - last[0]
    if dt < 1.5:
        time.sleep(1.5 - dt)
    last[0] = time.time()
    for k in range(3):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                data = r.read()
            open(dest, 'wb').write(data)
            return data
        except Exception as e:
            print('ERR', url, e, file=sys.stderr); time.sleep(3 * (k + 1))
    return b''


def main():
    y0, y1 = int(sys.argv[1]), int(sys.argv[2])
    cands = []
    for y in range(y0, y1 + 1):
        for m in range(1, 13):
            p = f'{y}-{m:02d}'
            t = get(f'https://www.spokesman.com/sitemap-stories.xml?p={p}', os.path.join(D, 'sitemaps', f'sm_{p}.xml')).decode('utf8', 'replace')
            locs = re.findall(r'<loc>([^<]+)</loc>', t)
            hits = [u for u in locs if CAND.search(u.rstrip('/').split('/')[-1])]
            print(p, len(locs), len(hits), flush=True)
            cands += hits
    json.dump(cands, open(os.path.join(D, f'candidates_{y0}_{y1}.json'), 'w'), indent=0)
    for u in cands:
        slug = '_'.join(u.rstrip('/').split('/')[-4:])
        get(u, os.path.join(D, 'articles', slug + '.html'))


if __name__ == '__main__':
    main()
