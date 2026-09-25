# -*- coding: utf-8 -*-
"""THE EXACT SOURCE OF EVERY NUMBER THE SITE SHOWS, AND A GUARD ON EVERY LINK (s2/source_links.py; collection 411, 25 September 2026).

Anthony, 25 September 2026: "on the widgets on the home page, dont include anything but the name of and link to the proper source,
the exact page we get the data from"; "All data links should be to the exact source without any errors ever"; "do our links
autoupdate if/when they should? If not FIX THIS!!! Does our data autoupdaters take into account for changing links if/when they do?"

1. WHERE EACH NUMBER COMES FROM. SOURCES names, for every row of the data page (by its ids), the pages the tool actually reads
   the numbers from, in the order it reads them: a FRED series page where the tool reads FRED's current series, an ALFRED page
   where it reads the series as first published (its vintages), the Department of Labor's own claims release and ETA 539 file,
   the chart feed's page for the S&P 500 close, the Google Trends query the tool asks. TILES does the same for the front page.
   A row this list does not know (a new version's) gets the FRED page of each FRED series among its ids, so a new series is
   linked exactly the day it appears; only a row with no series id keeps the address its build gave.
2. THE GUARD. Once a day (and whenever an address is new) every address is checked: a FRED or ALFRED page, and a FRED release
   page, through FRED's own API (the series or release must exist - FRED's web pages refuse scripts, its API does not); any
   other page by fetching it as a browser would. An address that has moved for good (301/308) is replaced on the page by its
   new one; one that is gone (404/410, a host that no longer resolves, a series or release FRED no longer has) is replaced by
   its fallback (FALLBACK), or left off the page if it has none - a dead link is never shown. A host that
   refuses scripts (403/429) or does not answer says nothing about the link, which stays. Each moved or dead address is told
   to the phone (s2/alert.sh), once in three days while it lasts. The next day's check puts an address back if it has returned.
3. THE FETCHERS' OWN ADDRESSES (FETCH): the files the update downloads without FRED's API are checked the same way. The
   downloads follow a move by themselves (every curl in the chain has -L since collection 411) and each has a stand-in when
   its file is gone (FRED for the claims and the S&P 500 close, the file in hand for the rest); the phone is told either way,
   so the address in the code is updated.
Never raises into its caller: with no network, no key or any error, the addresses stand as written.

    python3 s2/source_links.py            check every address now (as the day's first run does) and print the table
    python3 s2/source_links.py --cached   print what the last check found, without checking
"""
import datetime as dt
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))           # the workspace
CHECK = os.path.join(HERE, 'cache', 'source_links_check.json')
STATUS = os.path.join(HERE, 'out', 'source_links_status.json')
FRED_PAGE = 'https://fred.stlouisfed.org/series/'
ALFRED_PAGE = 'https://alfred.stlouisfed.org/series?seid='
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36'
ALERT_EVERY_DAYS = 3


def fred(s):
    return ('FRED ' + s, FRED_PAGE + s)


def alfred(s):
    return ('ALFRED ' + s, ALFRED_PAGE + s)


def gtrends(q):
    return ('Google Trends "%s"' % q, 'https://trends.google.com/trends/explore?date=today%%203-m&geo=US&q=%s' % urllib.parse.quote(q))


DOL_PDF = ('Department of Labor, weekly claims release (data.pdf)', 'https://www.dol.gov/ui/data.pdf')
AR539 = ('Department of Labor, ETA 539 (ar539.csv)', 'https://oui.doleta.gov/unemploy/csv/ar539.csv')
FRED_REL112 = ('FRED release 112, State Employment and Unemployment', 'https://fred.stlouisfed.org/release?rid=112')
FRED_REL469 = ('FRED release 469, State Unemployment Insurance Weekly Claims Report', 'https://fred.stlouisfed.org/release?rid=469')
YAHOO = ('Yahoo Finance ^GSPC', 'https://finance.yahoo.com/quote/%5EGSPC/history/')

