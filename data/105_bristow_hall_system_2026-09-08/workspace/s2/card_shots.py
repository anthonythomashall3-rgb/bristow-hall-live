#!/usr/bin/env python3
"""THE HOME CARDS SHOW EACH TOOL AS IT IS NOW (15 November 2026, collection 1052; Anthony 09:34 PT: the home page images must always show what
each live tool looks like right now). No AI.

Build mode (every site build, after the pages are written, before the deploy): serves ../site/public on a local port, opens every tool the
home page lists (its tool cards: detector, disturbance, state-onset, stress-map, damage-index, chronology) and the data page in headless Chrome,
takes a screenshot of the page as built (1200 x 760, the top of the page), writes it as <tool>/card.png, and points the home page's card at
it (img:'/<tool>/card.png?v=<sha8>'; the fixed pictures and the drawn sparkline are no longer used). Writes ../site/public/cards.json.
Exit 1 - and the workflow then publishes nothing - when a screenshot is missing or blank (fewer than 12 colours, or under 3% of the
picture differing from its most common colour).
  --readback  reads https://bristowhallsystem.pages.dev/ back: every card's picture must be the one the build behind the live site wrote (same sha256 as its /cards.json) and must match
              a fresh screenshot of the live tool page taken now (at most 3% of pixels differing). Writes out/cards_readback.json; exit 1 if not.
Usage: python3 s2/card_shots.py [--readback]

1167 (24 Nov 2026; Anthony: "under 3 minutes of data releases"): the same pictures, made side by side - one Chrome, every tool page in its
own window at once (at most four), the data page's shot beside them - and the colour count read with Pillow and numpy where they are
installed (the same pixels, the same sample, the same numbers as the pure-Python reader, which stays as the fallback). About 45 s became
about 10 s. Each page still waits for the network to go quiet, then 3 s, then the card's own preparation and 0.8 s, as before."""
import os, re, sys, json, time, zlib, struct, shutil, hashlib, threading, subprocess, http.server, socketserver, functools, urllib.request
H = os.path.dirname(os.path.abspath(__file__)); WS = os.path.dirname(H); SITE = os.path.abspath(os.path.join(WS, '..', 'site', 'public'))
LIVE = 'https://bristowhallsystem.pages.dev'; W, HH = 1200, 760; ASPECT = 2.3; TOP, CH_ = 145, round(1200 / 2.3)   # the card = rows 145..575: below the site masthead, the page's own title and chart (about the card's 2.8:1)
EXTRA = ['/data/']
# 15 Nov 2026 11:32 PT (Anthony: "show the actual graphs of the tools on the home page and the visuals of the tools"): a tool with a chart or
# map has its card made from that element alone (Playwright element screenshot, 2x); a page without one (in development) keeps the page shot.
# 11:49 PT (Anthony: every card the same size, cut if need be; no x or y axis, only the graph): a chart's card is its plot area alone (axis
# labels hidden, cut to the plot box) and every card is drawn ASPECT:1 (s2/card_prep.js); the map is centred whole in the same box.
SEL = {'/detector/': '#chart svg', '/state-onset/': '#chart svg', '/disturbance/': 'svg#chart', '/stress-map/': 'svg#map',
       '/forecaster/': '#chart svg', '/time-machine/': 'svg#tmc'}   # Tool 4 (1118, 15 Nov 2026) in place of the damage index
PREP = open(os.path.join(H, 'card_prep.js'), encoding='utf-8').read()          # shot as well (Anthony named it), though the home page has no card for it

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
            kind = pg.evaluate(PREP, [sel, ASPECT])
            if kind not in ('chart', 'map'): raise RuntimeError(f'card_prep: {kind}')
            pg.wait_for_timeout(800); e = pg.locator(sel).first
            e.screenshot(path=out, animations='disabled', timeout=120000)
        finally: b.close()
    return os.path.exists(out) and os.path.getsize(out) > 0, ''

async def _shoot_el_async(browser, url, sel, out, sem):
    """shoot_el's steps, in a window of one shared browser (1167): the same viewport, scale, waits, preparation and element screenshot"""
    async with sem:
        ctx = await browser.new_context(viewport={'width': W, 'height': 900}, device_scale_factor=2)
        try:
            pg = await ctx.new_page()
            await pg.goto(url, wait_until='networkidle', timeout=180000); await pg.wait_for_timeout(3000)
            kind = await pg.evaluate(PREP, [sel, ASPECT])
            if kind not in ('chart', 'map'): raise RuntimeError(f'card_prep: {kind}')
            await pg.wait_for_timeout(800); e = pg.locator(sel).first
            await e.screenshot(path=out, animations='disabled', timeout=120000)
        finally: await ctx.close()
    return os.path.exists(out) and os.path.getsize(out) > 0, ''


def shoot_many(jobs):
    """[(url, out, href)] -> {out: (ok, err)}: the element shots side by side in one Chrome (1167); a page without a chart selector by
    Chrome's own screenshot on a thread beside them. Any failure of the shared browser falls back to the one-by-one shots."""
    import asyncio, concurrent.futures
    res = {}
    el = [(u, o, h) for u, o, h in jobs if h in SEL]; other = [(u, o, h) for u, o, h in jobs if h not in SEL]
    for _, o, _ in jobs:
        if os.path.exists(o): os.remove(o)
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(other)))
    futs = {o: pool.submit(shoot, u, o, h) for u, o, h in other}
    async def run():
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            b = await p.chromium.launch(executable_path=chrome(), args=['--no-sandbox', '--disable-gpu', '--hide-scrollbars'])
            try:
                sem = asyncio.Semaphore(int(os.environ.get('CARD_PARALLEL') or 4))
                async def one(u, o, h):
                    try: res[o] = await _shoot_el_async(b, u, SEL[h], o, sem)
                    except Exception as e: res[o] = (False, f'{type(e).__name__} {e}'[:300])
                await asyncio.gather(*(one(u, o, h) for u, o, h in el))
            finally: await b.close()
    if el:
        try: asyncio.run(run())
        except Exception as e:
            print('home cards: the shared browser failed (%s); one by one' % str(e)[:120])
            for u, o, h in el: res[o] = shoot(u, o, h)
    for o, f in futs.items(): res[o] = f.result()
    pool.shutdown()
    return res


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

