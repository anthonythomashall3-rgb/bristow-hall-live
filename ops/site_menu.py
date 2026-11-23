#!/usr/bin/env python3
"""ONE MENU FOR EVERY PAGE (16 Nov 2026). Each tool page used to carry its own copy of the menu, and the copies drifted: on 16 Nov
the State and stress-map pages still said "Damage Index" and "Chronology" after both had been replaced. This writes the masthead menu
and the footer links of every built page from ops/site_contract.json, marking the page's own entry. Runs after every page is written.
Standard library only; no AI. Usage: python3 ops/site_menu.py --site DIR"""
import os, re, sys, json, glob
C = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'site_contract.json'), encoding='utf-8'))
SITE = sys.argv[sys.argv.index('--site') + 1]
n = 0
for f in glob.glob(os.path.join(SITE, '**', '*.html'), recursive=True):
    t = open(f, encoding='utf-8').read()
    rel = os.path.relpath(f, SITE).replace(os.sep, '/')
    own = '/' if rel == 'index.html' else '/' + rel.split('/')[0] + '/' if '/' in rel else None
    nav = '\n' + ''.join('    <a href="%s"%s>%s</a>\n' % (h, ' aria-current="page"' if h == own else '', l) for h, l in C['nav']) + '  '
    foot = ''.join('<a href="%s">%s</a>' % (h, l) for h, l in C['footer'])
    t2 = re.sub(r'(<nav class="nav"[^>]*>).*?(</nav>)', lambda m: m.group(1) + nav + m.group(2), t, flags=re.S)
    t2 = re.sub(r'(<div class="links">).*?(</div>)', lambda m: m.group(1) + foot + m.group(2), t2, flags=re.S)
    # 1166 (23 Nov 2026): the site's name on every page (Anthony, 20 Nov 2026: the logo line and footer of every page read "Bristow-Hall
    # System"). The State page is built from an old copy of the national page and its footer still read BRISTOW-HALL BUSINESS CYCLE PROGRAM.
    for a, b in (('BRISTOW-HALL BUSINESS CYCLE PROGRAM', 'BRISTOW-HALL SYSTEM'), ('Bristow-Hall Business Cycle Program', 'Bristow-Hall System'),
                 ('<div class="l2">BUSINESS CYCLE PROGRAM</div>', '<div class="l2">SYSTEM</div>')):   # the logo's second line
        t2 = t2.replace(a, b)
    if t2 != t: open(f, 'w', encoding='utf-8').write(t2); n += 1
print('site menu: written on %d pages' % n)
