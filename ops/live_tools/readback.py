#!/usr/bin/env python3
"""LIVE TOOLS ON GITHUB (1052, 15 Nov 2026; no AI): after the site deploy, read the live pages back from https://bhrrealtime.pages.dev:
  /stress-map/  1052 code/page_check_1052.py stress, the layers' months must equal this run's build (--expect-thru)
  /state-onset/ 1052 code/page_check_1052.py state: all 50 States render (no script error, 1979 start, 0-10 axis, episode rows)
  /shadow/      the page's text equals the page this run committed (build stamps aside)
  /data/        every row name of s2/tool_inputs_mac.json is on the page
  home cards    every card's picture is the deploying build's (sha256 of /cards.json) and matches a fresh screenshot of the live tool page
Retries for up to 15 minutes (Cloudflare can take minutes). Writes $LT_OUT/readback.json; exit 1 if any check fails."""
import os, re, sys, json, time, subprocess, urllib.request
LIVE = 'https://bhrrealtime.pages.dev'; ROOT = os.path.expanduser('~/Projects/Onset Detector Data')
C52 = os.path.join(ROOT, '1052_stress_map_fix_parse_collect_2026-11-12'); CHECK = os.path.join(C52, 'code/page_check_1052.py')
WT = os.environ.get('GITHUB_WORKSPACE') or os.getcwd(); WS = 'data/105_bristow_hall_system_2026-09-08/workspace'; SITE = 'data/105_bristow_hall_system_2026-09-08/site/public'
OUTD = os.environ.get('LT_OUT') or '/tmp'
def get(path):
    req = urllib.request.Request(LIVE + path + ('&' if '?' in path else '?') + 'v=%d' % time.time(), headers={'User-Agent': 'Mozilla/5.0 (bristow-hall live-tools read-back)', 'Cache-Control': 'no-cache'})
    with urllib.request.urlopen(req, timeout=60) as r: return r.read().decode('utf-8', 'replace')
def text(h): return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', re.sub(r'(?s)<(script|style)[^>]*>.*?</\1>', ' ', h))).strip()
def main():
    want = sys.argv[1:] or ['stress', 'scale', 'state', 'shadow', 'data', 'cards']; R = {}
    page = open(os.path.join(WT, WS, 's2/stress_map/page.html')).read()
    thru = json.loads(re.search(r'<script id="data" type="application/json">(.*?)</script>', page, re.S).group(1).replace('<\\/', '</'))['v2']['thru']
    t0 = time.time()
    while True:
        R = {}
        if 'stress' in want:
            r = subprocess.run([sys.executable, CHECK, 'stress', LIVE + '/stress-map/?v=%d' % time.time(), '--expect-thru', json.dumps(thru)], capture_output=True, text=True, timeout=300)
            R['stress'] = json.loads(r.stdout.strip().splitlines()[-1]) if r.stdout.strip() else dict(ok=False, err=r.stderr[-300:])
        if 'state' in want:
            r = subprocess.run([sys.executable, CHECK, 'state', LIVE + '/state-onset/'], capture_output=True, text=True, timeout=900)
            R['state'] = json.loads(r.stdout.strip().splitlines()[-1]) if r.stdout.strip() else dict(ok=False, err=r.stderr[-300:])
        if 'shadow' in want:
            try:
                mine = text(open(os.path.join(WT, SITE, 'shadow/index.html')).read()); live = text(get('/shadow/'))
                body = lambda t: t[t.find(' Shadow '):][:3000]          # the page's own block (shadow_page_823.py), not the shared masthead
                R['shadow'] = dict(ok=body(mine) == body(live) and ' Shadow ' in live, chars=len(live))
            except Exception as e: R['shadow'] = dict(ok=False, err=f'{type(e).__name__} {e}'[:200])
        if 'data' in want:
            try:
                J = json.load(open(os.path.join(WT, WS, 's2/tool_inputs_mac.json'))); live = get('/data/')
                names = sorted({r.get('name') or r.get('series') or '' for t in J['tools'].values() for r in t['rows']} - {''})
                import html as _h
                miss = [n for n in names if not any(x in live for x in (n, _h.escape(n), _h.escape(n, quote=False), n.replace("'", '&#x27;')))]
                R['data'] = dict(ok=not miss, rows=len(names), missing=miss[:10])
            except Exception as e: R['data'] = dict(ok=False, err=f'{type(e).__name__} {e}'[:200])
        if 'scale' in want:   # Anthony 10:03 PT: the colour-scale end labels must sit within the bar's left and right edges
            try:
                from playwright.sync_api import sync_playwright
                with sync_playwright() as p_:
                    br = p_.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless=True); pg = br.new_page(viewport={'width': 1400, 'height': 1000})
                    pg.goto(LIVE + '/stress-map/?v=%d' % time.time(), wait_until='load'); pg.wait_for_function('window.__SM && window.__SM.ready', timeout=60000)
                    g = pg.evaluate("()=>{const b=document.getElementById('sbar').getBoundingClientRect(),s=document.querySelectorAll('#sticks span');"
                                    "const f=s[0].getBoundingClientRect(),l=s[s.length-1].getBoundingClientRect();return {bar:[b.left,b.right],first:[f.left,f.right,s[0].textContent],last:[l.left,l.right,s[s.length-1].textContent]}}")
                    br.close()
                R['scale'] = dict(ok=g['first'][0] >= g['bar'][0] - 0.5 and g['last'][1] <= g['bar'][1] + 0.5, **g)
            except Exception as e: R['scale'] = dict(ok=False, err=f'{type(e).__name__} {e}'[:200])
        if 'cards' in want:   # the home cards: each the picture the deploying build took, matching the live tool page now (s2/card_shots.py --readback)
            r = subprocess.run([sys.executable, 's2/card_shots.py', '--readback'], cwd=os.path.join(WT, WS), capture_output=True, text=True, timeout=900)
            try: R['cards'] = json.load(open(os.path.join(WT, WS, 'out', 'cards_readback.json')))
            except Exception: R['cards'] = dict(ok=False, err=(r.stdout + r.stderr)[-300:])
        ok = all(v.get('ok') for v in R.values())
        if ok or time.time() - t0 > 900: break
        print('read-back not yet right:', {k: v.get('ok') for k, v in R.items()}, flush=True); time.sleep(60)
    R['ok'] = ok; json.dump(R, open(os.path.join(OUTD, 'readback.json'), 'w'), indent=1, default=str)
    print(json.dumps({k: (v.get('ok') if isinstance(v, dict) else v) for k, v in R.items()}))
    return 0 if ok else 1
if __name__ == '__main__': sys.exit(main())