# the data page's rows, by their ids (lower case, as the page's data-ids): where each number in the row is read from
SOURCES = {
    '^gspc': [YAHOO, fred('SP500')],                                   # the chart feed's close at 4:20 PM; FRED's official close
    'dfedtaru': [fred('DFEDTARU')],
    'dcpf1m, dcpn30, wtb3ms': [fred('DCPF1M'), fred('DCPN30'), fred('WTB3MS')],
    'icsa, ccsa, iursa': [DOL_PDF, alfred('ICSA'), alfred('CCSA'), alfred('IURSA')],   # the release day's PDF; ALFRED's first prints
    'eta 539 state insured rates': [FRED_REL469],                     # {ST}INSUREDUR, FRED's Friday post (walk9: the breadth object)
    'eta 539 by state': [AR539],
    'eta 539': [AR539, FRED_REL112],                                  # continued weeks by state over state payrolls ({ST}NA)
    'ccnsa / covemp': [fred('CCNSA'), fred('COVEMP')],
    'wei': [fred('WEI')],
    'unrate, awhman, ndmanemp, payems': [alfred('UNRATE'), alfred('AWHMAN'), alfred('NDMANEMP'), alfred('PAYEMS')],
    'houst, permit': [alfred('HOUST'), alfred('PERMIT')],
    'indpro': [alfred('INDPRO')],
    'laus state rates (51)': [FRED_REL112],                           # each state's {ST}UR as first printed (ALFRED initial releases)
    'sahmrealtime': [fred('SAHMREALTIME')],
    'cfnaima3': [fred('CFNAIMA3')],
    'unrate, jtsjol': [alfred('UNRATE'), alfred('JTSJOL')],          # Michaillat and Saez on first prints
    'jtsjol, clf16ov': [alfred('JTSJOL'), alfred('CLF16OV')],
    'gdpnow': [alfred('GDPNOW')],                                     # every GDPNow update is a vintage
    'gdpc1': [fred('GDPC1')],
    # the front page's readings as the data page lists them (s2/home_tiles.py reads FRED's current series)
    'unrate': [fred('UNRATE')], 'payems': [fred('PAYEMS')], 'icsa': [fred('ICSA')], 'iursa': [fred('IURSA')],
    'jtsjol': [fred('JTSJOL')], 'jtsqur': [fred('JTSQUR')], 'cpiaucsl': [fred('CPIAUCSL')], 'unemploy': [fred('UNEMPLOY')],
}
# the front page's readings, by their label: the FRED series each is computed from (s2/home_tiles.py)
TILES = {'Unemployment rate': ['UNRATE'], 'Nonfarm payrolls': ['PAYEMS'], 'Payroll growth': ['PAYEMS'],
         'Initial claims (week)': ['ICSA'], 'Insured unemployment rate': ['IURSA'], 'Job openings': ['JTSJOL'],
         'Unemployed per opening': ['UNEMPLOY', 'JTSJOL'], 'Quits rate': ['JTSQUR'], 'CPI inflation': ['CPIAUCSL']}
# where to point when an address is gone and it is not a FRED or ALFRED page
FALLBACK = {DOL_PDF[1]: ('Department of Labor, weekly claims', 'https://oui.doleta.gov/unemploy/claims.asp'),
            AR539[1]: ('Department of Labor, UI data downloads', 'https://oui.doleta.gov/unemploy/DataDownloads.asp'),
            YAHOO[1]: fred('SP500'),
            FRED_REL112[1]: ('Bureau of Labor Statistics, Local Area Unemployment Statistics', 'https://www.bls.gov/lau/'),
            FRED_REL469[1]: ('Department of Labor, weekly claims', 'https://oui.doleta.gov/unemploy/claims.asp')}
# the addresses the update downloads without FRED's API (checked, told when moved or gone; the code follows a move itself)
FETCH = [('the S&P 500 chart feed (bhs_update.py)', 'https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?range=5d&interval=1d'),
         ('the weekly claims release (bhs_dol_press.py)', DOL_PDF[1]),
         ('the ETA 539 file (s2/state539_live.py, s2/activity_opener.py, s2/backstop.py)', AR539[1]),
         ('the Indeed postings index (bhs_update.py)', 'https://raw.githubusercontent.com/hiring-lab/data/master/US/aggregate_job_postings_US.csv'),
         ('the LAUS release schedule (s2/state_breadth.py)', 'https://www.bls.gov/schedule/news_release/laus.htm')]

# every address named above: never checked quietly
KNOWN = ({p[1] for ps in SOURCES.values() for p in ps} | {u for _, u in FETCH} | {fb[1] for fb in FALLBACK.values()}
         | {fred(s)[1] for ss in TILES.values() for s in ss})