def _arr(path, step=3):
    """1167: the same sample as pix() - every third row and column, the first three channels - as a numpy array (Pillow decodes the
    PNG); None where Pillow or numpy is missing or the PNG is not 8-bit RGB/RGBA (the pure-Python reader then decides)"""
    try:
        from PIL import Image; import numpy as np
        im = Image.open(path); im.load()
        if im.mode not in ('RGB', 'RGBA'): return None
        return im.size, np.asarray(im)[::step, ::step, :3]
    except Exception: return None

def blank_stats(path):
    fa = _arr(path)
    if fa is not None:
        import numpy as np
        (w, h), a = fa; p = (a[..., 0].astype(np.uint32) << 16) | (a[..., 1].astype(np.uint32) << 8) | a[..., 2].astype(np.uint32)
        u, c = np.unique(p.ravel(), return_counts=True)
        return dict(w=w, h=h, colours=int(len(u)), share_not_main=round(1 - int(c.max()) / p.size, 4))
    w, h, px = pix(path); from collections import Counter
    cnt = Counter(px); top = cnt.most_common(1)[0][1]
    return dict(w=w, h=h, colours=len(cnt), share_not_main=round(1 - top / len(px), 4))

def diff_share(a, b):
    fa, fb = _arr(a), _arr(b)
    if fa is not None and fb is not None:
        import numpy as np
        if fa[0] != fb[0]: return 1.0
        d = np.abs(fa[1].astype(np.int16) - fb[1].astype(np.int16)).max(axis=2)
        return round(int((d > 24).sum()) / d.size, 4)
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
    jobs = []
    for href in tools + EXTRA:
        out = os.path.join(SITE, href.strip('/'), 'card.png'); os.makedirs(os.path.dirname(out), exist_ok=True)
        jobs.append((base + href, out, href))
    got = shoot_many(jobs) if os.environ.get('CARD_SERIAL') != '1' else {o: shoot(u, o, h) for u, o, h in jobs}
    for href in tools + EXTRA:
        out = os.path.join(SITE, href.strip('/'), 'card.png')
        ok, err = got.get(out, (False, 'not shot'))
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
        t = t.replace(old, 'style="object-fit:cover;object-position:center;background:#fff"')
    # 1167: written whole (a temporary name moved into place): the source gate reads the home page while the cards are made beside it
    with open(idx + '.tmp', 'w', encoding='utf-8') as fh: fh.write(t)
    os.replace(idx + '.tmp', idx)
    with open(os.path.join(SITE, 'cards.json.tmp'), 'w') as fh: json.dump(R, fh, indent=1)
    os.replace(os.path.join(SITE, 'cards.json.tmp'), os.path.join(SITE, 'cards.json'))
    print('home cards:', ', '.join(f"{h} {c['colours']} colours" for h, c in R['cards'].items())); return 0

def readback():
    get = lambda u: urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0 (bristow-hall card read-back)', 'Cache-Control': 'no-cache'}), timeout=60).read()
    mine = json.loads(get(LIVE + '/cards.json?v=%d' % time.time()))   # what the build that made the live site wrote
    home = get(LIVE + '/?v=%d' % time.time()).decode('utf-8', 'replace'); R = dict(at=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), cards={})
    imgs = dict(re.findall(r"href:'(/[^']+/)',img:'([^']+)'", home)); tmp = os.path.join(WS, 'out', 'cards_readback'); os.makedirs(tmp, exist_ok=True); ok = True
    # 1167: the live pages are shot side by side (one Chrome), as at the build; each is compared below exactly as before
    jobs = [(LIVE + h + '?v=%d' % time.time(), os.path.join(tmp, h.strip('/') + '_live_page.png'), h) for h in cards_of(home)]
    shots = shoot_many(jobs) if os.environ.get('CARD_SERIAL') != '1' else {}
    for href in cards_of(home):
        r = dict(img=imgs.get(href))
        try:
            if not r['img'] or 'card.png' not in r['img']: raise RuntimeError('the card has no generated picture')
            b = get(LIVE + r['img']); a = os.path.join(tmp, href.strip('/') + '_live_card.png'); open(a, 'wb').write(b)
            r['same_as_build'] = hashlib.sha256(b).hexdigest() == mine['cards'][href]['sha256']
            f = os.path.join(tmp, href.strip('/') + '_live_page.png')
            good, err = shots[f] if f in shots else shoot(LIVE + href + '?v=%d' % time.time(), f, href)
            r['page_vs_card_pixels_differing'] = diff_share(a, f) if good else None
            r['ok'] = bool(r['same_as_build'] and r['page_vs_card_pixels_differing'] is not None and r['page_vs_card_pixels_differing'] <= 0.03)
        except Exception as e: r.update(ok=False, err=f'{type(e).__name__} {e}'[:200])
        ok &= r['ok']; R['cards'][href] = r
    R['ok'] = ok; json.dump(R, open(os.path.join(WS, 'out', 'cards_readback.json'), 'w'), indent=1); print(json.dumps(R)[:1500]); return 0 if ok else 1

if __name__ == '__main__':
    sys.exit(readback() if '--readback' in sys.argv else build())
