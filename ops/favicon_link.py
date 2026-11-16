"""Put the BH favicon link into every page of the built site (16 Nov 2026).
Chrome keeps a remembered "no icon" for a site unless a page names its icon, so each page names it.
Usage: python3 ops/favicon_link.py <site/public>. Adds the tags once (a page that has them is left alone)."""
import os, sys, re
TAG = '<link rel="icon" href="/favicon.ico?v=1" sizes="any">\n<link rel="apple-touch-icon" href="/apple-touch-icon.png">\n'
root = sys.argv[1]; n = 0
for d, _, fs in os.walk(root):
    for f in fs:
        if not f.endswith('.html'): continue
        p = os.path.join(d, f); t = open(p, encoding='utf-8').read()
        if 'rel="icon"' in t: continue
        m = re.search(r'<head[^>]*>\s*', t, re.I)
        if not m: continue
        open(p, 'w', encoding='utf-8').write(t[:m.end()] + TAG + t[m.end():]); n += 1
print('favicon link: added to %d page(s)' % n)