TOKEN_RE = re.compile(r'^[A-Z][A-Z0-9_]{1,29}$')
NOT_SERIES = {'ETA', 'LAUS', 'GOOGLE', 'TRENDS', 'STATE', 'RATES', 'BY', 'INSURED'}


def norm(ids):
    return re.sub(r'\s+', ' ', str(ids or '').strip().lower())


def fred_tokens(ids):
    return [t for t in re.split(r'[,/;]|\s+', str(ids or '').upper()) if TOKEN_RE.match(t.strip()) and t.strip() not in NOT_SERIES]


def sources_for(ids, build_url=None):
    """the pages a row's numbers are read from, before the guard: the list above; else each FRED id's page; else the build's.
    An entry of the list may be (name, stable address, {how the release's own address is found}) - see RELEASE ADDRESSES."""
    k = norm(ids)
    if k in SOURCES:
        return list(SOURCES[k])
    m = re.match(r'^google trends "(.+)"$', k)
    if m:
        return [gtrends(m.group(1))]
    toks = fred_tokens(ids)
    if toks:
        return [fred(t) for t in toks]
    return [('source', build_url)] if build_url else []


# --------------------------------------------------------------------------------------------------- release addresses
# RELEASE ADDRESSES (collection 411, 25 September 2026; Anthony: "make sure that for the links that change upon updating/new
# data, we have a system in place for that too at the time of the new data release and at the time of the link change").
# Every exact page above is a fixed address that always shows the newest data (a FRED or ALFRED series page, a FRED release
# page, the Department's data.pdf and ar539.csv, which it overwrites at each release, the chart feed's page, the Google
# Trends query), so none of them changes at a release. A source that publishes each release at an address of its own is
# written as (name, stable address, spec), the stable address being where to point when the release's own cannot be had:
#   {'template': 'https://.../report_{through:%Y%m}.pdf'}   the address built from the row's own period (through) or today;
#   {'index': 'https://.../releases/', 'match': r'href="([^"]*report_\d{6}\.pdf)"', 'take': 'max'}
#                                                             the newest address the publisher's index page lists.
# Both are worked out again the moment the row's data changes (the run that reads the release) and at the first run of
# each day, checked like every other address, and the stable address stands in whenever the release's own does not answer.
def _ctx_date(s):
    m = re.match(r'^(\d{4})-(\d{2})(?:-(\d{2}))?', str(s or ''))
    return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3) or 1)) if m else None


def _index_links(page, match, take='max'):
    req = urllib.request.Request(page, headers={'User-Agent': UA, 'Accept': 'text/html,*/*;q=0.8'})
    with urllib.request.urlopen(req, timeout=20) as r:
        body = r.read(3_000_000).decode('utf-8', 'replace')
    found = [urllib.parse.urljoin(page, html_unescape(m.group(1) if m.groups() else m.group(0))) for m in re.finditer(match, body)]
    if not found:
        return None
    return {'first': found[0], 'last': found[-1]}.get(take) or max(found)


def html_unescape(s):
    return s.replace('&amp;', '&').replace('&#38;', '&')


def resolve_release(pair, ctx):
    """a (name, stable, spec) entry -> (name, the release's own address or None); a plain pair -> itself"""
    if len(pair) < 3 or not isinstance(pair[2], dict):
        return (pair[0], pair[1]), None
    name, stable, spec = pair[0], pair[1], pair[2]
    try:
        if spec.get('template'):
            return (name, stable), spec['template'].format(**ctx)
        if spec.get('index'):
            return (name, stable), _index_links(spec['index'], spec['match'], spec.get('take', 'max'))
    except Exception:
        pass
    return (name, stable), None


# ------------------------------------------------------------------------------------------------------------- the guard
def _jload(p, d):
    try:
        with open(p) as f:
            return json.load(f)
    except Exception:
        return d


def _jsave(p, o):
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p + '.tmp', 'w') as f:
            json.dump(o, f, indent=1, sort_keys=True)
        os.replace(p + '.tmp', p)
    except Exception:
        pass


