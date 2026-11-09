"""THE NATIONAL DISTURBANCE CHRONOLOGY on the live site (/disturbance/). Added 9 Nov 2026 (Anthony: "make the disturbance
indicator autoupdating forever"; the retrospective chronology replaces the real-time disturbance indicator, which is retired).
Research home: ~/Projects/Disturbance Indicator Data/10_chronology_site (definition, rulings, records).

Each run of the live system: download the six FRED series (fredgraph CSV, no key), re-date every episode with the fixed rule
(disturbance_chronology.py), and write ../site/public/disturbance/index.html with the site's own masthead and footer (taken
from the home page bhs_site.py has just written). The page that was built is kept as last_good_index.html. If anything
fails, the last good page is put back in place of the stub bhs_site.py writes, and the run goes on: this step never fails
the run. Run from the workspace directory, after bhs_site.py:  python3 s2/disturbance/disturbance_site.py"""
import json, os, re, shutil, subprocess, sys, traceback
H = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(H, '..', '..'))
SITE = os.path.abspath(os.path.join(WS, '..', 'site', 'public'))
PAGE = os.path.join(SITE, 'disturbance', 'index.html')
LAST = os.path.join(H, 'last_good_index.html')
OUT = os.path.join(H, 'out')


def build():
    r = subprocess.run([sys.executable, os.path.join(H, 'disturbance_chronology.py'), '--fred',
                        '--fred-dir', os.path.join(OUT, 'fred_latest'), '--out', OUT],
                       capture_output=True, text=True, timeout=600)
    if r.returncode != 0: raise RuntimeError('chronology failed: ' + r.stderr[-800:])
    J = json.load(open(os.path.join(OUT, 'chronology.json')))
    J.pop('data', None)
    n_dist = sum(e['status'].startswith('disturbance') for e in J['episodes'])
    if n_dist < 5 or len(J['deviation']['date']) < 900: raise RuntimeError('chronology output fails its sanity check')
    t = open(os.path.join(H, 'page_template.html'), encoding='utf-8').read()
    home = os.path.join(SITE, 'index.html')
    if os.path.exists(home):            # one masthead and footer across the site
        h = open(home, encoding='utf-8').read()
        hd = re.search(r'<header class="bh">.*?</header>', h, re.S); ft = re.search(r'<div class="foot">.*?</div></div>', h, re.S)
        if hd:
            nav = hd.group(0).replace(' aria-current="page"', '').replace('href="/disturbance/"', 'href="/disturbance/" aria-current="page"')
            t = re.sub(r'<header class="bh">.*?</header>', lambda m: nav, t, count=1, flags=re.S)
        if ft: t = re.sub(r'<div class="foot">.*?</div></div>', lambda m: ft.group(0), t, count=1, flags=re.S)
    html = t.replace('__DATA__', json.dumps(J, separators=(',', ':')).replace('</', '<\\/'))
    os.makedirs(os.path.dirname(PAGE), exist_ok=True)
    open(PAGE, 'w', encoding='utf-8').write(html)
    shutil.copyfile(PAGE, LAST)
    print('disturbance chronology: built, data through %s, %d disturbances' % (J['composite_last_month'], n_dist))


if __name__ == '__main__':
    try:
        build()
    except Exception as e:
        traceback.print_exc()
        if os.path.exists(LAST):
            os.makedirs(os.path.dirname(PAGE), exist_ok=True); shutil.copyfile(LAST, PAGE)
            print('disturbance chronology: NOT rebuilt (%s); last good page kept' % e)
        else:
            print('disturbance chronology: NOT rebuilt (%s); no last good page, the stub stands' % e)
    sys.exit(0)
