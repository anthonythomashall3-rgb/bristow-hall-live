"""The non-FRED sources the legs read, pulled fresh at every run (17 September 2026).

The standing collector (collection 191) refreshes its warehouse every six hours and keeps a file for twenty, so the
data page showed the previous week's mortgage rate at noon on the Thursday the new one came out, the OFR index a day
behind, the geopolitical index three days behind. This script pulls the live sources whole or incrementally at each
run and writes into the same warehouse files the collector keeps, which refresh_hf_data.py (collection 190) then
reads into the legs' files:
  ofr    fsi.csv                                   financialresearch.gov          whole file, the collector's fetch-and-derive
  pmms   PMMS_history.csv                          freddiemac.com                 whole file
  cboe   SKEW_History.csv, VVIX_History.csv        cdn.cboe.com                   whole files
  epu    All_Daily_Policy_Data.csv, GPR daily xls  policyuncertainty.com, Iacoviello   whole files
  dts    deposits and withdrawals, last 45 days    api.fiscaldata.treasury.gov    incremental, the collector's category rules
  eia    the five weekly petroleum series           api.eia.gov v2                 incremental
No lock is needed: the collector's lock is taken in its main() only. Prints one line per series whose last day moved
("SID old -> new", which bhs_run.sh reads as new data) and one summary line.  Run: python3 s2/live_sources.py
"""
import os, sys, re, json, datetime, importlib.util, urllib.parse
ROOT = os.path.expanduser('~/Projects/Onset Detector Data')
if not os.path.isdir(ROOT): ROOT = os.path.expanduser('~/mnt/Onset Detector Data')
C191 = os.path.join(ROOT, '191_standing_collector_2026-09-16', 'code')
_argv = sys.argv; sys.argv = [sys.argv[0]]
_spec = importlib.util.spec_from_file_location('collector', os.path.join(C191, 'collector.py')); C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C); sys.argv = _argv
C.FORCE = True
def _quiet_log(*a):   # the collector's log file only, not our stdout
    try: C._LOGF.write('%s live %s\n' % (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), ' '.join(str(x) for x in a))); C._LOGF.flush()
    except Exception: pass
C.log = _quiet_log
WH = C.WH; JOBS = {j['name']: j for j in C.SRC['jobs']}
TODAY = datetime.date.today()

def last_day(path):
    s = C.read_series(path); return max(s) if s else None
WATCH = {   # the derived files the legs read, by source
    'ofr': ['ofr/derived/ofr_fsi_equity_daily.csv'], 'pmms': ['freddiemac/derived/pmms30_weekly.csv'],
    'cboe': ['cboe/derived/SKEW_daily.csv', 'cboe/derived/VVIX_daily.csv'],
    'epu': ['policyuncertainty/derived/epu_us_daily.csv', 'policyuncertainty/derived/gpr_daily.csv'],
    'dts': ['dts/derived/dts_withheld_taxes_daily.csv', 'dts/derived/dts_customs_duties_daily.csv', 'dts/derived/dts_unemployment_insurance_benefits_daily.csv', 'dts/derived/dts_corporate_income_taxes_daily.csv'],
    'eia': ['eia/petroleum_sndw/%s.csv' % s for s in ('WRPUPUS2', 'WGFUPUS2', 'WDIUPUS2', 'WCESTUS1', 'WGTSTUS1')],
    'umich': ['umich/derived/umcsent_sca_monthly.csv']}
before = {p: last_day(os.path.join(WH, p)) for ps in WATCH.values() for p in ps}
fails = []

def files_job(name, keep):
    j = dict(JOBS[name]); j['files'] = [f for f in j['files'] if f['out'] in keep]
    C.job_files(j)
FILES = [('ofr', ['ofr_fsi.csv']), ('pmms', ['PMMS_history.csv']), ('cboe', ['SKEW_History.csv', 'VVIX_History.csv']), ('epu', ['All_Daily_Policy_Data.csv', 'data_gpr_daily_recent.xls'])]