def _key():
    root = os.path.dirname(os.path.dirname(HERE))
    for env in (os.path.join(os.path.expanduser('~'), 'mnt', 'Onset Detector Data', 'onset-detector-new-2026-08-23', 'live_data', 'config', 'local.env'),
                os.path.join(os.path.expanduser('~'), 'Projects', 'Onset Detector Data', 'onset-detector-new-2026-08-23', 'live_data', 'config', 'local.env'),
                os.path.join(root, 'onset-detector-new-2026-08-23', 'live_data', 'config', 'local.env')):
        try:
            for line in open(env):
                if line.startswith('FRED_API_KEY='):
                    return line.strip().split('=', 1)[1].strip().strip('"').strip("'")
        except Exception:
            continue
    return os.environ.get('FRED_API_KEY', '')


class _Chain(urllib.request.HTTPRedirectHandler):
    def __init__(self):
        self.hops = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.hops.append((code, newurl))
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _fred_api(kind, ident, key):
    q = {'api_key': key, 'file_type': 'json', ('series_id' if kind == 'series' else 'release_id'): ident}
    u = 'https://api.stlouisfed.org/fred/%s?%s' % (kind, urllib.parse.urlencode(q))
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'bristow-hall-source-links'}), timeout=20) as r:
            j = json.load(r)
        return 'ok' if (j.get('seriess') or j.get('releases')) else 'dead'
    except urllib.error.HTTPError as e:
        try:
            msg = e.read().decode('utf-8', 'replace').lower()
        except Exception:
            msg = ''
        if e.code in (400, 404) and ('does not exist' in msg or 'not found' in msg):
            return 'dead'
        return 'unknown'                  # a key refused, a FRED outage: says nothing about the page
    except Exception:
        return 'unknown'


def look(url, key=''):
    """one address: {'status': ok|moved|dead|blocked|unknown, 'code', 'final'}"""
    m = re.match(r'^https://(fred|alfred)\.stlouisfed\.org/series(?:/|\?seid=)([A-Za-z0-9_]+)$', url)
    if m and key:
        return {'status': _fred_api('series', m.group(2).upper(), key), 'code': None, 'final': None, 'via': 'FRED API'}
    m = re.match(r'^https://fred\.stlouisfed\.org/release\?rid=(\d+)$', url)
    if m and key:
        return {'status': _fred_api('release', m.group(1), key), 'code': None, 'final': None, 'via': 'FRED API'}
    ch = _Chain()
    op = urllib.request.build_opener(ch)
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'text/html,application/xhtml+xml,application/json,*/*;q=0.8',
                                               'Accept-Language': 'en-US,en;q=0.9', 'Range': 'bytes=0-65535'})
    try:
        with op.open(req, timeout=20) as r:
            r.read(65536)
            final, code = r.geturl(), r.status
        hops = [c for c, _ in ch.hops]
        if hops and hops[0] in (301, 308) and all(c in (301, 308) for c in hops) and final.rstrip('/') != url.rstrip('/'):
            return {'status': 'moved', 'code': code, 'final': final, 'hops': hops}
        return {'status': 'ok', 'code': code, 'final': None, 'hops': hops}
    except urllib.error.HTTPError as e:
        if e.code in (404, 410):
            return {'status': 'dead', 'code': e.code, 'final': None}
        if e.code == 416:                 # the host refuses the byte range: the page is there
            return {'status': 'ok', 'code': e.code, 'final': None}
        return {'status': 'blocked' if e.code in (401, 403, 405, 406, 429, 451, 999) else 'unknown', 'code': e.code, 'final': None}
    except urllib.error.URLError as e:
        r = str(getattr(e, 'reason', e))
        dns = 'nodename nor servname' in r or 'Name or service not known' in r or 'No address associated' in r or 'getaddrinfo failed' in r
        return {'status': 'dead' if dns else 'unknown', 'code': None, 'final': None, 'why': r[:80]}
    except Exception as e:
        return {'status': 'unknown', 'code': None, 'final': None, 'why': type(e).__name__}


def _today():
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo('America/New_York')).date().isoformat()
    except Exception:
        return dt.date.today().isoformat()


