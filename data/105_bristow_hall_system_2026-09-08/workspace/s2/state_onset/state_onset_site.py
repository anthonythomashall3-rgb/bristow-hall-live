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
    """The home page card's picture: the share of the 50 states in a recession (shaded red) and in a disturbance (lined
    blue above it), month by month since 1979, read from the page's own data. Written beside the page each run."""
    import json
    A = json.loads(re.search(r'const ALL = (\{.*?\});\n', t, re.S).group(1)); n = len(A)
    months = A[sorted(A)[0]]['series']['dates']; mk = [m[:7] for m in months]; ix = {m: i for i, m in enumerate(mk)}
    rec = [0] * len(mk); dis = [0] * len(mk)
    for v in A.values():
        r_ = [0] * len(mk); d_ = [0] * len(mk)
        for p in v['nber']:
            if p.get('nested'): continue
            for m in mk:
                if p['peak'] < m <= p['trough']:
                    (r_ if p['cls'] == 'recession' else d_)[ix[m]] = 1
        for i in range(len(mk)):
            rec[i] += r_[i]; dis[i] += d_[i] if not r_[i] else 0
    X = lambda i: pad + i / max(1, len(mk) - 1) * (Wd - 2 * pad); Y = lambda v: Hh - pad - v / n * (Hh - 2 * pad)
    top = [rec[i] + dis[i] for i in range(len(mk))]
    area = lambda lo, hi: 'M' + ' L'.join('%.1f %.1f' % (X(i), Y(hi[i])) for i in range(len(mk))) + ' L' + ' L'.join('%.1f %.1f' % (X(i), Y(lo[i])) for i in reversed(range(len(mk)))) + ' Z'
    zero = [0] * len(mk)
    g = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" preserveAspectRatio="none">' % (Wd, Hh),
         '<defs><pattern id="d" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
         '<rect width="1.6" height="5" fill="#1f4e79" fill-opacity=".45"/></pattern></defs>', '<rect width="%d" height="%d" fill="#fff"/>' % (Wd, Hh)]
    for frac in (0.5, 1.0):
        g.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="#e3e6ea" stroke-width="1" vector-effect="non-scaling-stroke"/>' % (pad, Wd - pad, Y(frac * n), Y(frac * n)))
    g.append('<path d="%s" fill="url(#d)" stroke="none"/>' % area(rec, top))
    g.append('<path d="%s" fill="#990000" fill-opacity=".18" stroke="none"/>' % area(zero, rec))
    g.append('<path d="%s" fill="none" stroke="#990000" stroke-width="1.1" vector-effect="non-scaling-stroke"/>' % ('M' + ' L'.join('%.1f %.1f' % (X(i), Y(rec[i])) for i in range(len(mk)))))
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
