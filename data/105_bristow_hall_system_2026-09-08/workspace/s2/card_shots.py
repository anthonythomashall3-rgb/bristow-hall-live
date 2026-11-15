#!/usr/bin/env python3
"""THE HOME CARDS SHOW EACH TOOL AS IT IS NOW (15 November 2026, collection 1052; Anthony 09:34 PT: the home page images must always show what
each live tool looks like right now). No AI.

Build mode (every site build, after the pages are written, before the deploy): serves ../site/public on a local port, opens every tool the
home page lists (its tool cards: detector, disturbance, state-onset, stress-map, damage-index, chronology) and the data page in headless Chrome,
takes a screenshot of the page as built (1200 x 760, the top of the page), writes it as <tool>/card.png, and points the home page's card at
it (img:'/<tool>/card.png?v=<sha8>'; the fixed pictures and the drawn sparkline are no longer used). Writes ../site/public/cards.json.
Exit 1 - and the workflow then publishes nothing - when a screenshot is missing or blank (fewer than 12 colours, or under 3% of the
picture differing from its most common colour).
  --readback  reads https://bhrrealtime.pages.dev/ back: every card's picture must be the one the build behind the live site wrote (same sha256 as its /cards.json) and must match
              a fresh screenshot of the live tool page taken now (at most 3% of pixels differing). Writes out/cards_readback.json; exit 1 if not.
Usage: python3 s2/card_shots.py [--readback]"""
import os, re, sys, json, time, zlib, struct, shutil, hashlib, threading, subprocess, http.server, socketserver, functools, urllib.request
H = os.path.dirname(os.path.abspath(__file__)); WS = os.path.dirname(H); SITE = os.path.abspath(os.path.join(WS, '..', 'site', 'public'))
LIVE = 'https://bhrrealtime.pages.dev'; W, HH = 1200, 760; TOP, CH_ = 145, 430   # the card = rows 145..575: below the site masthead, the page's own title and chart (about the card's 2.8:1)
EXTRA = ['/data/']
# 15 Nov 2026 11:32 PT (Anthony: "show the actual graphs of the tools on the home page and the visuals of the tools"): a tool with a chart or
# map has its card made from that element alone (Playwright element screenshot, 2x); a page without one (in development) keeps the page shot.
SEL = {'/detector/': '#chart', '/state-onset/': '#chart', '/disturbance/': 'svg#chart', '/stress-map/': 'svg#map'}          # shot as well (Anthony named it), though the home page has no card for it

def chrome():
    for c in (os.environ.get('CHROME'), shutil.which('google-chrome'), shutil.which('google-chrome-stable'), shutil.which('chromium'),
              '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'):
        if c and os.path.exists(c): return c
    raise SystemExit('no Chrome found')

def shoot_el(url, sel, out):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=chrome(), args=['--no-sandbox', '--disable-gpu', '--hide-scrollbars'])
        try:
            pg = b.new_page(viewport={'width': W, 'height': 900}, device_scale_factor=2)
            pg.goto(url, wait_until='networkidle', timeout=180000); pg.wait_for_timeout(3000)
            e = pg.locator(sel).first; e.scroll_into_view_if_needed(); pg.wait_for_timeout(800)
            e.screenshot(path=out, animations='disabled', timeout=120000)
        finally: b.close()
    return os.path.exists(out) and os.path.getsize(out) > 0, ''

def shoot(url, out, href=None):
    if os.path.exists(out): os.remove(out)
    if href in SEL:
        try: return shoot_el(url, SEL[href], out)
        except Exception as e: return False, f'{type(e).__name__} {e}'[:300]
    import tempfile
    prof = tempfile.mkdtemp(prefix='cardshot')
    cmd = [chrome(), '--headless=new', '--disable-gpu', '--no-sandbox', '--hide-scrollbars', '--no-first-run', '--user-data-dir=' + prof,
           f'--window-size={W},{HH}', '--virtual-time-budget=20000', '--run-all-compositor-stages-before-draw', '--screenshot=' + out, url]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180); shutil.rmtree(prof, ignore_errors=True)
    ok = os.path.exists(out) and os.path.getsize(out) > 0
    if ok: crop(out)
    return ok, (r.stderr or '')[-300:]

