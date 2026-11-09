"""THE NATIONAL DISTURBANCE CHRONOLOGY on the live site (/disturbance/). Added 9 Nov 2026 (Anthony: "make the disturbance
indicator autoupdating forever"; the retrospective chronology replaces the real-time disturbance indicator, which is retired).
Research home: ~/Projects/Disturbance Indicator Data/10_chronology_site (definition, rulings, records).

Each run of the live system: download the six FRED series (fredgraph CSV, no key), re-date every episode with the fixed rule
(disturbance_chronology.py), and write ../site/public/disturbance/index.html with the site's own masthead and footer (taken
from the home page bhs_site.py has just written). The page that was built is kept as last_good_index.html. Any change to the
episodes since the last run (the open episode closing, a new episode, a status or start that moved) is sent to the phone
through s2/alert.sh, the same path as the rule's own calls. If anything
fails, the last good page is put back in place of the stub bhs_site.py writes, and the run goes on: this step never fails
the run. Run from the workspace directory, after bhs_site.py:  python3 s2/disturbance/disturbance_site.py"""
import json, os, re, shutil, subprocess, sys, traceback
H = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(H, '..', '..'))
SITE = os.path.abspath(os.path.join(WS, '..', 'site', 'public'))
PAGE = os.path.join(SITE, 'disturbance', 'index.html')
LAST = os.path.join(H, 'last_good_index.html')
OUT = os.path.join(H, 'out')


KIND = {'disturbance_class1': 'disturbance', 'disturbance_class2': 'jobless-recovery disturbance', 'recession': 'recession window',
        'labor_bar_crossed_no_recession': 'labor bar crossed, no recession', 'fails_DD': 'too shallow', 'runup': 'run-up',
        'open_unsettled': 'open, not yet 1.0 point deep'}


def changes(old, new):
    """What changed in the episode list since the last run, in plain words; the open episode first."""
    o = {e['peak']: e for e in old}; n = {e['peak']: e for e in new}; msgs = []; closed = False
    for e in new:
        if e['open']:
            prev = [x for x in old if x['open']]
            if not prev: msgs.append('A new open episode since %s (%s).' % (e['peak'], KIND.get(e['status'], e['status'])))
            elif prev[0]['peak'] != e['peak']: msgs.append('The open episode now starts %s (was %s), %s.' % (e['peak'], prev[0]['peak'], KIND.get(e['status'], e['status'])))
            elif prev[0]['status'] != e['status']: msgs.append('The open episode since %s is now a %s (was %s).' % (e['peak'], KIND.get(e['status'], e['status']), KIND.get(prev[0]['status'], prev[0]['status'])))
    for k, e in n.items():
        if k in o and o[k]['open'] and not e['open']:
            closed = True; msgs.append('The episode open since %s CLOSED: trough %s, %s, grade %.2f.' % (k, e['trough'], KIND.get(e['status'], e['status']), e['grade']))
        elif k in o and not e['open'] and (o[k]['trough'], o[k]['status']) != (e['trough'], e['status']):
            msgs.append('%s..%s is now %s..%s, %s (was %s).' % (k, o[k]['trough'], k, e['trough'], KIND.get(e['status'], e['status']), KIND.get(o[k]['status'], o[k]['status'])))
        elif k not in o and not e['open']:
            msgs.append('New episode %s..%s, %s.' % (k, e['trough'], KIND.get(e['status'], e['status'])))
    for k, e in o.items():
        if k not in n and not e['open']: msgs.append('Episode %s..%s is no longer dated.' % (k, e['trough']))
    return closed, msgs


def build():
    prevf = os.path.join(OUT, 'chronology.json')
    prev = json.load(open(prevf))['episodes'] if os.path.exists(prevf) else None
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
    if prev is not None:
        closed, msgs = changes(prev, J['episodes'])
        if msgs:
            msg = ' '.join(msgs) + ' Data through %s. https://bhrrealtime.pages.dev/disturbance/' % J['composite_last_month']
            print('disturbance chronology: CHANGED:', msg)
            subprocess.run(['bash', os.path.join(WS, 's2', 'alert.sh'), 'DISTURBANCE EPISODE CLOSED' if closed else 'DISTURBANCE CHRONOLOGY CHANGED', msg], timeout=90)


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
