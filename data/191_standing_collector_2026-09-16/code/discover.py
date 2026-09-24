#!/usr/bin/env python3
"""The collector's own search for data nobody told it about.

18 September 2026. Written after Anthony's judgement that neither Claude nor the machine was searching hard enough.
The earlier discovery job asked one portal at a time. This asks every open-data portal in the United States at once:
api.us.socrata.com indexes all of them, and a single query returns matches across data.ny.gov, data.texas.gov,
data.pa.gov, city and county portals and the federal ones together. Two national CKAN catalogues are asked the same
questions afterwards.

What it does with a match, in order, and it stops at the first gate that fails:
  1. the name or description must match a relevance pattern, so that a parking dataset is not fetched;
  2. it must not already be held, by identifier, anywhere in the registry or in an earlier discovery;
  3. its own newest observation must be recent. This is the gate the third sweep taught: a portal's updatedAt is
     metadata churn, not data. Colorado's foreclosure files carry today's updatedAt and end in 2016. So the dataset's
     column metadata is read, its first date column found, and the maximum of that column asked for. A dataset whose
     own data stopped more than `stale_years` ago is recorded and never fetched;
  4. it must fit the budget: a number of datasets and a number of megabytes per pass, and a ceiling on the folder.

Everything kept is written to warehouse/discovered/<domain>/<id>__<name>.csv with a row in discovered_registry.csv
giving the portal, the identifier, the name, the date column, the newest observation, the rows and the bytes. A dataset
already held is fetched again only when its newest observation has moved, so a weekly file costs one small question a
cycle and nothing else.

Reads only public catalogues. Uses the fetch engine when it is importable, so a portal that refuses a plain request
still answers.
"""
import os, re, csv, sys, json, time, urllib.parse

CAT = 'https://api.us.socrata.com/api/catalog/v1'
CKAN = ['https://data.ca.gov/api/3/action/package_search',
        'https://data.virginia.gov/api/3/action/package_search']

# what the rule could read. Order matters only in that the pass walks them in rotation.
TERMS = [
 'unemployment insurance claims', 'initial claims', 'continued claims', 'unemployment rate',
 'WARN notice', 'layoff', 'mass layoff', 'dislocated worker', 'rapid response',
 'job openings', 'job vacancies', 'job postings', 'hiring', 'labor force', 'nonfarm employment',
 'employment and wages', 'covered employment', 'quarterly census of employment',
 'business entity', 'new business registration', 'business filings', 'business licenses',
 'sales tax collections', 'sales tax allocation', 'revenue collections', 'tax receipts',
 'withholding tax', 'mixed beverage receipts', 'lottery sales', 'liquor sales',
 'eviction filings', 'foreclosure', 'mortgage delinquency', 'tax lien', 'utility shutoff',
 'SNAP participation', 'food assistance', 'medicaid enrollment', 'public assistance',
 'bankruptcy filings', 'building permits', 'housing starts', 'home sales',
 'transit ridership', 'traffic volume', 'airport enplanements', 'port tonnage', 'freight',
 'electricity consumption', 'natural gas consumption', 'gasoline prices',
 'consumer spending', 'retail sales', 'restaurant', 'hotel occupancy', 'tourism',
 'wages', 'earnings', 'income', 'poverty', 'household', 'establishment',
 'economic indicators', 'leading index', 'coincident index', 'gross domestic product',
 'manufacturing', 'construction employment', 'trucking', 'warehouse employment',
 'child care', 'school enrollment', 'crime', 'population estimates',
]

GOOD = re.compile(r'(?i)(unemploy|claim|layoff|warn|job|employ|payroll|wage|labor|labour|workforce|'
                  r'business (entity|registration|filing|licen)|sales tax|revenue|receipt|withhold|'
                  r'evict|foreclos|delinquen|snap|food assistance|medicaid|assistance|bankrupt|'
                  r'permit|housing|transit|riders|traffic|freight|port|electric|gas price|'
                  r'retail|spending|restaurant|hotel|occupancy|tourism|income|poverty|establishment|'
                  r'econom|leading index|coincident|gross domestic|manufactur|construction|lottery)')