def png_pixels(path):
    """8-bit RGB or RGBA PNG (what Chrome writes) -> (width, height, channels, rows as bytes)"""
    b = open(path, 'rb').read(); assert b[:8] == b'\x89PNG\r\n\x1a\n'; i = 8; idat = b''; w = h = ct = 0
    while i < len(b):
        n = struct.unpack('>I', b[i:i + 4])[0]; t = b[i + 4:i + 8]; d = b[i + 8:i + 8 + n]; i += 12 + n
        if t == b'IHDR': w, h, bd, ct = struct.unpack('>IIBB', d[:10]); assert bd == 8 and ct in (2, 6), (bd, ct)
        elif t == b'IDAT': idat += d
    ch = 3 if ct == 2 else 4; raw = zlib.decompress(idat); stride = w * ch; rows = []; prev = bytearray(stride); p = 0
    for _ in range(h):
        f = raw[p]; line = bytearray(raw[p + 1:p + 1 + stride]); p += 1 + stride
        for x in range(stride):
            a = line[x - ch] if x >= ch else 0; up = prev[x]; c = prev[x - ch] if x >= ch else 0
            if f == 1: line[x] = (line[x] + a) & 255
            elif f == 2: line[x] = (line[x] + up) & 255
            elif f == 3: line[x] = (line[x] + ((a + up) >> 1)) & 255
            elif f == 4:
                pa, pb, pc = abs(up - c), abs(a - c), abs(a + up - 2 * c); pr = a if (pa <= pb and pa <= pc) else (up if pb <= pc else c); line[x] = (line[x] + pr) & 255
        rows.append(bytes(line)); prev = line
    return w, h, ch, rows

def crop(path, top=TOP, height=CH_):
    """keep rows top..top+height of the screenshot (the shared masthead above is the same on every page), written back as PNG"""
    w, h, ch, rows = png_pixels(path); rows = rows[top:top + height]
    ihdr = struct.pack('>IIBBBBB', w, len(rows), 8, 2 if ch == 3 else 6, 0, 0, 0)
    chunk = lambda t_, d: struct.pack('>I', len(d)) + t_ + d + struct.pack('>I', zlib.crc32(t_ + d) & 0xffffffff)
    open(path, 'wb').write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + chunk(b'IDAT', zlib.compress(b''.join(b'\x00' + r for r in rows), 9)) + chunk(b'IEND', b''))

def pix(path, step=3):
    w, h, ch, rows = png_pixels(path)
    return w, h, [r[x:x + 3] for r in rows[::step] for x in range(0, w * ch, ch * step)]

def blank_stats(path):
    w, h, px = pix(path); from collections import Counter
    cnt = Counter(px); top = cnt.most_common(1)[0][1]
    return dict(w=w, h=h, colours=len(cnt), share_not_main=round(1 - top / len(px), 4))

def diff_share(a, b):
    wa, ha, pa = pix(a); wb, hb, pb = pix(b)
    if (wa, ha) != (wb, hb): return 1.0
    return round(sum(1 for x, y in zip(pa, pb) if max(abs(x[i] - y[i]) for i in range(3)) > 24) / len(pa), 4)

def cards_of(index_html):
    m = re.search(r'const T=\[(.*?)\n  \];', index_html, re.S); assert m, 'home page: the tool card list (const T=[...]) not found'
    return [h for h in re.findall(r"href:'(/[^']+/)'", m.group(1))]

def serve(root):
    class Q(socketserver.ThreadingMixIn, http.server.HTTPServer): daemon_threads = True
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
    h = functools.partial(Quiet, directory=root)
    s = Q(('127.0.0.1', 0), h); threading.Thread(target=s.serve_forever, daemon=True).start(); return s