def dts_recent(days=45):
    j = JOBS['dts']; base = j['base'] + 'deposits_withdrawals_operating_cash'
    start = (TODAY - datetime.timedelta(days=days)).isoformat()
    fields = ['record_date', 'transaction_type', 'transaction_catg', 'transaction_today_amt']
    rows = C.fiscal_pages(base, {'sort': 'record_date', 'fields': ','.join(fields), 'filter': 'record_date:gte:' + start}, fields)
    if rows is None: raise RuntimeError('fiscaldata did not answer')
    for name in ('withheld_taxes', 'customs_duties', 'unemployment_insurance_benefits', 'corporate_income_taxes'):
        rule = j['derived'][name]; inc = [re.compile(p, re.I) for p in rule['match']]; exc = [re.compile(p, re.I) for p in rule.get('exclude', [])]
        s = {}
        for d, t, c, v in rows:
            c = c or ''
            if t != rule['type'] or not any(p.search(c) for p in inc) or any(p.search(c) for p in exc): continue
            x = C.num(v)
            if x is None: continue
            s[d] = s.get(d, 0.0) + x
        p = os.path.join(WH, 'dts', 'derived', 'dts_%s_daily.csv' % name); old = C.read_series(p)
        merged = {d: v for d, v in old.items() if d < start}; merged.update(s)
        C.write_series(p, merged, quiet=True)

def eia_recent():
    k = C.key('EIA_API_KEY')
    if not k: raise RuntimeError('no EIA key')
    start = (TODAY - datetime.timedelta(days=70)).isoformat(); sids = ('WRPUPUS2', 'WGFUPUS2', 'WDIUPUS2', 'WCESTUS1', 'WGTSTUS1')
    q = [('api_key', k), ('frequency', 'weekly'), ('data[0]', 'value')] + [('facets[series][]', s) for s in sids] + [('start', start), ('sort[0][column]', 'period'), ('sort[0][direction]', 'asc'), ('length', 500)]
    js = C.http_json('https://api.eia.gov/v2/petroleum/sum/sndw/data/?' + urllib.parse.urlencode(q), timeout=60)   # the five series in one call (17 September 2026)
    data = (js or {}).get('response', {}).get('data', [])
    if not data: raise RuntimeError('no answer')
    by = {}
    for r in data:
        if r.get('value') is not None and r.get('period') and r.get('series') in sids: by.setdefault(r['series'], {})[r['period']] = r['value']
    for sid in sids:
        if sid not in by: fails.append('eia %s: no answer' % sid); continue
        p = os.path.join(WH, 'eia', 'petroleum_sndw', sid + '.csv'); old = C.read_series(p); old.update(by[sid]); C.write_series(p, old, quiet=True)

# The fetch engine's NOT_MODIFIED sentinel, needed to tell an unchanged page from an empty one. Absent when
# the engine is not installed, in which case http_get never returns it.
try:
    import fetch_engine as _FE
except Exception:
    _FE = getattr(C, 'FE', None)