BAD = re.compile(r'(?i)(parking|park |trail|tree|art |mural|library book|animal|pet |bicycle rack|'
                 r'restroom|playground|cemeter|golf|fishing|hunting licen|marriage licen|'
                 r'covid vaccin|immuniz|salaries of|employee directory|employee salar|campaign finance|'
                 r'enviro|air quality|water quality|emission|pollut|inpatient|outpatient|hospital|clinic|'
                 r'disease|cancer|birth|death certificate|restaurant inspect|food safety|school test|'
                 r'voter|election result|procurement|contract award|grant award|lobby|'
                 r'employee pay|state employee|salar|diversity|inspector general|vehicle for hire|'
                 r'marijuana|cannabis|thc |compliance check|crime|police|fire department|'
                 r'brands|directory of|self-identified|budget program measures|annual data)')

DATEY = re.compile(r'(?i)(date|week|month|period|year|time|quarter|as_of|filed|reported)')


def _log(*a):
    print(time.strftime('%H:%M:%S'), ' '.join(str(x) for x in a), flush=True)


LOG = [_log]


def log(*a):
    try: LOG[0](*a)
    except Exception: _log(*a)


def _get(url, timeout=90, engine=None):
    if engine is not None:
        b = engine.smart_get(url, timeout=timeout, quiet=True, respect_quarantine=False)
        return None if (b is None or b is engine.NOT_MODIFIED) else b
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/140.0.0.0 Safari/537.36', 'Accept': '*/*'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception:
        return None


def catalog(term, limit=100, offset=0, engine=None):
    q = urllib.parse.urlencode({'q': term, 'only': 'dataset', 'limit': limit, 'offset': offset})
    b = _get(CAT + '?' + q, engine=engine)
    if not b: return []
    try: j = json.loads(b)
    except Exception: return []
    out = []
    for r in j.get('results', []):
        res = r.get('resource', {}) or {}
        meta = r.get('metadata', {}) or {}
        out.append({'id': res.get('id', ''), 'name': res.get('name', ''),
                    'desc': (res.get('description') or '')[:300],
                    'domain': meta.get('domain', ''), 'updated': res.get('updatedAt', '')})
    return out


def date_column(domain, rid, engine=None):
    """The dataset's own first date column, from its column metadata. None when it has none."""
    b = _get('https://%s/api/views/%s.json' % (domain, rid), timeout=60, engine=engine)
    if not b: return None
    try: j = json.loads(b)
    except Exception: return None
    cols = j.get('columns') or []
    for c in cols:
        if (c.get('dataTypeName') or '') in ('calendar_date', 'date', 'floating_timestamp'):
            return c.get('fieldName')
    for c in cols:                                   # a date written as text still sorts, if it is ISO
        if DATEY.search(c.get('fieldName') or ''):
            return c.get('fieldName')
    return None


def newest(domain, rid, col, engine=None):
    b = _get('https://%s/resource/%s.json?$select=max(%s)' % (domain, rid, col), timeout=60, engine=engine)
    if not b: return ''
    try:
        j = json.loads(b)
        if isinstance(j, list) and j:
            return str(list(j[0].values())[0])[:10]
    except Exception:
        pass
    return ''


def ckan(term, engine=None):
    out = []
    for base in CKAN:
        b = _get(base + '?' + urllib.parse.urlencode({'q': term, 'rows': 25}), engine=engine)
        if not b: continue
        try: j = json.loads(b)
        except Exception: continue
        for p in (j.get('result', {}) or {}).get('results', []) or []:
            for r in p.get('resources', []) or []:
                if (r.get('format') or '').upper() in ('CSV', 'XLSX', 'XLS', 'JSON'):
                    out.append({'id': r.get('id', ''), 'name': (p.get('title') or '')[:150],
                                'desc': (p.get('notes') or '')[:300], 'domain': urllib.parse.urlparse(base).netloc,
                                'url': r.get('url', ''), 'updated': p.get('metadata_modified', '')})
                    break
    return out


def run(root, held_ids=None, datasets_per_pass=40, mb_per_pass=400, folder_cap_gib=30,
        stale_years=3, terms_per_pass=12, state=None, engine=None):
    """One discovery pass. `root` is the warehouse folder; `held_ids` identifiers already registered elsewhere."""
    out = os.path.join(root, 'discovered')
    os.makedirs(out, exist_ok=True)
    reg = os.path.join(out, 'discovered_registry.csv')
    seen, stale = {}, set()
    if os.path.exists(reg):
        try:
            for row in csv.DictReader(open(reg, newline='')):
                seen[row['id']] = row
                if row.get('verdict') == 'stale': stale.add(row['id'])
        except Exception:
            pass
    held = set(held_ids or []) | set(seen)

    # how far through the term list the last pass got, so the rotation continues rather than restarting
    spath = os.path.join(out, '_discover_state.json')
    start = 0
    try: start = int(json.load(open(spath)).get('term_index', 0))
    except Exception: pass

    total = 0
    for dp, dn, fn in os.walk(out):
        for f in fn:
            try: total += os.path.getsize(os.path.join(dp, f))
            except OSError: pass
    if total > folder_cap_gib * 2 ** 30:
        log('  discovery: folder at %.1f GiB, at its ceiling; nothing fetched' % (total / 2 ** 30)); return 0

    new = 0
    bytes_this_pass = 0
    rows_out = []
    terms = [TERMS[(start + i) % len(TERMS)] for i in range(terms_per_pass)]
    log('  discovery: asking every portal about', ', '.join(t for t in terms[:4]) + ' and %d more' % (len(terms) - 4))

    for term in terms:
        if new >= datasets_per_pass or bytes_this_pass > mb_per_pass * 2 ** 20: break
        hits = catalog(term, engine=engine) + ckan(term, engine=engine)
        for h in hits:
            if new >= datasets_per_pass or bytes_this_pass > mb_per_pass * 2 ** 20: break
            rid, dom, name = h.get('id', ''), h.get('domain', ''), h.get('name', '')
            if not rid or not dom or rid in held or rid in stale: continue
            if not (dom.endswith('.gov') or dom.endswith('.us') or 'socrata.com' in dom): continue
            text = name + ' ' + h.get('desc', '')
            if BAD.search(text) or not GOOD.search(text): continue
            url = h.get('url') or ''
            col = maxd = ''
            if not url:
                col = date_column(dom, rid, engine=engine) or ''
                if col:
                    maxd = newest(dom, rid, col, engine=engine)
                    if maxd and maxd[:4].isdigit():
                        if int(maxd[:4]) < time.localtime().tm_year - stale_years:
                            rows_out.append([rid, dom, name[:120], col, maxd, 0, 0, 'stale'])
                            held.add(rid); continue
                url = 'https://%s/resource/%s.csv?$limit=500000' % (dom, rid)
            b = _get(url, timeout=300, engine=engine)
            held.add(rid)
            if not b or len(b) < 400:
                rows_out.append([rid, dom, name[:120], col, maxd, 0, 0, 'empty']); continue
            safe = re.sub(r'[^A-Za-z0-9_-]+', '_', name)[:70].strip('_') or rid
            d = os.path.join(out, dom.replace('/', '_'))
            os.makedirs(d, exist_ok=True)
            p = os.path.join(d, '%s__%s.csv' % (rid, safe))
            with open(p + '.tmp', 'wb') as f: f.write(b)
            os.replace(p + '.tmp', p)
            nrows = b.count(b'\n')
            rows_out.append([rid, dom, name[:120], col, maxd, nrows, len(b), 'kept'])
            bytes_this_pass += len(b); new += 1
            log('    found', dom, name[:70], '%.1f MB' % (len(b) / 2 ** 20), maxd)

    if rows_out:
        newfile = not os.path.exists(reg)
        with open(reg, 'a', newline='') as f:
            w = csv.writer(f)
            if newfile: w.writerow(['id', 'domain', 'name', 'date_column', 'newest_observation', 'rows', 'bytes', 'verdict'])
            w.writerows(rows_out)
    try: json.dump({'term_index': (start + terms_per_pass) % len(TERMS), 'last_pass': time.strftime('%Y-%m-%d %H:%M')},
                   open(spath, 'w'))
    except Exception: pass
    log('  discovery: %d new datasets, %.0f MB, %d judged stale or empty' %
        (new, bytes_this_pass / 2 ** 20, sum(1 for r in rows_out if r[7] != 'kept')))
    return new


if __name__ == '__main__':
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.join(os.path.dirname(here), '_shared'))
    try: import fetch_engine as fe
    except Exception: fe = None
    run(os.path.join(here, 'warehouse'), engine=fe,
        datasets_per_pass=int(os.environ.get('DISCOVER_N', '40')))
