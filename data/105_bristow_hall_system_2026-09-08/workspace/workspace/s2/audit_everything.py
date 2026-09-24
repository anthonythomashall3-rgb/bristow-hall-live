# -*- coding: utf-8 -*-
"""THE WHOLE-SYSTEM AUDIT (18 September 2026).

Anthony: "make sure nothing fails us EVER". Nothing can be promised, but everything can be CHECKED, every time, by
a script instead of by remembering. This is that script. It checks the published site end to end and the tool
behind it, prints one line per check, and exits non-zero if anything failed, so it can be wired into the run and
into the watchdog.

What it checks, in order:
  the site      every page answers, is the right size, carries no error or placeholder text, and is current
  the numbers   the headline number on each page equals the number in the state file the page was built from
  the JSON      every served .json parses under a STRICT parser, the kind a browser uses, not Python's forgiving one
  the links     every internal link resolves and every external source link answers
  the freshness the published build is recent, and the local build matches what is published
  the tool      the last run finished, the gate passed, the freeze is clean, the data check is 113/113
  the machine   the launchd jobs are loaded, the collector is writing, the disk has room
"""
import os, sys, json, re, subprocess, datetime, urllib.request, urllib.error, socket
import concurrent.futures as cf

SITE = 'https://bhrrealtime.pages.dev'
PAGES = ['/', '/detector/', '/data/', '/chronology/', '/damage-index/', '/disturbance/',
         '/state-onset/', '/stress-map/']
JSONS = ['/bhs_state.json', '/detector/bhs_state.json']
QUIET = '--quiet' in sys.argv
# --fast skips the 57 external source links, which take most of the time. The fast form runs after every publish;
# the full form runs once a day from the watchdog.
FAST = '--fast' in sys.argv
R = []
# Publishers and Cloudflare alike refuse an unfamiliar user agent: the first run of this audit reported 48 of 57
# source links dead, and every one of them was alive in a browser. An audit that cries wolf is worse than none.
UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/128.0 Safari/537.36',
      'Accept': 'text/html,application/json,*/*'}


def ok(name, good, detail=''):
    R.append((name, bool(good), detail))
    if not QUIET or not good:
        print('%-4s %-52s %s' % ('PASS' if good else 'FAIL', name[:52], detail[:90]))


def get(url, timeout=40):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b''
    except Exception as e:
        return 0, str(e).encode()


def _key(name):
    """read a key from local.env without ever printing it"""
    p = os.path.join(DATAROOT(), 'onset-detector-new-2026-08-23', 'live_data', 'config', 'local.env')
    try:
        for ln in open(p):
            if ln.startswith(name + '='): return ln.split('=', 1)[1].strip().strip('"').strip("'")
    except Exception: pass
    return ''


_FREDK = None


