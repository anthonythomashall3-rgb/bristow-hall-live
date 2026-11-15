#!/usr/bin/env python3
"""LIVE TOOLS ON GITHUB (1052, 15 Nov 2026; no AI): after the site deploy, read the live pages back from https://bhrrealtime.pages.dev:
  /stress-map/  1052 code/page_check_1052.py stress, the layers' months must equal this run's build (--expect-thru)
  /state-onset/ 1052 code/page_check_1052.py state: all 50 States render (no script error, 1979 start, 0-10 axis, episode rows)
  /shadow/      the page's text equals the page this run committed (build stamps aside)
  /data/        every row name of s2/tool_inputs_mac.json is on the page
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
    want = sys.argv[1:] or ['stress', 'state', 'shadow', 'data']; R = {}
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
        ok = all(v.get('ok') for v in R.values())
        if ok or time.time() - t0 > 900: break
        print('read-back not yet right:', {k: v.get('ok') for k, v in R.items()}, flush=True); time.sleep(60)
    R['ok'] = ok; json.dump(R, open(os.path.join(OUTD, 'readback.json'), 'w'), indent=1, default=str)
    print(json.dumps({k: (v.get('ok') if isinstance(v, dict) else v) for k, v in R.items()}))
    return 0 if ok else 1
if __name__ == '__main__': sys.exit(main())