def check(urls, force=False, fetch_names=None, quiet=(), force_urls=()):
    """checks the addresses not yet checked today (all of them with force), those force_urls names (a row whose data just
    changed: the run that reads a release checks that row's addresses again), and at every run any address last found
    moved, gone or silent, so a fix or a return is seen at once. Tells the phone of a moved or dead one, once in three days
    while it lasts. Returns the check table {url: result}."""
    doc = _jload(CHECK, {})
    tab = doc.get('urls', {})
    day = _today()
    fu = set(force_urls)
    todo = sorted({u for u in urls if u and u.startswith('http') and (
        force or u in fu or (tab.get(u) or {}).get('day') != day or (tab.get(u) or {}).get('status') in ('moved', 'dead', 'unknown'))})
    if todo:
        key = _key()
        try:
            import concurrent.futures as cf
            with cf.ThreadPoolExecutor(max_workers=8) as ex:
                res = dict(zip(todo, ex.map(lambda u: look(u, key), todo)))
        except Exception:
            res = {}
        for u, r in res.items():
            prev = tab.get(u) or {}
            r['day'] = day
            if r['status'] == 'unknown' and (prev.get('status') in ('ok', 'moved', 'dead', 'blocked') or prev.get('last_known')):
                r['last_known'] = prev.get('last_known') or prev.get('status')   # no answer today: the last finding stands
                if r['last_known'] == 'moved':
                    r['final'] = prev.get('final')
            r['alerted'] = prev.get('alerted')
            if u in quiet and u not in KNOWN:
                r['quiet'] = True                  # a guess from a new row's ids: checked, never alerted
            tab[u] = r
        doc = _jload(CHECK, {}) or doc             # another caller in the same run may have written meanwhile
        doc.setdefault('urls', {}).update({u: tab[u] for u in res})
        tab = doc['urls']
        doc['checked_utc'] = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        _alert(tab, day, fetch_names or {}, set(quiet))
        _jsave(CHECK, doc)
    return tab


def _state(r):
    return (r or {}).get('last_known') if (r or {}).get('status') == 'unknown' else (r or {}).get('status')


def _alert(tab, day, fetch_names, quiet=frozenset()):
    bad = []
    for u, r in sorted(tab.items()):
        st = _state(r)
        if st not in ('moved', 'dead') or u in quiet or r.get('quiet'):
            continue
        last = r.get('alerted')
        if last and (dt.date.fromisoformat(day) - dt.date.fromisoformat(last)).days < ALERT_EVERY_DAYS:
            continue
        what = fetch_names.get(u)
        if st == 'moved':
            bad.append('%s moved for good to %s%s' % (u, r.get('final'), (' - %s follows it; update the address there' % what) if what else ' - the site links the new address'))
        else:
            bad.append('%s is gone (%s)%s' % (u, r.get('code') or r.get('why') or ('FRED has no such series or release' if r.get('via') else 'no such host'), (' - %s uses its stand-in until the address is fixed' % what) if what else ' - the site shows its fallback'))
        r['alerted'] = day
    if bad:
        try:
            sh = os.path.join(HERE, 's2', 'alert.sh')
            subprocess.run(['bash', sh, 'SOURCE LINK', 'A source address changed: ' + '; '.join(bad)[:900]], timeout=90)
        except Exception:
            pass
        print('source links: ' + '; '.join(bad))


def resolve(pairs, tab):
    """the pairs as the page shows them: a moved address by its new one, a dead one by its fallback (or left off)"""
    out = []
    for name, url in pairs:
        r = tab.get(url) or {}
        st = _state(r)
        if st == 'moved' and r.get('final'):
            out.append((name, r['final']))
        elif st == 'dead':
            fb = FALLBACK.get(url)            # a FRED or ALFRED page is dead only when FRED has no such series: none stands in
            if fb and _state(tab.get(fb[1])) != 'dead':
                out.append(fb)
        else:
            out.append((name, url))
    seen, uniq = set(), []
    for p in out:
        if p[1] not in seen:
            seen.add(p[1])
            uniq.append(p)
    return uniq