def umich():
    """The Surveys of Consumers press page (sca.isr.umich.edu): the current month's index (preliminary the second
    Friday, final the fourth) and the month before, two months ahead of FRED's UMCSENT, which the source delays by a
    month. Written to warehouse/umich/ and merged onto the FRED file the leg reads (186/data/UMCSENT.csv) for the
    months FRED does not yet carry; the page's own "Next data release" line is kept for the data page."""
    d = os.path.join(WH, 'umich'); os.makedirs(os.path.join(d, 'derived'), exist_ok=True)
    # 18 September 2026: this failed with "press page not parsed" while the page itself was perfectly parseable.
    # The fetch had returned an EMPTY body - not None, so the None guard passed - and the empty body was written
    # over the last good copy before the regexes ran, so the saved evidence was empty too and the error named the
    # wrong thing. Three changes: a browser user agent, because the default one gets an empty answer from this
    # host often enough to matter; a length guard that says what actually came back; and the write moved AFTER
    # that guard, so a bad fetch can no longer destroy the last good page.
    UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) '
                        'Chrome/128.0 Safari/537.36'}
    b = C.http_get('https://www.sca.isr.umich.edu/', headers=UA, timeout=60)
    # THE REAL CAUSE, found 18 September. The collector's fetch engine makes CONDITIONAL requests and returns the
    # sentinel FE.NOT_MODIFIED - which is literally b'' - when the server answers 304. This function checked only
    # for None, so an unchanged page became an empty string, the regexes failed, and it reported "press page not
    # parsed" on every run between releases. It was not a parse failure and it was not an outage: it was the page
    # being unchanged, which is the normal state on twenty-six days out of twenty-eight. Nothing was ever lost.
    if _FE is not None and b is _FE.NOT_MODIFIED:
        # unchanged since the last fetch: answer from the copy on disk, so the data page keeps showing the right
        # release and the run does not record a failure for a page that is simply the same as it was
        try:
            j = json.load(open(os.path.join(d, 'sca_front.json')))
            return j['months'][0], j['sentiment'][0], j['status'][j['months'][0]], j.get('next_release')
        except Exception:
            raise RuntimeError('sca.isr.umich.edu unchanged (304) and no saved copy to answer from')
    if not b or len(b) < 500:
        raise RuntimeError('sca.isr.umich.edu returned %d bytes' % len(b or b''))
    h = b.decode('utf-8', 'replace'); C.write_bytes(os.path.join(d, 'sca_front.html'), b)
    t = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', h))
    m = re.search(r'(Preliminary|Final) Results for (\w+) (\d{4})', t)
    r = re.search(r'Index of Consumer Sentiment ([\d.]+) ([\d.]+) ([\d.]+)', t)
    hd = re.search(r'(\w{3}) (\w{3}) (\w{3}) M-M Y-Y (\d{4}) (\d{4}) (\d{4}) Change', t)
    nx = re.search(r'Next data release: \w+, (\w+ \d{1,2}, \d{4}) for (Preliminary|Final) (\w+) data', t)
    if not (m and r and hd): raise RuntimeError('press page not parsed')
    MON = {mm: i + 1 for i, mm in enumerate(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])}
    months = ['%s-%02d-01' % (hd.group(4 + i), MON[hd.group(1 + i)]) for i in range(3)]
    vals = [float(r.group(1 + i)) for i in range(3)]
    status = {months[0]: m.group(1).lower(), months[1]: 'final', months[2]: 'final'}
    nxt = datetime.datetime.strptime(nx.group(1), '%B %d, %Y').date().isoformat() if nx else None
    C.write_json(os.path.join(d, 'sca_front.json'), {'fetched': datetime.datetime.now().isoformat(timespec='seconds'), 'headline': m.group(0), 'months': months, 'sentiment': vals, 'status': status, 'next_release': nxt, 'next_kind': (nx.group(2).lower() if nx else None)})
    old = C.read_series(os.path.join(d, 'derived', 'umcsent_sca_monthly.csv')); old.update({mo: v for mo, v in zip(months, vals)})
    C.write_series(os.path.join(d, 'derived', 'umcsent_sca_monthly.csv'), old, quiet=True)
    # merge onto the FRED file the leg reads: FRED's months stand; the press page fills the months after them
    f = os.path.join(ROOT, '186_realtime_channels_2026-09-15', 'data', 'UMCSENT.csv')
    if os.path.exists(f):
        rows = [l.split(',') for l in open(f).read().strip().splitlines()]; hdr = rows[0]; body = [x for x in rows[1:] if len(x) >= 2 and x[0][:4].isdigit()]
        fred_last = max(x[0][:10] for x in body) if body else ''
        rows_by = {x[0][:10]: x[1].strip() for x in body}
        changed = False
        for mo, v in zip(months, vals):   # the press page's months are the source's latest word (a preliminary becomes its final); the rest is FRED's
            if rows_by.get(mo) != C.fmt(v): rows_by[mo] = C.fmt(v); changed = True
        if changed:
            with open(f, 'w') as fh:
                fh.write(','.join(hdr) + '\n'); fh.write(''.join('%s,%s\n' % (mo, rows_by[mo]) for mo in sorted(rows_by)))
    return months[0], vals[0], status[months[0]], nxt

# the seven sources at once (17 September 2026, Anthony: "as fast as possible, as safe as possible"): each writes its own
# files, so they share nothing but the collector's log; the slowest source sets the time instead of the sum of all
def _run(label, fn):
    try: return fn()
    except Exception as e: fails.append('%s: %s' % (label, str(e)[:60])); return None
TASKS = [(name, (lambda n=name, k=keep: files_job(n, k))) for name, keep in FILES] + [('dts', dts_recent), ('eia', eia_recent), ('umich', umich)]
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(max_workers=len(TASKS)) as ex: results = dict(zip([t[0] for t in TASKS], ex.map(lambda t: _run(*t), TASKS)))
_u = results.get('umich'); UMICH = ('UMCSENT %s = %s (%s; next %s)' % (_u[0][:7], _u[1], _u[2], _u[3])) if _u else None

after = {p: last_day(os.path.join(WH, p)) for p in before}
moved = [(p, before[p], after[p]) for p in before if after[p] and after[p] != before[p]]
for p, a, b in moved: print('%s %s -> %s' % (os.path.basename(p)[:-4], a or 'none', b))
newest = {os.path.basename(p)[:-4]: after[p] for p in after}
print('live sources: %d pulled, %d moved%s%s | %s' % (len(before), len(moved), ('; ' + UMICH) if UMICH else '', ('; FAILED: ' + '; '.join(fails)) if fails else '',
      ', '.join('%s %s' % (k, v) for k, v in sorted(newest.items(), key=lambda kv: kv[1] or '', reverse=True)[:6])))
sys.exit(1 if fails and not moved and len(fails) >= 4 else 0)
