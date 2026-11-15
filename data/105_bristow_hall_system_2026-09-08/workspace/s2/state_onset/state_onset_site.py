#!/usr/bin/env python3
"""The State Recession Chronology and Damage Grade on the site (14 November 2026; Anthony: "publish to the live site").
The page is built in collection 1032 (code/state_page_1032.py: 50 states dated as the nation is, on the Philadelphia Fed
state coincident index, graded on labor and output) and committed here as page.html. This step writes it over the stub
bhs_site.py writes at ../site/public/state-onset/, with the site's own masthead and footer (taken from the home page the
run has just built). It never fails the run: on any error the stub stays."""
import os, re, sys, traceback
H = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(H, '..', '..'))
SITE = os.path.abspath(os.path.join(WS, '..', 'site', 'public'))
PAGE = os.path.join(SITE, 'state-onset', 'index.html')


def main():
    t = open(os.path.join(H, 'page.html'), encoding='utf-8').read()
    assert 'const ALL = ' in t and len(t) > 1000000, 'page.html is not the built state page'
    home = os.path.join(SITE, 'index.html')
    if os.path.exists(home):            # one masthead and footer across the site
        h = open(home, encoding='utf-8').read()
        hd = re.search(r'<header class="bh">.*?</header>', h, re.S); ft = re.search(r'<div class="foot">.*?</div></div>', h, re.S)
        if hd:
            nav = hd.group(0).replace(' aria-current="page"', '').replace('href="/state-onset/"', 'href="/state-onset/" aria-current="page"')
            t = re.sub(r'<header class="bh">.*?</header>', lambda m: nav, t, count=1, flags=re.S)
        if ft:
            t = re.sub(r'<div class="foot">.*?</div></div>', lambda m: ft.group(0), t, count=1, flags=re.S)
    os.makedirs(os.path.dirname(PAGE), exist_ok=True)
    open(PAGE, 'w', encoding='utf-8').write(t)
    print('state page written:', PAGE, len(t))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        traceback.print_exc(); print('state page NOT written; the stub stays')
    sys.exit(0)