def guarded(rows_pairs, force=False, quiet=(), tokens=None, ctx=None):
    """rows_pairs: {key: [(name, url) or (name, stable, spec)]} -> {key: [(name, url)]}, checked and resolved; also checks the
    fetchers' own addresses. tokens: {key: what the row's data is now (its through-date and value)} - a row whose token moved
    since the last run has just read a release, so its addresses (and a release's own address) are worked out and checked
    again in this run. ctx: {key: {'through': date}} for release addresses. Never raises: on any error the stable pairs."""
    try:
        doc = _jload(CHECK, {})
        day = _today()
        old_tok = doc.get('row_tokens', {})
        moved_rows = {k for k in rows_pairs if tokens and k in tokens and old_tok.get(str(k)) != tokens[k]}
        rel_cache = doc.get('release', {})
        plain, release_of = {}, {}
        for k, ps in rows_pairs.items():
            plain[k] = []
            for p in ps:
                (name, stable), _ = resolve_release(p, {})
                plain[k].append((name, stable))
                if len(p) >= 3 and isinstance(p[2], dict):
                    ck = '%s|%s' % (k, name)
                    c = rel_cache.get(ck) or {}
                    if k in moved_rows or c.get('day') != day or force:
                        cx = dict({'today': dt.date.fromisoformat(day)}, **((ctx or {}).get(k) or {}))
                        _, rel = resolve_release(p, cx)
                        c = {'day': day, 'url': rel}
                        rel_cache[ck] = c
                    if c.get('url'):
                        release_of[(k, stable)] = c['url']
        urls = [u for ps in plain.values() for _, u in ps] + list(release_of.values()) + [u for _, u in FETCH]
        urls += [fb[1] for fb in FALLBACK.values()]
        fu = [u for k in moved_rows for _, u in plain[k]] + [u for (k, _s), u in release_of.items() if k in moved_rows]
        # a release's own address that is not there yet is expected (the release has not come): no alert; the stable stands in
        tab = check(urls, force=force, fetch_names={u: n for n, u in FETCH}, quiet=list(quiet) + list(release_of.values()), force_urls=fu)
        out = {}
        for k, ps in plain.items():
            cand = []
            for name, stable in ps:
                rel = release_of.get((k, stable))
                if rel and _state(tab.get(rel)) in ('ok', 'blocked', 'moved'):
                    cand.append((name, rel))        # the release's own address, when it answers
                else:
                    cand.append((name, stable))
            out[k] = resolve(cand, tab)
        d2 = _jload(CHECK, {})
        d2['release'] = rel_cache
        d2.setdefault('row_tokens', {}).update({str(k): v for k, v in (tokens or {}).items()})
        _jsave(CHECK, d2)
        _jsave(STATUS, {'day': day, 'rows': {str(k): [list(p) for p in ps] for k, ps in out.items()},
                        'rows_with_new_data_this_run': sorted(str(k) for k in moved_rows),
                        'fetch': {n: (tab.get(u) or {}).get('status') for n, u in FETCH},
                        'problems': {u: _state(r) for u, r in tab.items() if _state(r) in ('moved', 'dead')}})
        return out
    except Exception as e:
        print('source links: the guard did not run (%s); the addresses stand as written' % type(e).__name__)
        return {k: [(p[0], p[1]) for p in ps] for k, ps in rows_pairs.items()}


def tile_sources(lab):
    return [fred(s) for s in TILES.get(lab, [])]


def row_links(rows, force=False):
    """rows: {key: (ids, build_url, name_for_build_url[, data_token[, through]])} -> {key: [(name, url)]}, checked and
    resolved. The key should be the row's ids (it carries the row's data token from run to run). A row whose every address
    is gone (a word in its ids taken for a FRED id that FRED does not have, say) keeps the address its build gave."""
    pairs, tokens, ctx = {}, {}, {}
    for k, v in rows.items():
        ids, url = v[0], v[1]
        pairs[k] = sources_for(ids, url)
        if len(v) > 3 and v[3] is not None:
            tokens[k] = v[3]
        if len(v) > 4 and _ctx_date(v[4]):
            ctx[k] = {'through': _ctx_date(v[4])}
    # a row the list above does not know: its FRED pages are guesses from its ids, checked quietly (no alert for a word that is
    # not a series); the list above is what the phone is told about
    quiet = [p[1] for k, v in rows.items() if norm(v[0]) not in SOURCES for p in pairs[k]]
    out = guarded(pairs, force=force, quiet=quiet, tokens=tokens, ctx=ctx)
    for k, v in rows.items():
        if not out.get(k) and v[1]:
            out[k] = [(v[2] or 'source', v[1])]
    return out


if __name__ == '__main__':
    if '--cached' in sys.argv:
        tab = _jload(CHECK, {}).get('urls', {})
    else:
        allp = {k: v for k, v in SOURCES.items()}
        for q in ('unemployment', 'layoffs', 'laid off'):
            allp['google trends "%s"' % q] = [gtrends(q)]
        guarded(allp, force=True)
        tab = _jload(CHECK, {}).get('urls', {})
    for u, r in sorted(tab.items()):
        print('%-8s %-5s %s%s' % (r.get('status'), r.get('code') or '', u, (' -> ' + r['final']) if r.get('final') else ''))