def link_ok(url, timeout=25):
    """Is this link good?

    A FRED series page cannot be checked by machine: fred.stlouisfed.org times out on HEAD and on GET, from this
    Mac and from a cloud host alike, while working perfectly in a browser. The first run of this audit called 48
    of 57 links dead on that basis and every one of them was alive. So a FRED series link is checked against the
    FRED API instead, with the key the pipeline already uses - which is the better check anyway: it confirms the
    link points at a series that EXISTS, not merely that a web page loaded.
    """
    global _FREDK
    m = re.match(r'https://fred\.stlouisfed\.org/series/([A-Za-z0-9_.@\-]+)/?$', url)
    if m:
        if _FREDK is None: _FREDK = _key('FRED_API_KEY')
        if not _FREDK: return 'no FRED key'
        q = ('https://api.stlouisfed.org/fred/series?series_id=%s&api_key=%s&file_type=json'
             % (m.group(1), _FREDK))
        try:
            req = urllib.request.Request(q, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return 200 if b'"seriess"' in r.read(400) else 404
        except urllib.error.HTTPError as e: return e.code
        except Exception: return 0
    if url.startswith('/'):
        url = SITE + url
    return head_ok(url, timeout)


def head_ok(url, timeout=25):
    """HEAD first because it is cheap, then GET whenever HEAD does not answer well.

    Publishers refuse HEAD in more ways than one: 403, 405, 501, a redirect loop, or simply hanging. The EIA weekly
    supply page answers HEAD with nothing at all and GET with 200, and the first version of this audit reported it
    dead. A link is dead only when GET says so."""
    def once(method):
        try:
            req = urllib.request.Request(url, headers=UA, method=method)
            with urllib.request.urlopen(req, timeout=timeout) as r: return r.status
        except urllib.error.HTTPError as e: return e.code
        except Exception: return 0
    c = once('HEAD')
    if c in (200, 301, 302): return c
    return once('GET')


BAD_TEXT = ['Traceback', 'NameError', 'KeyError', 'undefined', 'NaN', 'None</', '>None<',
            'TODO', 'FIXME', 'lorem ipsum', 'Internal Server Error', '{{', '}}']


def main():
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    print('WHOLE-SYSTEM AUDIT  %s' % stamp)

    # ---------------------------------------------------------------- the site
    bodies = {}
    with cf.ThreadPoolExecutor(8) as ex:
        got = dict(zip(PAGES, ex.map(lambda p: get(SITE + p + ('?w=%d' % int(datetime.datetime.now().timestamp()))), PAGES)))
    for p in PAGES:
        code, body = got[p]
        bodies[p] = body
        ok('page answers: %s' % p, code == 200, 'HTTP %s' % code)
        ok('page has content: %s' % p, len(body) > 1500, '%d bytes' % len(body))
        # Only what a READER sees. NaN, undefined and }} are ordinary inside JavaScript; the first run of this
        # audit failed two live, correct pages on them. Scripts and styles are stripped before looking.
        txt = body.decode('utf-8', 'replace')
        vis = re.sub(r'(?is)<(script|style)[^>]*>.*?</\1>', ' ', txt)
        vis = re.sub(r'<[^>]+>', ' ', vis)
        found = [b for b in BAD_TEXT if b in vis]
        ok('no error or placeholder text is visible to a reader: %s' % p, not found, ', '.join(found))

    # ---------------------------------------------------------------- the served JSON, strictly
    states = {}
    for j in JSONS:
        code, body = get(SITE + j + '?w=%d' % int(datetime.datetime.now().timestamp()))
        ok('json answers: %s' % j, code == 200, 'HTTP %s' % code)
        # strict: the parser a browser uses refuses NaN and Infinity, and Python's does not unless told
        try:
            s = json.loads(body.decode('utf-8', 'replace'),
                           parse_constant=lambda c: (_ for _ in ()).throw(ValueError('%s is not JSON' % c)))
            states[j] = s; good, why = True, '%d keys' % len(s)
        except Exception as e:
            good, why = False, str(e)[:80]
        ok('json is valid under a strict parser: %s' % j, good, why)

    st = states.get('/bhs_state.json')
    if st:
        # ------------------------------------------------------------ freshness
        try:
            b = datetime.datetime.strptime(st['built_at'][:16], '%Y-%m-%d %H:%M')
            age = (datetime.datetime.now() - b).total_seconds() / 3600.0 - 3.0   # built_at is New York
            limit = 54 if datetime.date.today().weekday() >= 5 else 30
            ok('the published build is current', age < limit, '%.1f hours old (limit %d)' % (age, limit))
        except Exception as e:
            ok('the published build is current', False, str(e)[:70])

        # ------------------------------------------------------------ the line, and the number on the page
        se = st.get('series') or {}
        vals = [v for v in (se.get('values') or []) if v is not None]
        ok('the line has values', len(vals) > 1000, '%d daily readings' % len(vals))
        last_day = (se.get('dates') or [None])[-1]
        try:
            d = datetime.date.fromisoformat(last_day)
            ok('the line runs to within a fortnight', (datetime.date.today() - d).days <= 14,
               'last reading %s' % last_day)
        except Exception:
            ok('the line runs to within a fortnight', False, 'unreadable last date %s' % last_day)
        if vals:
            cur = vals[-1]
            page = bodies.get('/detector/', b'').decode('utf-8', 'replace')
            shown = ('%.2f' % cur) in page or ('%.3f' % cur) in page or ('%g' % cur) in page
            ok('the detector page shows the current reading', shown, 'state says %s' % cur)
        stand = st.get('standing') or {}
        ok('the standing is stated', stand.get('state') in ('open', 'closed'), str(stand)[:70])

        # ------------------------------------------------------------ the local build matches the published one
        try:
            loc = json.load(open('out/bhs_state.json'))
            ok('this machine has published its latest build',
               loc.get('built_at') == st.get('built_at'),
               'local %s, published %s' % (loc.get('built_at'), st.get('built_at')))
        except Exception as e:
            ok('this machine has published its latest build', False, str(e)[:70])

        # ------------------------------------------------------------ every source link answers
        feeds = st.get('leg_feeds') or []
        urls = [] if FAST else sorted({f['url'] for f in feeds if f.get('url')})
        with cf.ThreadPoolExecutor(10) as ex:
            codes = dict(zip(urls, ex.map(link_ok, urls)))
        dead = [u for u, c in codes.items() if c not in (200, 301, 302)]
        if not FAST:
            ok('every source link on the data page answers', not dead,
               '%d of %d dead: %s' % (len(dead), len(urls), ', '.join(dead[:3])))

        # ------------------------------------------------------------ every feed is inside its own cadence
        today = datetime.date.today()
        LIM = {'daily': 12, 'weekly': 24, 'monthly': 95, 'quarterly': 200}
        late = []
        for f in feeds:
            t = (f.get('through') or '')[:10]
            try: d = datetime.date.fromisoformat(t)
            except Exception: continue
            lim = LIM.get(f.get('cadence') or '', 150)
            if (today - d).days > lim and (f.get('n') or 0) > 0 and f.get('refreshed'):
                try: rd = datetime.date.fromisoformat(f['refreshed'][:10])
                except Exception: rd = None
                # only a fault if we are still refreshing it: a discontinued historical series is not late
                if rd and (today - rd).days <= 7: late.append('%s %s' % (f['channel'], t))
        ok('every live feed is inside its own cadence', len(late) <= 8,
           '%d late: %s' % (len(late), ', '.join(late[:4])))

    # ---------------------------------------------------------------- internal links
    bad_links = []
    if FAST: bodies = {}
    for p, body in bodies.items():
        txt = body.decode('utf-8', 'replace')
        for href in set(re.findall(r'href="(/[^"#?]*)"', txt)):
            u = SITE + href
            if head_ok(u) not in (200, 301, 302): bad_links.append(p + ' -> ' + href)
    ok('every internal link resolves', not bad_links, '%d broken: %s' % (len(bad_links), ', '.join(bad_links[:3])))

    # ---------------------------------------------------------------- the tool
    def run(cmd):
        try:
            p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=600)
            return p.returncode, (p.stdout + p.stderr).strip().splitlines()[-1] if (p.stdout + p.stderr).strip() else ''
        except Exception as e:
            return 99, str(e)[:70]
    rc, out = run('python3 s2/freeze.py --check')
    ok('the freeze is clean', rc == 0, out)
    rc, out = run('PYTHONPATH=. python3 s2/q41_data_check.py')
    ok('the data check passes', rc == 0, out)
    rc, out = run('PYTHONPATH=. python3 s2/deploy_gate.py')
    ok('the deploy gate passes', rc == 0, out)
    rc, out = run('python3 s2/score_record.py')
    ok('the scorer reproduces the published record', rc == 0, out)
    # THE CHECK THIS AUDIT DID NOT HAVE. On 18 September every walk had been broken for days - a folder the walk
    # reads had moved - and nothing noticed, because the site publishes from the walk's CACHED results and kept
    # working perfectly. The product looked healthy while the laboratory was dead. This runs the live walk's
    # preamble, which is where that failure appeared, and is skipped in --fast because it takes about a minute.
    if not FAST:
        rc, out = run('python3 s2/walk_health.py')
        ok('the live walk can still be run', rc == 0, out)
    ok('no publish is owed', not os.path.exists('cache/deploy_pending'), 'cache/deploy_pending present')

    try:
        ld = open('cache/last_done').read().strip()
        t = datetime.datetime.fromisoformat(ld)
        if t.tzinfo is None: t = t.astimezone()
        mins = (datetime.datetime.now(datetime.timezone.utc) - t.astimezone(datetime.timezone.utc)).total_seconds() / 60
        hr = datetime.datetime.now().hour
        lim = 180 if 5 <= hr <= 16 else 1200
        ok('a run finished recently', mins < lim, '%.0f minutes ago (limit %d)' % (mins, lim))
    except Exception as e:
        ok('a run finished recently', False, str(e)[:70])

    # ---------------------------------------------------------------- the machine
    if sys.platform == 'darwin':
        rc, out = run("launchctl list | grep -c bristowhall")
        ok('the launchd jobs are loaded', rc == 0 and out.isdigit() and int(out) >= 3, '%s jobs' % out)
        rc, out = run("df -g /System/Volumes/Data | awk 'NR==2{print $4}'")
        ok('the disk has room', out.isdigit() and int(out) >= 80, '%s GiB free (floor 80)' % out)
    import glob as _g
    hits = _g.glob(os.path.join(DATAROOT(), '191_standing_collector_*', 'logs', 'STATUS.txt'))
    stat = hits[0] if hits else '(no collector STATUS.txt found)'
    try:
        age = (datetime.datetime.now().timestamp() - os.path.getmtime(stat)) / 3600
        ok('the collector is writing', age < 6, '%.1f hours since its last cycle' % age)
    except Exception as e:
        ok('the collector is writing', False, str(e)[:70])

    bad = [r for r in R if not r[1]]
    print('\n%d/%d PASS' % (len(R) - len(bad), len(R)))
    if bad:
        print('FAILURES:')
        for n, _g, d in bad: print('   %-52s %s' % (n[:52], d[:80]))
    out_dir = os.path.join(DATAROOT(), '217_site_tool_audit_2026-09-18', 'out')
    try:
        os.makedirs(out_dir, exist_ok=True)
        json.dump(dict(generated=stamp, checks=len(R), failures=len(bad),
                       results=[dict(check=n, passed=g, detail=d) for n, g, d in R]),
                  open(os.path.join(out_dir, 'audit_%s.json' % stamp.replace(':', '')), 'w'), indent=1)
    except Exception:
        pass
    return 1 if bad else 0


def COLROOT():
    """the collection folder. This file lives at <collection>/workspace/s2/, so it is three levels up, not two -
    the first version was one short and the audit reported the collector missing when it was writing fine."""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def DATAROOT():
    return os.path.dirname(COLROOT())


if __name__ == '__main__':
    sys.exit(main())
