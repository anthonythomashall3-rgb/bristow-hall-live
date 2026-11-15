#!/usr/bin/env python3
"""The State Recession Chronology and Damage Grade on the site (14 November 2026; Anthony: "publish to the live site").
The page is built in collection 1032 (code/state_page_1032.py: 50 states dated as the nation is, on the Philadelphia Fed
state coincident index, graded on labor and output) and committed here as page.html. This step writes it over the stub
bhs_site.py writes at ../site/public/state-onset/, with the site's own masthead (taken from the home page the
run has just built). It never fails the run: on any error the stub stays."""
import os, re, sys, traceback
H = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(H, '..', '..'))
SITE = os.path.abspath(os.path.join(WS, '..', 'site', 'public'))
PAGE = os.path.join(SITE, 'state-onset', 'index.html')


def thumb(t, Wd=420, Hh=150, pad=5):
    """The home page card's picture: the chart the page opens on (California), drawn as the page draws it - the damage
    grade on 0 to 10, recessions shaded gray, disturbances hatched - from the page's own data. Written each run."""
    import json
    A = json.loads(re.search(r'const ALL = (\{.*?\});\n', t, re.S).group(1))
    dft = re.search(r'return ALL\[k\]\?k:"([A-Z]{2})"', t); S = A[dft.group(1) if dft else 'CA']
    mk = [m[:7] for m in S['series']['dates']]; vals = S['series']['values']; n = len(mk)
    X = lambda i: pad + i / max(1, n - 1) * (Wd - 2 * pad); Y = lambda v: Hh - pad - min(max(v, 0), 10) / 10 * (Hh - 2 * pad)
    pos = lambda m: mk.index(m) if m in mk else (0 if m < mk[0] else n - 1)
    g = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" preserveAspectRatio="none">' % (Wd, Hh),
         '<defs><pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
         '<line x1="0" y1="0" x2="0" y2="6" stroke="#b9c0c7" stroke-width="2"/></pattern></defs>', '<rect width="%d" height="%d" fill="#fff"/>' % (Wd, Hh)]
    for v in (2, 4, 6, 8, 10):
        g.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="#e3e6ea" stroke-width="1" vector-effect="non-scaling-stroke"/>' % (pad, Wd - pad, Y(v), Y(v)))
    for r in S['nber']:
        a, b = X(pos(r['peak'])), X(pos(r['trough']))
        if r['prov']:
            g.append('<rect x="%.1f" y="%d" width="%.1f" height="%d" fill="url(#hatch)" stroke="#9aa3ad" stroke-width="1" vector-effect="non-scaling-stroke"/>' % (a, pad, max(2, b - a), Hh - 2 * pad))
        else:
            g.append('<rect x="%.1f" y="%d" width="%.1f" height="%d" fill="#dcdcdc"/>' % (a, pad, max(1, b - a), Hh - 2 * pad))
    pts = [(X(i), Y(v)) for i, v in enumerate(vals) if v is not None]
    g.append('<path d="%s" fill="none" stroke="#990000" stroke-width="1.3" vector-effect="non-scaling-stroke"/>' % ('M' + ' L'.join('%.1f %.1f' % p for p in pts)))
    g.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="#c9ced4" stroke-width="1" vector-effect="non-scaling-stroke"/></svg>' % (pad, Wd - pad, Y(0), Y(0)))
    return ''.join(g)


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
        # the footer is NOT swapped: the first 'foot' block in this page is the chart's own (it holds the legend and the full-screen button)
    os.makedirs(os.path.dirname(PAGE), exist_ok=True)
    open(PAGE, 'w', encoding='utf-8').write(t)
    try:
        open(os.path.join(os.path.dirname(PAGE), 'thumb.svg'), 'w', encoding='utf-8').write(thumb(t))
    except Exception:
        traceback.print_exc(); print('state thumbnail NOT written')
    print('state page written:', PAGE, len(t))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        traceback.print_exc(); print('state page NOT written; the stub stays')
    sys.exit(0)
