#!/usr/bin/env python3
"""THE SITE CONTRACT (16 Nov 2026; Anthony: "make sure no issues like this ever happen again"). Runs after the site is built and
before it is published; a non-zero exit stops the publish, so the live site keeps its last good build and the run's message says why.
Checks, from ops/site_contract.json:
 1. every listed page exists and is not empty;
 2. every built page's masthead and footer menus are exactly the contract's, with no retired entry or link;
 3. the home page carries a card for every listed tool;
 4. every menu link and home-card link on every page leads to a built page or a redirect;
 5. files that must be rebuilt by every run (the forecaster's state) are fresh;
 6. nothing on the live site's menu is missing from this build unless the contract retires it (so a tool cannot vanish by accident).
Standard library only; no AI. Usage: python3 ops/site_contract.py --site DIR [--no-live]"""
import os, re, sys, json, glob, datetime as dt, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
C = json.load(open(os.path.join(HERE, 'site_contract.json'), encoding='utf-8'))
SITE = sys.argv[sys.argv.index('--site') + 1]
bad = []
def read(f): return open(f, encoding='utf-8', errors='replace').read()
def menus(t):
    return ''.join(re.findall(r'<header class="bh">.*?</header>', t, re.S) + re.findall(r'<div class="foot">.*?</div></div>', t, re.S))
def labels(m): return {re.sub(r'<[^>]+>', '', x).strip() for x in re.findall(r'<a [^>]*>(.*?)</a>', m, re.S)}

for p in C['pages']:
    f = os.path.join(SITE, p)
    if not os.path.exists(f) or os.path.getsize(f) < 200: bad.append('page missing or empty: /' + p)

redirects = set()
rf = os.path.join(SITE, '_redirects')
if os.path.exists(rf):
    for l in read(rf).splitlines():
        if l.split(): redirects.add(l.split()[0].rstrip('*').rstrip('/'))
def resolves(href):
    href = href.split('#')[0].split('?')[0]
    if not href.startswith('/') or href.startswith('//'): return True
    if href.rstrip('/') in redirects: return True
    f = os.path.join(SITE, href.lstrip('/'))
    return os.path.isfile(f) or os.path.isfile(os.path.join(f, 'index.html'))

pages = [f for f in glob.glob(os.path.join(SITE, '**', '*.html'), recursive=True)]
n_menu = 0
for f in pages:
    rel = '/' + os.path.relpath(f, SITE); t = read(f); m = menus(t)
    if not m: continue                      # a redirect stub or a bare file: no masthead to check
    n_menu += 1
    for cls, rx, want in (('masthead', r'<nav class="nav"[^>]*>(.*?)</nav>', C['nav']), ('footer', r'<div class="links">(.*?)</div>', C['footer'])):
        for blk in re.findall(rx, t, re.S):
            got = [[h, re.sub(r'<[^>]+>', '', l).strip()] for h, l in re.findall(r'<a href="([^"]+)"[^>]*>(.*?)</a>', blk, re.S)]
            if got != want: bad.append('%s: the %s menu is not the contract\'s (%s)' % (rel, cls, ', '.join(l for _, l in got)))
    for s in C['forbidden']:
        if s in m: bad.append('%s: the menu carries the retired entry %s' % (rel, s))
    for href in set(re.findall(r'href="([^"]+)"', m)):
        if not resolves(href): bad.append('%s: menu link %s leads nowhere' % (rel, href))
if n_menu < len([p for p in C['pages'] if p.endswith('.html')]): bad.append('only %d pages carry a masthead' % n_menu)

home = read(os.path.join(SITE, 'index.html')) if os.path.exists(os.path.join(SITE, 'index.html')) else ''
cards = re.findall(r"href:'([^']+)'", home)
for h in C['home_cards']:
    if h not in cards: bad.append('home page: no card for ' + h)
for h in cards:
    if not resolves(h): bad.append('home page: card link %s leads nowhere' % h)
for s in C['forbidden']:
    if s in home: bad.append('home page carries the retired entry ' + s)

for p, hrs in (C.get('fresh_hours') or {}).items():      # by the file's own "built" stamp (a checkout gives every file today's date)
    f = os.path.join(SITE, p)
    if '--no-fresh' in sys.argv or not os.path.exists(f): continue
    try:
        built = dt.datetime.strptime(json.load(open(f, encoding='utf-8'))['built'], '%Y-%m-%d %H:%M UTC').replace(tzinfo=dt.timezone.utc)
        age = (dt.datetime.now(dt.timezone.utc) - built).total_seconds() / 3600
        if age > hrs: bad.append('/%s was not rebuilt by this run (built %.1f hours ago; limit %d)' % (p, age, hrs))
    except Exception as e:
        bad.append('/%s carries no readable "built" stamp (%s)' % (p, e))

if '--no-live' not in sys.argv and home:
    try:
        live = urllib.request.urlopen(urllib.request.Request(C['live'], headers={'User-Agent': 'bristow-hall site contract'}), timeout=20).read().decode('utf-8', 'replace')
        gone = labels(menus(live)) - labels(menus(home)) - set(C['retired_menu'])
        for g in sorted(gone): bad.append('on the live menu but not in this build: "%s" (retire it in ops/site_contract.json if meant)' % g)
    except Exception as e:
        print('site contract: live menu not read (%s); the other checks stand' % e)

if bad:
    print('HOLD site contract: %d failure(s) - not published' % len(bad))
    for b in bad[:40]: print('  ' + b)
    sys.exit(1)
print('site contract: pass (%d pages with a masthead, %d cards)' % (n_menu, len(cards)))
