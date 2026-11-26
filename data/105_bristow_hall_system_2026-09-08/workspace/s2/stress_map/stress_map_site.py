#!/usr/bin/env python3
"""The National Stress Map on the site (15 November 2026; Anthony: "ENSURE THAT EVERYTHING IS LIVE UPDATING ... ALWAYS HAVE THE MOST RECENT DATA LIVE").
The page is built on the Mac in collection 1052 (code/stress_map_v2_1052.py --all: version 3.1, PREREG-1052 v3 with Amendment 1) and committed here as
page.html by the Mac job com.bristowhall.stressmap1052 only after every check passes. This step writes it over the stub bhs_site.py writes at
../site/public/stress-map/, with the site's own masthead (taken from the home page the run has just built), and draws the home card's picture
(thumb.svg: the nation's payroll-weighted mean State damage grade, recessions shaded). It never fails the run: on any error the stub stays."""
import os, re, sys, json, traceback
H = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(H, '..', '..'))
SITE = os.path.abspath(os.path.join(WS, '..', 'site', 'public'))
PAGE = os.path.join(SITE, 'stress-map', 'index.html')


def thumb(J, Wd=420, Hh=150, pad=5):
    y0, m0 = int(J['start'][:4]), int(J['start'][5:7]); n = J['n']; vals = [v / 100 for v in J['red']]
    idx = lambda k: (int(k[:4]) - y0) * 12 + int(k[5:7]) - m0
    X = lambda i: pad + i / max(1, n - 1) * (Wd - 2 * pad); top = max(4.0, max(vals)); Y = lambda v: Hh - pad - min(max(v, 0), top) / top * (Hh - 2 * pad)
    g = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" preserveAspectRatio="none">' % (Wd, Hh),
         '<defs><pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
         '<line x1="0" y1="0" x2="0" y2="6" stroke="#b9c0c7" stroke-width="2"/></pattern></defs>', '<rect width="%d" height="%d" fill="#fff"/>' % (Wd, Hh)]
    for b in (J.get('v2') or {}).get('bands', []):
        if b[0] not in ('R', 'RB'): continue
        a = X(max(0, idx(b[1]))); e = X(min(n - 1, idx(b[2]) if b[2] else n - 1))
        g.append('<rect x="%.1f" y="%d" width="%.1f" height="%d" fill="%s"/>' % (a, pad, max(1, e - a), Hh - 2 * pad, 'url(#hatch)' if b[0] == 'RB' else '#dcdcdc'))
    g.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="#FFCC00" stroke-width="1" vector-effect="non-scaling-stroke"/>' % (pad, Wd - pad, Y(2.0), Y(2.0)))
    g.append('<path d="%s" fill="none" stroke="#990000" stroke-width="1.3" vector-effect="non-scaling-stroke"/>' % ('M' + ' L'.join('%.1f %.1f' % (X(i), Y(v)) for i, v in enumerate(vals))))
    g.append('</svg>')
    return ''.join(g)


def main():
    t = open(os.path.join(H, 'page.html'), encoding='utf-8').read()
    m = re.search(r'<script id="data" type="application/json">(.*?)</script>', t, re.S)
    assert m and len(t) > 1000000, 'page.html is not the built stress map'
    J = json.loads(m.group(1).replace('<\\/', '</'))
    home = os.path.join(SITE, 'index.html')
    if os.path.exists(home):            # one masthead across the site
        h = open(home, encoding='utf-8').read()
        hd = re.search(r'<header class="bh">.*?</header>', h, re.S)
        if hd and re.search(r'<header class="bh">.*?</header>', t, re.S):
            nav = hd.group(0).replace(' aria-current="page"', '').replace('href="/stress-map/"', 'href="/stress-map/" aria-current="page"')
            t = re.sub(r'<header class="bh">.*?</header>', lambda _: nav, t, count=1, flags=re.S)
    # 26 Nov 2026 (1182; Anthony: "the 2024 recession shouldnt be shown"): the page built on the Mac still carries the program-dated
    # 2024 band (kind RB), its legend entry and its sentence. They are taken out here, whatever page.html holds.
    t = re.sub(r'\["RB",[^\]]*\],?', '', t)
    t = re.sub(r"<span>'\+sw\('RB'\)\+'[^<]*</span>", '', t)
    t = re.sub(r"\(NBER dates gray; the program's own dating from 2024 hatched, as on the live page: [^)]*\)", '(NBER dates gray)', t)
    if (J.get('v2') or {}).get('bands'): J['v2']['bands'] = [b for b in J['v2']['bands'] if b[0] != 'RB']
    os.makedirs(os.path.dirname(PAGE), exist_ok=True)
    t = t.replace('Bristow-Hall Business Cycle Program', 'Bristow-Hall System')      # the site's name since 18 November 2026 (1141); the page is built outside this step
    open(PAGE, 'w', encoding='utf-8').write(t)
    try:
        open(os.path.join(os.path.dirname(PAGE), 'thumb.svg'), 'w', encoding='utf-8').write(thumb(J))
    except Exception:
        traceback.print_exc(); print('stress map thumbnail NOT written')
    print('stress map page written:', PAGE, len(t), 'State layer through', J.get('last'), 'layers', (J.get('v2') or {}).get('thru'))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        traceback.print_exc(); print('stress map page NOT written; the stub stays')
    sys.exit(0)