def build():
    idx = os.path.join(SITE, 'index.html'); t = open(idx, encoding='utf-8').read(); tools = cards_of(t); s = serve(SITE); base = 'http://127.0.0.1:%d' % s.server_address[1]
    R = dict(built=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), size=[W, HH], cards={}); bad = []
    for href in tools + EXTRA:
        out = os.path.join(SITE, href.strip('/'), 'card.png'); os.makedirs(os.path.dirname(out), exist_ok=True)
        ok, err = shoot(base + href, out, href)
        if not ok: bad.append(f'{href}: no screenshot ({err})'); continue
        st = blank_stats(out); sha = hashlib.sha256(open(out, 'rb').read()).hexdigest()
        if st['colours'] < 12 or st['share_not_main'] < 0.03: bad.append(f'{href}: blank picture {st}')
        R['cards'][href] = dict(png=href + 'card.png', sha256=sha, on_home=href in tools, **st)
    s.shutdown()
    if bad:
        print('HOME CARDS NOT MADE:', bad); json.dump(dict(R, failed=bad), open(os.path.join(SITE, 'cards.json'), 'w'), indent=1); return 1
    def img_for(m):
        body = m.group(0); href = re.search(r"href:'(/[^']+/)'", body).group(1); v = R['cards'][href]['sha256'][:8]
        body = re.sub(r",img:'[^']*'", '', body).replace(',spark:true', '')
        return body.replace("href:'%s'" % href, "href:'%s',img:'%scard.png?v=%s'" % (href, href, v), 1)
    m = re.search(r'const T=\[(.*?)\n  \];', t, re.S); block = re.sub(r"\{n:'[^}]*\}", img_for, m.group(1))
    t = t[:m.start(1)] + block + t[m.end(1):]
    for old in ('style="object-fit:fill"', 'style="object-fit:cover;object-position:top"'):
        t = t.replace(old, 'style="object-fit:contain;object-position:center;background:#fff"')
    open(idx, 'w', encoding='utf-8').write(t); json.dump(R, open(os.path.join(SITE, 'cards.json'), 'w'), indent=1)
    print('home cards:', ', '.join(f"{h} {c['colours']} colours" for h, c in R['cards'].items())); return 0

def readback():
    get = lambda u: urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0 (bristow-hall card read-back)', 'Cache-Control': 'no-cache'}), timeout=60).read()
    mine = json.loads(get(LIVE + '/cards.json?v=%d' % time.time()))   # what the build that made the live site wrote
    home = get(LIVE + '/?v=%d' % time.time()).decode('utf-8', 'replace'); R = dict(at=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), cards={})
    imgs = dict(re.findall(r"href:'(/[^']+/)',img:'([^']+)'", home)); tmp = os.path.join(WS, 'out', 'cards_readback'); os.makedirs(tmp, exist_ok=True); ok = True
    for href in cards_of(home):
        r = dict(img=imgs.get(href))
        try:
            if not r['img'] or 'card.png' not in r['img']: raise RuntimeError('the card has no generated picture')
            b = get(LIVE + r['img']); a = os.path.join(tmp, href.strip('/') + '_live_card.png'); open(a, 'wb').write(b)
            r['same_as_build'] = hashlib.sha256(b).hexdigest() == mine['cards'][href]['sha256']
            f = os.path.join(tmp, href.strip('/') + '_live_page.png'); good, err = shoot(LIVE + href + '?v=%d' % time.time(), f, href)
            r['page_vs_card_pixels_differing'] = diff_share(a, f) if good else None
            r['ok'] = bool(r['same_as_build'] and r['page_vs_card_pixels_differing'] is not None and r['page_vs_card_pixels_differing'] <= 0.03)
        except Exception as e: r.update(ok=False, err=f'{type(e).__name__} {e}'[:200])
        ok &= r['ok']; R['cards'][href] = r
    R['ok'] = ok; json.dump(R, open(os.path.join(WS, 'out', 'cards_readback.json'), 'w'), indent=1); print(json.dumps(R)[:1500]); return 0 if ok else 1

if __name__ == '__main__':
    sys.exit(readback() if '--readback' in sys.argv else build())
