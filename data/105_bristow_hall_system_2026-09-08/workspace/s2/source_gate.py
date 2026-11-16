# -*- coding: utf-8 -*-
"""THE SOURCE GATE (15 November 2026, collection 1052; Anthony: "make sure that there are NEVER anymore data errors that will EVER
happen again"). No AI. Standard library only.

An audit on 15 November found published numbers that were wrong yet passed every existing check: a CPI tile showing an estimate
(3.9%) instead of the published 12-month change (3.7%); ICNSA and CCNSA values from old rows shown as current (a .dropna().iloc[-1]
fallback); a detector reading frozen since September; 'Next published' days that were the build day, not the publisher's release;
data-page rows held through stale months; a phantom carried-forward month on /state-onset/. Every existing check compared the
site with the site's own files. This one compares the BUILT PAGES with the PUBLISHERS:

  1. inventory  every published figure is read out of the built pages (home tiles, the data page, the detector's embedded state
                and bhs_state.json, /state-onset/, /stress-map/, /forecaster/state.json): page, label, value, unit, period, series,
                transformation.
  2. source     each figure with a FRED/ALFRED/BLS series behind it is fetched independently and recomputed from scratch with its
                declared transformation (level, 12-month % change by date with no estimation, 3-month average change, ratio of
                same-month series, 13-week mean, differences and 12-month highs/lows). Real-time figures are compared with the
                ALFRED vintage that stood on the build day (the first print for first-print figures). Off by more than the
                displayed rounding -> FAIL.
  3. freshness  each figure's period must be the newest the publisher has released (FRED's newest observation, or the BLS API v2
                when FRED has not posted yet); a release posted on the build day itself is a WARN (the publication lag before the
                next run), an older one is a FAIL ('stale'). A label later than the data used -> FAIL ('carried forward').
  4. integrity  no chart point beyond the newest month of its inputs (phantom months); no value from a row older than its cadence
                allows; no estimate unless labelled and allowed; every 'Next published' is the publisher's next release day (FRED's
                release calendar, or the program's documented rule for month averages), never the build day.
  5. behavior   any FAIL -> exit 10 in hold mode (the workflow publishes nothing; the live site keeps the last good build), or a
                warning only in warn mode. A source that cannot be reached is retried; a figure that still cannot be checked is
                UNVERIFIED, which holds only if the figure changed since the last verified build (ops/state/source_gate_verified.json),
                so an outage cannot let a new unverified number out and does not freeze the site either.

Writes out/source_gate_report.json (every figure and every check) and prints a short summary. The mode is read from
ops/source_gate.json ({"mode": "warn"|"hold"}) unless --mode is given.

Usage (from the repository root or anywhere):
  python3 source_gate.py --site <site/public> [--mode warn|hold] [--pages home,data,detector,state,stress,forecaster]
                         [--sources-in cache.json] [--sources-out cache.json] [--now 'YYYY-MM-DD HH:MM'] [--out report.json]
  python3 source_gate.py --live https://bhrrealtime.pages.dev ...      (downloads the live pages first)
"""
import argparse, calendar, copy, datetime as dt, html as htmlmod, json, math, os, re, sys, time, urllib.error, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(WS, '..', '..', '..'))
UA = 'bhr-source-gate/1.0'
MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
LIVE_PAGES = ['index.html', 'data/index.html', 'bhs_state.json', 'detector/index.html', 'state-onset/index.html',
              'stress-map/index.html', 'forecaster/state.json', 'ops/release_calendar.json']
STATES = ['AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'DC', 'FL', 'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
          'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC', 'SD',
          'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY']
# NYSE holidays (the S&P 500 close is not published on them); 2026-2027 from the NYSE calendar
NYSE_HOLIDAYS = {'2026-01-01', '2026-01-19', '2026-02-16', '2026-04-03', '2026-05-25', '2026-06-19', '2026-07-03', '2026-09-07',
                 '2026-11-26', '2026-12-25', '2027-01-01', '2027-01-18', '2027-02-15', '2027-03-26', '2027-05-31', '2027-06-18',
                 '2027-07-05', '2027-09-06', '2027-11-25', '2027-12-24'}
FED_HOLIDAYS = {'2026-01-01', '2026-01-19', '2026-02-16', '2026-05-25', '2026-06-19', '2026-07-03', '2026-09-07', '2026-10-12',
                '2026-11-11', '2026-11-26', '2026-12-25', '2027-01-01', '2027-01-18', '2027-02-15', '2027-05-31', '2027-06-18',
                '2027-07-05', '2027-09-06', '2027-10-11', '2027-11-11', '2027-11-25', '2027-12-24'}
# units of FRED series in which the pages show words like "million": the scale of one FRED unit, in persons/units
FRED_SCALE = {'PAYEMS': 1e3, 'JTSJOL': 1e3, 'UNEMPLOY': 1e3, 'LNS13023621': 1e3, 'ICSA': 1, 'ICNSA': 1, 'CCSA': 1, 'CCNSA': 1}
# a FRED series that the BLS API v2 also serves (used only when FRED has not yet posted the newest period)
# 1052 (16 Nov 2026): the BLS series behind FRED ids, for the publisher fallback when FRED cannot be read (Gate.publisher_rows)
PUB_BLS = {'PAYEMS': 'CES0000000001', 'USMINE': 'CES1000000001', 'USCONS': 'CES2000000001', 'MANEMP': 'CES3000000001',
           'USTPU': 'CES4000000001', 'USINFO': 'CES5000000001', 'USFIRE': 'CES5500000001', 'USPBS': 'CES6000000001',
           'USEHS': 'CES6500000001', 'USLAH': 'CES7000000001', 'USSERV': 'CES0800000001', 'USGOVT': 'CES9000000001',
           'UNRATE': 'LNS14000000', 'UNEMPLOY': 'LNS13000000', 'LNS13023621': 'LNS13023621', 'JTSJOL': 'JTS000000000000000JOL',
           'JTSQUR': 'JTS000000000000000QUR', 'CPIAUCSL': 'CUSR0000SA0', 'CPIAUCNS': 'CUUR0000SA0'}
DOL_OF = {'ICSA': ('ic_week_ended', 'icsa'), 'ICNSA': ('ic_week_ended', 'icnsa'), 'IURSA': ('iu_week_ended', 'iur_sa'), 'CCSA': ('iu_week_ended', 'iusa')}
PUB_BEA = {'GDPC1': ('T10106', '1', 'Q'), 'W875RX1': ('T20600', '36', 'M')}   # W875RX1 = Table 2.6 line 36 (found by ops/speed/parity_publisher_first.py: 33 of 33 months equal FRED's)   # 1052: NIPA table, line, frequency of the BEA series behind FRED ids (publisher fallback)
BLS_OF = {'UNRATE': 'LNS14000000', 'PAYEMS': 'CES0000000001', 'UNEMPLOY': 'LNS13000000', 'LNS13023621': 'LNS13023621',
          'JTSJOL': 'JTS000000000000000JOL', 'JTSQUR': 'JTS000000000000000QUR', 'CPIAUCSL': 'CUSR0000SA0'}
# month averages of daily H.15 / Moody's series: next published by the program's documented rule, not FRED's daily H.15 calendar
MONTH_AVG_RULE = {'FEDFUNDS': 'next_bday', 'GS10': 'next_bday', 'GS1': 'next_bday', 'TB3MS': 'next_bday', 'BAA': 'bday_or_day7'}
# rows that are archives, not live inputs (their period is fixed on purpose); every one is named with its reason
ARCHIVAL = {
    'state payrolls, as first published 1994-2007': 'a closed archive of first prints (1994-2007)',
    'state payroll employment, not seasonally adjusted (history layer before 1979-07)': 'history layer before 1979-07',
    'state initial claims, not seasonally adjusted (history layer before 1979-07)': 'history layer before 1979-07',
    'national disturbance register v3.2': 'the frozen v3.2 register (dated through 2024-06)',
    'state boundaries, 2024 (drawn from the census file)': 'static map geometry',
    'county boundaries, 2024': 'static map geometry',
}
# a published estimate is allowed only here (the publisher's own nowcast is not our estimate)
ALLOWED_ESTIMATES = {'GDPNOW'}
PUB_ANY = set(DOL_OF) | set(PUB_BEA) | {'INDPRO'}   # 1052: series with a publisher read other than the BLS API


# ------------------------------------------------------------------------------------------------------------------- dates
def D(s): return dt.date.fromisoformat(s[:10])
def mkey(s): return s[:7]
def madd(m, k):
    y, mo = int(m[:4]), int(m[5:7]); t = y * 12 + mo - 1 + k; return '%04d-%02d' % (t // 12, t % 12 + 1)
def mdiff(a, b):  # months a - b
    return (int(a[:4]) * 12 + int(a[5:7])) - (int(b[:4]) * 12 + int(b[5:7]))
def bday(d, hol=FED_HOLIDAYS):
    while d.weekday() >= 5 or d.isoformat() in hol: d += dt.timedelta(days=1)
    return d
def label_period(text):
    """'week ending Nov 7, 2026' -> '2026-11-07'; 'Oct 2026' -> '2026-10'; None."""
    if not text: return None
    m = re.search(r'week ending (%s)\w* (\d{1,2}), (\d{4})' % '|'.join(MON), text)
    if m: return '%s-%02d-%02d' % (m.group(3), MON.index(m.group(1)) + 1, int(m.group(2)))
    m = re.search(r'\b(%s)\w* (\d{4})\b' % '|'.join(MON), text)
    if m: return '%s-%02d' % (m.group(2), MON.index(m.group(1)) + 1)
    return None


def parse_num(text):
    """'+137,000 a month' -> (137000.0, tol, mult); '4.1%' -> (4.1, 0.05, 1); '159.3 million' -> (159.3e6, 0.05e6, 1e6)."""
    if text is None: return None
    t = htmlmod.unescape(str(text)).replace('−', '-').replace('−', '-')
    m = re.search(r'([-+]?\d[\d,]*(?:\.\d+)?|[-+]?\.\d+)', t)
    if not m: return None
    s = m.group(1).replace(',', ''); v = float(s)
    dec = len(s.split('.')[1]) if '.' in s else 0
    rest = t[m.end():].lower()
    mult = 1.0
    if re.match(r'\s*(million|mn)\b', rest): mult = 1e6
    elif re.match(r'\s*(billion|bn)\b', rest): mult = 1e9
    elif re.match(r'\s*(thousand|k)\b', rest): mult = 1e3
    if dec == 0:
        z = len(s.lstrip('+-')) - len(s.lstrip('+-').rstrip('0')) if s.lstrip('+-') != '0' else 0
        tol = 0.5 * (10 ** min(z, 3)) if z >= 3 else 0.5
    else:
        tol = 0.5 * 10 ** (-dec)
    return v * mult, tol * mult + 1e-9 * max(1.0, abs(v * mult)), mult


def fmt(x):
    if x is None: return None
    return float('%.6g' % x)


# ------------------------------------------------------------------------------------------------------------------- sources
class Sources:
    """FRED (API with the key the build uses; fredgraph CSV without one), the BLS API v2, and QCEW open data. Every fetch is retried;
    results are cached in memory and can be saved to / loaded from a file (the self-test re-uses one fetch)."""

    def __init__(self, fred_key='', bls_key='', cache=None, offline=False, budget_s=420):
        self.fred_key, self.bls_key = fred_key, bls_key
        self.c = cache if cache is not None else {}
        self.offline = offline
        self.t0 = time.time(); self.budget = budget_s
        self.last_call = 0.0; self.calls = 0; self.errors = {}
        import threading; self._lock = threading.Lock(); self.spacing = 0.55   # 1052 speed: the spacing holds across threads (prefetch)

    def _get(self, url, data=None, headers=None, tries=5):
        if self.offline: raise RuntimeError('offline')
        if time.time() - self.t0 > self.budget: raise RuntimeError('time budget spent')
        err = None
        for i in range(tries):
            if i and time.time() - self.t0 > self.budget: break
            with self._lock:
                wait = self.spacing - (time.time() - self.last_call)     # FRED allows 120 requests a minute
                if wait > 0: time.sleep(wait)
                self.last_call = time.time(); self.calls += 1
            try:
                req = urllib.request.Request(url, data=data, headers=dict({'User-Agent': UA}, **(headers or {})))
                with urllib.request.urlopen(req, timeout=40) as r:
                    return r.read().decode('utf-8', 'replace')
            except urllib.error.HTTPError as e:
                body = e.read().decode('utf-8', 'replace')[:300]
                err = 'HTTP %d %s' % (e.code, body.replace(self.fred_key or '\0', '[key]'))
                if e.code == 400 or e.code == 404: break      # a bad series id: retrying will not help
                if e.code == 429:
                    # 1052 (16 Nov 2026): FRED's limit is per key, and the key is shared by every job running at the moment (the
                    # update, live-tools, a PR's checks). A 429 is a read that came too early, not a missing source: every thread
                    # waits out the minute together (15, 30, 45, 60 s), then the read is tried again.
                    with self._lock: self.last_call = time.time() + min(60, 15 * (i + 1)) - self.spacing
                    continue
            except Exception as e:
                err = type(e).__name__ + ' ' + str(e)[:120]
            time.sleep(min(20, 3 * 2 ** i))
        raise RuntimeError(err or 'unreachable')

    # one call per series: every vintage of every observation since `start` (ALFRED real-time periods)
    def fred(self, sid, start='2024-06-01'):
        key = 'fred:%s:%s' % (sid, start)
        if key in self.c: return self.c[key]
        if key + ':err' in self.c: return None
        try:
            if self.fred_key:
                q = urllib.parse.urlencode(dict(series_id=sid, api_key=self.fred_key, file_type='json', observation_start=start,
                                                realtime_start=start, realtime_end='9999-12-31'))
                try:
                    obs = json.loads(self._get('https://api.stlouisfed.org/fred/series/observations?' + q))['observations']
                    rows = [[o['date'], o['realtime_start'], o['realtime_end'], None if o['value'] in ('.', '') else float(o['value'])] for o in obs]
                except RuntimeError as e:
                    if 'does not exist in ALFRED' not in str(e): raise
                    # a series FRED keeps without vintages (the S&P 500): today's values, no publication days
                    q = urllib.parse.urlencode(dict(series_id=sid, api_key=self.fred_key, file_type='json', observation_start=start))
                    obs = json.loads(self._get('https://api.stlouisfed.org/fred/series/observations?' + q))['observations']
                    rows = [[o['date'], None, '9999-12-31', None if o['value'] in ('.', '') else float(o['value'])] for o in obs]
            else:
                txt = self._get('https://fred.stlouisfed.org/graph/fredgraph.csv?' + urllib.parse.urlencode(dict(id=sid, cosd=start)))
                rows = []
                for line in txt.splitlines()[1:]:
                    p = line.split(',')
                    if len(p) >= 2 and re.match(r'\d{4}-\d\d-\d\d', p[0]):
                        rows.append([p[0], None, '9999-12-31', None if p[1] in ('.', '') else float(p[1])])
            self.c[key] = rows
            return rows
        except Exception as e:
            self.c[key + ':err'] = str(e); self.errors[sid] = str(e)
            return None

    def release_dates(self, sid, today):
        key = 'rel:%s:%s' % (sid, today)
        if key in self.c: return self.c[key]
        if key + ':err' in self.c or not self.fred_key: return None
        try:
            q = urllib.parse.urlencode(dict(series_id=sid, api_key=self.fred_key, file_type='json'))
            rel = json.loads(self._get('https://api.stlouisfed.org/fred/series/release?' + q))['releases'][0]
            start = (D(today) - dt.timedelta(days=40)).isoformat()
            q = urllib.parse.urlencode(dict(release_id=rel['id'], api_key=self.fred_key, file_type='json', realtime_start=start,
                                            realtime_end='9999-12-31', include_release_dates_with_no_data='true',
                                            sort_order='asc', limit=200))
            dates = [x['date'] for x in json.loads(self._get('https://api.stlouisfed.org/fred/release/dates?' + q))['release_dates']]
            out = {'release_id': rel['id'], 'release': rel.get('name'), 'dates': sorted(set(d for d in dates if d >= start))}
            self.c[key] = out; return out
        except Exception as e:
            self.c[key + ':err'] = str(e); return None

    def bls(self, ids, start_year):
        key = 'bls:%s:%s' % (','.join(sorted(ids)), start_year)
        if key in self.c: return self.c[key]
        if key + ':err' in self.c: return None
        try:
            body = {'seriesid': sorted(ids), 'startyear': str(start_year), 'endyear': str(dt.date.today().year)}
            if self.bls_key: body['registrationkey'] = self.bls_key
            j = json.loads(self._get('https://api.bls.gov/publicAPI/v2/timeseries/data/', data=json.dumps(body).encode(),
                                     headers={'Content-Type': 'application/json'}))
            if j.get('status') != 'REQUEST_SUCCEEDED': raise RuntimeError('BLS: %s' % (j.get('message') or j.get('status')))
            out = {}
            for s in j['Results']['series']:
                vals = {}
                for o in s['data']:
                    if not o['period'].startswith('M') or o['period'] == 'M13': continue
                    try: vals['%s-%s' % (o['year'], o['period'][1:])] = float(o['value'])
                    except ValueError: pass
                out[s['seriesID']] = vals
            self.c[key] = out; return out
        except Exception as e:
            self.c[key + ':err'] = str(e); return None

    def bea(self, table, line, freq):
        """one NIPA line from the BEA API (key BEA_API_KEY): {'YYYY-MM': value in billions}. 1052: the publisher fallback for GDP."""
        key = 'bea:%s:%s:%s' % (table, line, freq)
        if key in self.c: return self.c[key]
        if key + ':err' in self.c: return None
        try:
            k = os.environ.get('BEA_API_KEY', '').strip()
            if not k: raise RuntimeError('no BEA key')
            q = urllib.parse.urlencode(dict(UserID=k, method='GetData', datasetname='NIPA', TableName=table, Frequency=freq, Year='ALL', ResultFormat='JSON'))
            res = json.loads(self._get('https://apps.bea.gov/api/data?' + q).replace(k, '[key]'))['BEAAPI']['Results']
            res = res[0] if isinstance(res, list) else res
            out = {}
            for o in res.get('Data', []):
                if str(o.get('LineNumber')) != str(line): continue
                tp = o['TimePeriod']
                m = '%s-%02d' % (tp[:4], (int(tp[5]) - 1) * 3 + 1) if 'Q' in tp else '%s-%s' % (tp[:4], tp[5:7])
                try: out[m] = float(o['DataValue'].replace(',', '')) * 10 ** int(o.get('UNIT_MULT') or 0) / 1e9
                except ValueError: pass
            if not out: raise RuntimeError('BEA: no line %s in %s' % (line, table))
            self.c[key] = out; return out
        except Exception as e:
            self.c[key + ':err'] = str(e); return None

    def dol_press(self):
        """the Department of Labor's weekly claims release (data.pdf), read again and parsed by the update's own parser (bhs_dol_press.py):
        {'ic_week_ended', 'icsa', 'icnsa', 'iu_week_ended', 'iur_sa', 'iusa', 'release_date'}. 1052: the claims before FRED posts them."""
        key = 'dolpress'
        if key in self.c: return self.c[key]
        if key + ':err' in self.c: return None
        try:
            if self.offline: raise RuntimeError('offline')
            import tempfile, subprocess, importlib.util
            tmp = os.path.join(tempfile.mkdtemp(prefix='sg_dol_'), 'data.pdf')
            r = subprocess.run(['curl', '-sSL', '-m', '60', '--retry', '3', '--retry-delay', '5', '-o', tmp, 'https://www.dol.gov/ui/data.pdf'], capture_output=True, text=True)
            if r.returncode != 0 or open(tmp, 'rb').read(5) != b'%PDF-': raise RuntimeError('DOL release not fetched')
            spec = importlib.util.spec_from_file_location('bhs_dol_press_sg', os.path.join(WS, 'bhs_dol_press.py')); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
            import pandas as _pd
            row = m.parse(m._text(tmp), _pd.Timestamp(dt.date.today()))
            self.c[key] = {k: row[k] for k in ('ic_week_ended', 'icsa', 'icnsa', 'iu_week_ended', 'iur_sa', 'iusa', 'release_date')}; return self.c[key]
        except Exception as e:
            self.c[key + ':err'] = str(e); return None

    def g17(self, code='B50001'):
        """the Federal Reserve's G.17 data file (ip_sa.txt): {'YYYY-MM': value} of one seasonally adjusted series (B50001 = INDPRO).
        1052 speed: the publisher's own print, read where FRED has not posted the release yet."""
        key = 'g17:%s' % code
        if key in self.c: return self.c[key]
        if key + ':err' in self.c: return None
        try:
            out = {}
            for ln in self._get('https://www.federalreserve.gov/releases/g17/Current/ipdisk/ip_sa.txt').splitlines():
                p = ln.split()
                if len(p) >= 3 and p[0] == '"%s"' % code and p[1].isdigit():
                    for m, v in enumerate(p[2:14], 1):
                        try: out['%s-%02d' % (p[1], m)] = float(v)
                        except ValueError: pass
            if not out: raise RuntimeError('G.17: no %s in the file' % code)
            self.c[key] = out; return out
        except Exception as e:
            self.c[key + ':err'] = str(e); return None

    def dol539(self):
        """the Department of Labor's ETA 539 file (the State weekly claims the build reads), re-read: each State's newest week of
        initial claims (rptdate) and of continued claims (the reflecting week c2)."""
        key = 'dol539'
        if key in self.c: return self.c[key]
        if key + ':err' in self.c: return None
        try:
            import csv, io
            txt = self._get('https://oui.doleta.gov/unemploy/csv/ar539.csv')
            out = {}
            for r in csv.DictReader(io.StringIO(txt)):
                st = r.get('st'); o = out.setdefault(st, {'ic': '', 'cc': ''})
                if (r.get('c3') or '').strip() and r['rptdate'] > o['ic']: o['ic'] = r['rptdate'][:10]
                if (r.get('c8') or '').strip() and (r.get('c2') or '')[:10] > o['cc']: o['cc'] = r['c2'][:10]
            if len(out) < 50: raise RuntimeError('the ETA 539 file has %d States' % len(out))
            self.c[key] = out; return out
        except Exception as e:
            self.c[key + ':err'] = str(e); self.errors['ETA539'] = str(e); return None

    def qcew_has(self, year, q):
        key = 'qcew:%d:%d' % (year, q)
        if key in self.c: return self.c[key]
        try:
            self._get('https://data.bls.gov/cew/data/api/%d/%d/area/US000.csv' % (year, q), tries=2); self.c[key] = True
        except Exception as e:
            self.c[key] = (False if 'HTTP 404' in str(e) else None)
        return self.c[key]

    def save(self, path):
        json.dump(self.c, open(path, 'w'))


class Series:
    """A FRED series as fetched: the current values, each observation's first publication day and first print, and the values as
    they stood on any day (ALFRED)."""

    def __init__(self, sid, rows):
        self.sid = sid; self.rows = rows or []
        self.cur, self.first_pub, self.first_val = {}, {}, {}
        for d, rs, re_, v in self.rows:
            if re_ == '9999-12-31': self.cur[d] = v
            if rs is not None and (d not in self.first_pub or rs < self.first_pub[d]):
                self.first_pub[d] = rs; self.first_val[d] = v
        self.dates = sorted(k for k, v in self.cur.items() if v is not None)

    @property
    def newest(self): return self.dates[-1] if self.dates else None

    def on(self, day):
        """{date: value} as it stood on `day` (the ALFRED vintage)."""
        if not self.rows or self.rows[0][1] is None: return {k: v for k, v in self.cur.items() if v is not None}
        out = {}
        for d, rs, re_, v in self.rows:
            if rs <= day <= re_ and v is not None: out[d] = v
        return out

    def newest_on(self, day):
        o = self.on(day); return max(o) if o else None


# ------------------------------------------------------------------------------------------------------------------- report
class Report:
    def __init__(self):
        self.rows = []

    def add(self, page, label, check, status, value=None, period=None, series=None, transform=None, expected=None, detail=''):
        self.rows.append(dict(page=page, label=label, check=check, status=status, value=value, period=period, series=series,
                              transform=transform, expected=expected, detail=detail))

    def counts(self):
        out = {}
        for r in self.rows:
            p = out.setdefault(r['page'], {}); p[r['status']] = p.get(r['status'], 0) + 1
        return out


# ------------------------------------------------------------------------------------------------------------------- the checks
class Gate:
    def __init__(self, site, src, now, verified, rep):
        self.site, self.src, self.now, self.verified, self.R = site, src, now, verified, rep
        self.today = now.date().isoformat()
        self._s = {}
        self.build_day = self.today
        self.figures = []     # (key, value, period, status) for the verified store

    # ---- helpers
    def later_today(self, cells):
        """15 Nov 2026: a next-published time later on the build day itself is in the future. The cell reads
        'Mon D, YYYY, H:MM AM/PM ET'; the build time is the state's built_at (ET wall clock, 'YYYY-MM-DD HH:MM')."""
        m = re.search(r'(\d{1,2}):(\d{2}) (AM|PM) ET', re.sub(r'<[^>]+>', ' ', cells or ''))
        b = re.search(r'\d{4}-\d{2}-\d{2}[T ](\d{2}):(\d{2})', str((getattr(self, '_S', None) or {}).get('built_at') or ''))
        if not m or not b: return False
        h = int(m.group(1)) % 12 + (12 if m.group(3) == 'PM' else 0)
        return h * 60 + int(m.group(2)) > int(b.group(1)) * 60 + int(b.group(2))

    def S(self, sid, start='2024-06-01'):
        k = (sid, start)
        if k not in self._s:
            rows = self.src.fred(sid, start)
            if rows is None: rows = self.publisher_rows(sid, start)
            self._s[k] = Series(sid, rows) if rows is not None else None
        return self._s[k]

    def publisher_rows(self, sid, start):
        """1052 (16 Nov 2026): FRED could not be read after its retries. For a series the publisher serves itself - the BLS API v2
        (labour series, CPI, the payroll supersectors) and the Fed's G.17 file (INDPRO) - the publisher's current values stand in, so
        the figure is checked against the source of record instead of going unverified. No vintages: the values as of now, which on a
        build's own run are the build day's. None when the publisher cannot be read either (the figure is then unverified, as before)."""
        try:
            if sid == 'INDPRO':
                vals = self.src.g17() or {}
            elif sid in PUB_BEA:
                vals = self.src.bea(*PUB_BEA[sid]) or {}
            elif sid in PUB_BLS:
                vals = {}
                if PUB_BLS[sid] in BLS_OF.values():      # the bundle the gate reads anyway (value_on, bls_newest): one call for all
                    vals = (self.src.bls(list(BLS_OF.values()), self.now.year - 1) or {}).get(PUB_BLS[sid]) or {}
                if not vals:
                    vals = (self.src.bls([PUB_BLS[sid]], int(start[:4])) or {}).get(PUB_BLS[sid]) or {}
            else:
                return None
            rows = [['%s-01' % m, None, '9999-12-31', v] for m, v in sorted(vals.items()) if '%s-01' % m >= start]
            if not rows: return None
            self.R.add('sources', sid, 'source', 'WARN', detail='FRED could not be read: checked against the publisher (%s)' % ('G.17 file' if sid == 'INDPRO' else ('BEA API %s line %s' % PUB_BEA[sid][:2]) if sid in PUB_BEA else 'BLS API v2 ' + PUB_BLS[sid]))
            return rows
        except Exception:
            return None

    def dol_series(self, st, which):
        """a State's newest DOL week as a one-observation series (which: 'ic' initial claims, 'cc' continued/insured); st='US*' = the
        newest across States."""
        d = self.src.dol539()
        if not d: return None
        if st == 'US*':
            w = max((v[which] for v in d.values() if v.get(which)), default=None)
        else:
            w = (d.get(st) or {}).get(which)
        if not w: return None
        return Series('DOL539:%s:%s' % (st, which), [[w, None, '9999-12-31', 1.0]])

    def read(self, rel):
        p = os.path.join(self.site, rel)
        if not os.path.exists(p): return None
        return open(p, encoding='utf-8', errors='replace').read()

    def obs_key(self, s, period):
        """the observation date of `period` ('YYYY-MM' -> 'YYYY-MM-01'; a week end stays; a quarter month -> its quarter start)."""
        if period is None: return None
        if len(period) == 7:
            k = period + '-01'
            if s and k not in s.cur and s.dates and all(x[5:7] in ('01', '04', '07', '10') for x in s.dates[-4:]):
                m = int(period[5:7]); k = '%s-%02d-01' % (period[:4], (m - 1) // 3 * 3 + 1)
            return k
        return period

    def norm_period(self, s, through, freq):
        """a data-page 'through' (month end, month start, week end) in the series' own observation key."""
        if not through: return None
        if freq in ('weekly', 'daily'): return through[:10]
        return self.obs_key(s, through[:7])

    def unverified(self, page, label, value, period, series, transform, why, check='source'):
        key = '%s|%s|%s' % (page, label, series)
        last = self.verified.get(key)
        same = last is not None and str(last.get('value')) == str(value) and str(last.get('period')) == str(period)
        if same:
            self.R.add(page, label, check, 'UNVERIFIED', value, period, series, transform,
                       detail='%s; unchanged since the last verified build: it may stay' % why)
        else:
            self.R.add(page, label, check, 'FAIL', value, period, series, transform,
                       detail='UNVERIFIED and %s since the last verified build (%s): a new number that cannot be checked is held'
                              % ('new' if last is None else 'changed', why))

    def remember(self, page, label, series, value, period):
        self.figures.append(('%s|%s|%s' % (page, label, series), value, period))

    def fresh(self, page, label, s, period, freq='', value=None, transform='', need_lag=None):
        """FAIL if a newer period than `period` was published before the build day; WARN if only on the build day; FAIL if
        `period` is later than anything the publisher has (carried forward / phantom)."""
        if s is None or not s.dates:
            return self.unverified(page, label, value, period, getattr(s, 'sid', None), transform, 'the source could not be read', 'freshness')
        p = period
        newest = s.newest
        if need_lag:      # a transformation that needs an earlier observation: the newest period it can be computed for
            ok = [d for d in s.dates if need_lag(d) in s.cur and s.cur.get(need_lag(d)) is not None]
            newest = ok[-1] if ok else newest
        if p is None:
            self.R.add(page, label, 'freshness', 'FAIL', value, p, s.sid, transform, newest, 'no period could be read for the figure'); return
        if p > newest:
            # beyond FRED: FRED may not have posted the release yet; the BLS API decides for BLS series
            b = self.pub_newest(s.sid)
            if b and b >= p[:len(b)]:
                self.R.add(page, label, 'freshness', 'PASS', value, p, s.sid, transform, b, 'newest at the publisher (FRED has not posted it yet)')
            elif b is None and s.sid not in BLS_OF and s.sid not in PUB_ANY:
                self.R.add(page, label, 'freshness', 'FAIL', value, p, s.sid, transform, newest,
                           'labelled %s but the publisher has nothing after %s: carried forward or phantom' % (p, newest))
            else:
                self.R.add(page, label, 'freshness', 'FAIL', value, p, s.sid, transform, newest,
                           'labelled %s but the newest published is %s: carried forward or phantom' % (p, newest))
            return
        if p < newest:
            later = [d for d in s.dates if d > p]
            pubs = [s.first_pub[d] for d in later if s.first_pub.get(d)]
            pub = min(pubs) if pubs else None
            if pub and pub >= self.build_day:
                self.R.add(page, label, 'freshness', 'WARN', value, p, s.sid, transform, newest,
                           'a newer period (%s) was published %s, on or after the build day: the next run takes it' % (newest, pub))
            else:
                self.R.add(page, label, 'freshness', 'FAIL', value, p, s.sid, transform, newest,
                           'stale: shows %s but %s was published %s' % (p, newest, pub or 'before the build'))
            return
        self.R.add(page, label, 'freshness', 'PASS', value, p, s.sid, transform, newest)

    def pub_newest(self, sid):
        """1052 speed: the newest period the PUBLISHER has, for a series read from its publisher before FRED posts it: the BLS API, the
        G.17 file (INDPRO), the BEA API (GDPC1, W875RX1), the Department's weekly release (claims). 'YYYY-MM' (monthly) or 'YYYY-MM-DD'."""
        if sid in BLS_OF: return self.bls_newest(sid)
        if sid == 'INDPRO': g = self.src.g17() or {}; return max(g) if g else None
        if sid in PUB_BEA: b = self.src.bea(*PUB_BEA[sid]) or {}; return max(b) if b else None
        if sid in DOL_OF: d = self.src.dol_press() or {}; return d.get(DOL_OF[sid][0])
        return None

    def bls_newest(self, sid):
        bid = BLS_OF.get(sid)
        if not bid: return None
        j = self.src.bls(list(BLS_OF.values()), self.now.year - 1)
        if not j or bid not in j or not j[bid]: return None
        return max(j[bid])

    def value_on(self, s, day, period):
        """the value of `period` as it stood on `day`; the BLS API for a BLS period FRED has not posted yet."""
        v = s.on(day).get(period)
        if v is None and s.sid in BLS_OF and period not in s.cur:
            j = self.src.bls(list(BLS_OF.values()), self.now.year - 1) or {}
            v = (j.get(BLS_OF[s.sid]) or {}).get(period[:7])
        if v is None and s.sid == 'INDPRO' and period not in s.cur:   # 1052 speed: the G.17 print before FRED posts it
            v = (self.src.g17() or {}).get(period[:7])
        if v is None and s.sid in PUB_BEA and period not in s.cur:    # 1052 speed: the BEA print before FRED posts it
            v = (self.src.bea(*PUB_BEA[s.sid]) or {}).get(period[:7])
        if v is None and s.sid in DOL_OF and period not in s.cur:     # 1052 speed: the Department's release before FRED posts it
            d = self.src.dol_press() or {}
            if d.get(DOL_OF[s.sid][0]) == period[:10] and d.get(DOL_OF[s.sid][1]) not in (None, ''): v = float(d[DOL_OF[s.sid][1]])
        return v

    def compare(self, page, label, published, expected, tol, series, period, transform, detail=''):
        if expected is None:
            return self.unverified(page, label, published, period, series, transform,
                                   'the source has no value to recompute it from (%s)' % (detail or 'missing observation'), 'value')
        pv = published if isinstance(published, (int, float)) else None
        if pv is None:
            self.R.add(page, label, 'value', 'FAIL', published, period, series, transform, fmt(expected), 'the published value could not be read'); return
        if abs(pv - expected) <= tol:
            self.R.add(page, label, 'value', 'PASS', fmt(pv), period, series, transform, fmt(expected), detail)
        else:
            self.R.add(page, label, 'value', 'FAIL', fmt(pv), period, series, transform, fmt(expected),
                       'published %s, the source gives %s (%s)%s' % (fmt(pv), fmt(expected), transform, ('; ' + detail) if detail else ''))

    def recompute(self, transform, sids, period, day, scale=1.0):
        """the figure from scratch. period is the observation key ('YYYY-MM-01' or a week end)."""
        ss = [self.S(x) for x in sids]
        if any(s is None for s in ss): return None, 'source unreachable'
        s = ss[0]
        def at(sr, k): return self.value_on(sr, day, k)
        def back(k, n):
            if len(k) == 10 and k.endswith('-01') and (s.dates and s.dates[-1].endswith('-01')):
                return madd(k[:7], -n) + '-01'
            return (D(k) - dt.timedelta(weeks=n)).isoformat()
        if transform == 'level':
            v = at(s, period); return (None if v is None else v * scale), None
        if transform == 'yoy':
            a, b = at(s, period), at(s, back(period, 12))
            if a is None or b is None: return None, 'no observation for %s or 12 months earlier' % period
            return (a / b - 1) * 100, None
        if transform == 'avgchg3':
            a, b = at(s, period), at(s, back(period, 3))
            if a is None or b is None: return None, 'no observation for %s or 3 months earlier' % period
            return (a - b) / 3 * scale, None
        if transform == 'ratio':
            a, b = at(ss[0], period), at(ss[1], period)
            if a is None or not b: return None, 'no same-month observations'
            return a / b, None
        if transform == 'mean13':
            o = s.on(day); ks = sorted(k for k in o if k <= period)[-13:]
            if len(ks) < 13: return None, 'fewer than 13 weeks'
            return sum(o[k] for k in ks) / 13, None
        if transform == 'diff1':
            a, b = at(s, period), at(s, back(period, 1))
            return (None, 'missing') if a is None or b is None else (a - b, None)
        if transform == 'diff12':
            a, b = at(s, period), at(s, back(period, 12))
            return (None, 'missing') if a is None or b is None else (a - b, None)
        if transform == 'spread':
            a, b = at(ss[0], period), at(ss[1], period)
            return (None, 'missing') if a is None or b is None else (a - b, None)
        if transform in ('vs_high12', 'vs_high12_pct', 'vs_low12'):
            a = at(s, period); prior = [at(s, back(period, i)) for i in range(1, 13)]
            if a is None or any(x is None for x in prior): return None, 'missing months in the prior 12'
            if transform == 'vs_high12': return max(prior) - a, None     # 'below their high': positive when under it
            if transform == 'vs_high12_pct': return (a / max(prior) - 1) * 100, None
            return a - min(prior), None
        if transform == 'sp_yoy':
            o = s.on(day); a = o.get(period)
            # the reading of the build day: its newest close against the last close on or before 365 days before that day
            ago = (D(day) - dt.timedelta(days=365)).isoformat(); ks = [k for k in o if k <= ago]
            if a is None or not ks: return None, 'missing'
            return (a / o[max(ks)] - 1) * 100, None
        return None, 'no recipe for %s' % transform

    def next_check(self, page, label, nxt, sids, through=None, freq=''):
        """'Next published' must be the publisher's next release day after the build, never the build day itself."""
        if not nxt or not re.match(r'\d{4}-\d\d-\d\d', nxt):
            return
        bd = self.build_day
        sid = sids[0] if sids else None
        exp, how = None, ''
        if sid in MONTH_AVG_RULE and through:
            # the month after the newest month held is the next to be posted: its first business day (the publisher) or, for
            # Moody's Baa, the 7th (the day the program reads it); a day already gone moves to the month after
            days = (1, 7) if MONTH_AVG_RULE[sid] == 'bday_or_day7' else (1,)
            exp_set = set()
            for day in days:
                for k in (2, 3):
                    m = madd(through[:7], k); c = bday(dt.date(int(m[:4]), int(m[5:7]), day)).isoformat()
                    if c > bd: exp_set.add(c); break
            exp = min(exp_set) if exp_set else None
            how = 'the month average is posted the first business day after the month%s' % (' (read the 7th)' if len(days) > 1 else '')
            ok = nxt in exp_set
        elif sid == 'SP500':
            d = D(bd) + dt.timedelta(days=1)
            while d.weekday() >= 5 or d.isoformat() in NYSE_HOLIDAYS: d += dt.timedelta(days=1)
            exp, how = d.isoformat(), 'the next NYSE trading day'
            ok = nxt in (exp, bd) and (nxt != bd or D(bd).weekday() < 5 and bd not in NYSE_HOLIDAYS)
        elif sid:
            group = list(dict.fromkeys(sids))
            if re.search(r'(ICLAIMS|CCLAIMS|INSUREDUR)$', sid):
                group = [sid, 'ICSA']      # the State weekly claims: DOL's Thursday release, or FRED's State claims report
            rels = [r for r in (self.src.release_dates(x, bd) for x in group) if r]
            rel = None
            if rels:
                nexts = sorted({min([d for d in r['dates'] if d > bd] or ['9999']) for r in rels})
                rel = {'release_id': '+'.join(str(r['release_id']) for r in rels), 'release': ' / '.join(r['release'] or '' for r in rels),
                       'dates': sorted(set(d for r in rels for d in r['dates'])), 'accept': nexts if re.search(r'(ICLAIMS|CCLAIMS|INSUREDUR)$', sid) else nexts[:1]}
            if not rel:
                if nxt <= bd:
                    self.R.add(page, label, 'next published', 'FAIL', nxt, None, sid, None, None, 'next published %s is not after the build day %s' % (nxt, bd))
                else:
                    self.R.add(page, label, 'next published', 'WARN', nxt, None, sid, None, None, 'the release calendar could not be read; next is after the build day')
                return
            ds = rel['dates']
            exp = rel['accept'][0] if rel['accept'] else None
            how = 'FRED release %s (%s)' % (rel['release_id'], rel['release'])
            ok = (nxt in rel['accept']) or (nxt == bd and bd in ds)
        else:
            exp, how = None, 'no series to look the release up by'
            ok = nxt > bd
            if ok:
                self.R.add(page, label, 'next published', 'WARN', nxt, None, None, None, None,
                           'after the build day, but no publisher calendar to confirm it (no series id on the row)'); return
        if ok:
            self.R.add(page, label, 'next published', 'PASS', nxt, None, sid, None, exp, how)
        else:
            self.R.add(page, label, 'next published', 'FAIL', nxt, None, sid, None, exp,
                       'next published %s; the publisher\'s next release is %s (%s)%s' % (
                           nxt, exp, how, ' - that is the build day' if nxt == bd else ''))

    # ================================================================================================= pages
    def home(self):
        t = self.read('index.html')
        if t is None: self.R.add('home', 'index.html', 'inventory', 'FAIL', detail='the home page is missing'); return
        i = t.find('const H=')
        if i < 0: self.R.add('home', 'tiles', 'inventory', 'FAIL', detail='the tile data (const H=) is not on the home page'); return
        H, _ = json.JSONDecoder().raw_decode(t[i + 8:])
        RECIPES = {'unemployment rate': ('level', ['UNRATE']), 'nonfarm payrolls': ('level', ['PAYEMS']),
                   'payroll growth': ('avgchg3', ['PAYEMS']), 'initial claims (week)': ('level', ['ICSA']),
                   'insured unemployment rate': ('level', ['IURSA']), 'job openings': ('level', ['JTSJOL']),
                   'unemployed per opening': ('ratio', ['UNEMPLOY', 'JTSJOL']), 'quits rate': ('level', ['JTSQUR']),
                   'cpi inflation': ('yoy', ['CPIAUCSL'])}
        for tile in H.get('tiles') or []:
            lab, val, sub = tile.get('lab', ''), tile.get('val', ''), tile.get('sub', '')
            r = RECIPES.get(lab.lower())
            if r is None:
                ids = [re.sub(r'^(FRED|ALFRED)\s+', '', s[0]) for s in tile.get('srcs') or [] if s and re.match(r'(FRED|ALFRED)\s', s[0])]
                if not ids and tile.get('sid'): ids = [tile['sid']]
                tr = 'yoy' if 'year over year' in sub else 'avgchg3' if '3-month' in sub else 'ratio' if (' per ' in lab.lower() and len(ids) > 1) else 'level'
                r = (tr, ids)
            tr, sids = r
            self.estimate_check('home', lab, val + ' ' + sub, sids)
            if not sids:
                self.R.add('home', lab, 'source', 'WARN', val, None, None, None, detail='no source series on the tile: not source-checked'); continue
            period = label_period(sub)
            s = self.S(sids[0])
            pk = self.obs_key(s, period)
            pn = parse_num(val)
            scale = 1.0
            if pn and pn[2] != 1 or tr == 'avgchg3':
                scale = FRED_SCALE.get(sids[0], 1.0)
            if s is None:
                self.unverified('home', lab, val, pk, sids[0], tr, 'the source could not be read'); continue
            if tr == 'ratio':
                s2 = self.S(sids[1])
                both = sorted(set(s.dates) & set(s2.dates)) if s2 else []
                self.fresh_ratio('home', lab, pk, both, s, s2, val)
            else:
                self.fresh('home', lab, s, pk, value=val, transform=tr,
                           need_lag=(lambda d: madd(d[:7], -12) + '-01') if tr == 'yoy' else (lambda d: madd(d[:7], -3) + '-01') if tr == 'avgchg3' else None)
            exp, why = self.recompute(tr, sids, pk, self.build_day, scale)
            self.compare('home', lab, pn[0] if pn else None, exp, pn[1] if pn else 0, sids[0], pk, tr, why or '')
            self.remember('home', lab, sids[0], val, pk)
            self.next_check('home', lab, tile.get('next'), list(dict.fromkeys(sids + ([tile['sid']] if tile.get('sid') else []))), pk)
        # the indicator's own tile and its sparkline: the detector's own reading on the build day
        S = self.detector_state()
        if S and H.get('last_date'):
            ser = S.get('series') or {}
            ok = ser.get('dates') and H['last_date'] == ser['dates'][-1] and abs((H.get('last_value') or 0) - (ser['values'][-1] or 0)) < 5e-4
            self.R.add('home', 'Bristow-Hall Rule, recession indicator', 'matches the detector', 'PASS' if ok else 'FAIL',
                       H.get('last_value'), H.get('last_date'), 'BHRREALTIME', 'the detector reading',
                       (ser.get('values') or [None])[-1], '' if ok else 'the home tile is not the detector\'s newest reading')
            if H['last_date'] > self.build_day:
                self.R.add('home', 'Bristow-Hall Rule, recession indicator', 'phantom', 'FAIL', H['last_date'], detail='dated after the build day')

    def fresh_ratio(self, page, lab, pk, both, s, s2, val):
        if not both: return self.unverified(page, lab, val, pk, s.sid, 'ratio', 'no same-month observations')
        if pk == both[-1]: self.R.add(page, lab, 'freshness', 'PASS', val, pk, s.sid + '/' + s2.sid, 'ratio', both[-1])
        elif pk < both[-1]:
            pub = max(s.first_pub.get(both[-1]) or '0', s2.first_pub.get(both[-1]) or '0')
            st = 'WARN' if pub >= self.build_day else 'FAIL'
            self.R.add(page, lab, 'freshness', st, val, pk, s.sid + '/' + s2.sid, 'ratio', both[-1], 'stale: both series have %s (published %s)' % (both[-1], pub))
        else:
            self.R.add(page, lab, 'freshness', 'FAIL', val, pk, s.sid + '/' + s2.sid, 'ratio', both[-1], 'labelled after the newest same-month pair')

    def estimate_check(self, page, label, text, sids):
        if re.search(r'\bestimat|\bnowcast|\bprojected\b|\bimputed\b', text or '', re.I) and not (set(sids or []) & ALLOWED_ESTIMATES):
            self.R.add(page, label, 'estimate', 'FAIL', text[:80], detail='an estimate is published where the rules allow only published figures')

    # ---- the data page
    def data_page(self):
        t = self.read('data/index.html')
        if t is None: self.R.add('data', 'data/index.html', 'inventory', 'FAIL', detail='the data page is missing'); return
        rows = re.findall(r'<tr data-tool="([^"]*)" data-name="([^"]*)" data-ids="([^"]*)" data-value="([^"]*)" data-freq="([^"]*)" '
                          r'data-through="([^"]*)" data-next="([^"]*)"(.*?)</tr>', t, re.S)
        if not rows: self.R.add('data', 'rows', 'inventory', 'FAIL', detail='no rows could be read off the data page'); return
        cal = self.calendar_rows()
        ROW_RECIPES = {'iursa': ('level', 'IURSA'), 'cpiaucsl': ('yoy', 'CPIAUCSL'), 'jtsqur': ('level', 'JTSQUR'),
                       'cfnaima3': ('level', 'CFNAIMA3'), 'wei': ('mean13', 'WEI')}
        for tool, name, ids, value, freq, through, nxt, rest in rows:
            tool = tool.split(' ', 1)[-1]; name = htmlmod.unescape(name); value = htmlmod.unescape(value)
            page = 'data/' + tool; label = name
            idl = [x.strip() for x in re.split(r'[,/]', ids) if x.strip()]
            if name in ARCHIVAL:
                self.R.add(page, label, 'freshness', 'INFO', value, through, ids, None, None, 'archival: ' + ARCHIVAL[name])
                if nxt and (nxt < self.build_day or (nxt == self.build_day and not self.later_today(rest))):
                    self.R.add(page, label, 'next published', 'FAIL', nxt, detail='next published is not after the build time')
                continue
            if freq == 'static':
                self.R.add(page, label, 'freshness', 'INFO', value, through, ids, detail='static file'); continue
            self.estimate_check(page, label, value + ' ' + re.sub(r'<[^>]+>', ' ', rest), [x.upper() for x in idl])
            # representative FRED series for the row: a 'xx ... yy' group stands for every State; AL, CA and WY are read
            reps = []
            for x in idl:
                if '...' in x:
                    a = x.split('...')[0].strip()
                    suf = a[2:].upper()
                    reps += ['AL' + suf, 'CA' + suf, 'WY' + suf]
                elif re.match(r'^[a-z0-9_]+$', x):
                    reps.append(x.upper())
            vals = re.findall(r'<div class="v"><b>([^<]*)</b><span class="u">([^<]*)</span></div>', rest)
            row_period = through
            # --- values with their own series id
            for vtxt, utxt in vals:
                utxt = htmlmod.unescape(utxt); sid = utxt.split(' · ')[0].strip()
                if not re.match(r'^[A-Z0-9_]+$', sid): continue
                s = self.S(sid)
                own = label_period(utxt)
                if sid == 'GDPNOW':
                    self.gdpnow(page, label, vtxt, through, s); continue
                pk = own if own else self.norm_period(s, through, freq)
                pn = parse_num(vtxt)
                if s is None:
                    self.unverified(page, '%s: %s' % (label, sid), vtxt, pk, sid, 'level', 'the source could not be read'); continue
                self.fresh(page, '%s: %s' % (label, sid), s, pk, freq, vtxt, 'level')
                exp, why = self.recompute('level', [sid], pk, self.build_day)
                self.compare(page, '%s: %s' % (label, sid), pn[0] if pn else None, exp, pn[1] if pn else 0, sid, pk, 'level', why or '')
                self.remember(page, '%s: %s' % (label, sid), sid, vtxt, pk)
            # --- a single value on the row
            if not vals:
                key = ids.strip().lower()
                if key in ROW_RECIPES and re.search(r'\d', value or '') and not re.match(r'^\d+ files?$', value):
                    tr, sid = ROW_RECIPES[key]; s = self.S(sid)
                    pk = self.norm_period(s, through, freq)
                    pn = parse_num(value)
                    if s is None:
                        self.unverified(page, label, value, pk, sid, tr, 'the source could not be read')
                    else:
                        self.fresh(page, label, s, pk, freq, value, tr,
                                   need_lag=(lambda d: madd(d[:7], -12) + '-01') if tr == 'yoy' else None)
                        exp, why = self.recompute(tr, [sid], pk, self.build_day)
                        self.compare(page, label, pn[0] if pn else None, exp, pn[1] if pn else 0, sid, pk, tr, why or '')
                        if tr == 'mean13':
                            lw = re.search(r'the latest week (-?[\d.]+)', htmlmod.unescape(rest))
                            if lw:
                                e2, w2 = self.recompute('level', [sid], pk, self.build_day); p2 = parse_num(lw.group(1))
                                self.compare(page, label + ': latest week', p2[0], e2, p2[1], sid, pk, 'level', w2 or '')
                        self.remember(page, label, sid, value, pk)
                elif re.match(r'^-?[\d,.]+$', value.strip()) and len(idl) == 1 and idl[0].isalnum() and tool in ('disturbance',):
                    sid = idl[0].upper(); s = self.S(sid); pk = self.norm_period(s, through, freq); pn = parse_num(value)
                    if s is None: self.unverified(page, label, value, pk, sid, 'level', 'the source could not be read')
                    else:
                        self.fresh(page, label, s, pk, freq, value, 'level')
                        exp, why = self.recompute('level', [sid], pk, self.build_day)
                        self.compare(page, label, pn[0] if pn else None, exp, pn[1] if pn else 0, sid, pk, 'level', why or '')
                        self.remember(page, label, sid, value, pk)
                else:
                    # a derived reading or a file: the period is checked against its inputs; the value is listed as not source-checked
                    if re.search(r'\bmissing\b|\bnan\b|\bnone\b|\bnull\b|\bundefined\b', value or '', re.I):
                        self.R.add(page, label, 'value', 'FAIL', value, through, ids, None, None,
                                   'the page shows "%s" where the value it holds should be' % value)
                    elif value and not re.match(r'^\d+ files?$', value):
                        self.R.add(page, label, 'value', 'WARN', value, through, ids, 'derived', None,
                                   'a derived value with no recipe here: not recomputed (listed as remaining risk)')
                    self.row_fresh(page, label, reps, through, freq, value)
            elif reps:
                # the row's own 'through' = the newest of its values
                pass
            self.next_check(page, label, nxt, self.row_sids(reps, idl), through)
            # the release calendar the build wrote must agree with the row
            c = cal.get((tool, name))
            if c and c.get('next_ny') and nxt and c['next_ny'][:10] != nxt and not reps:
                self.R.add(page, label, 'next published', 'FAIL', nxt, None, None, None, c['next_ny'][:10],
                           'the row says %s; the release calendar says %s' % (nxt, c['next_ny'][:10]))

    def row_sids(self, reps, idl):
        return reps[:1] if reps else []

    def row_fresh(self, page, label, reps, through, freq, value):
        if not reps:
            self.R.add(page, label, 'freshness', 'WARN', value, through, None, None, None,
                       'no series id on the row: its period cannot be checked against a publisher (listed as remaining risk)')
            return
        got = []
        for x in reps:
            m = re.search(r'(ICLAIMS|CCLAIMS|INSUREDUR)$', x)
            if m:     # the State weekly claims: the publisher is the DOL ETA 539 file (FRED posts it a week later)
                s = self.dol_series('US*', 'ic' if m.group(1) == 'ICLAIMS' else 'cc') or self.S(x, '2025-01-01')
            else:
                s = self.S(x, '2025-01-01')
            got.append((x, s))
        live = [(x, s) for x, s in got if s is not None and s.dates]
        if not live:
            return self.unverified(page, label, value, through, ','.join(reps), 'file', 'none of %s could be read' % ','.join(reps), 'freshness')
        # the row's period in each series' own terms; a monthly row built from a weekly series may trail the newest week by a month
        src_weekly = any((len(s.dates) > 1 and (D(s.dates[-1]) - D(s.dates[-2])).days == 7) or s.sid.startswith('DOL539') for _, s in live)
        best = max(live, key=lambda xs: xs[1].newest)
        x, s = best
        if freq == 'monthly' and src_weekly:
            last_full = mkey((D(s.newest) - dt.timedelta(days=6)).isoformat())
            if through[:7] < madd(last_full, -1):
                self.R.add(page, label, 'freshness', 'FAIL', value, through[:7], x, 'monthly from weekly', last_full,
                           'stale: monthly through %s but the weekly source runs to %s' % (through[:7], s.newest))
            elif through[:7] > mkey(s.newest):
                self.R.add(page, label, 'freshness', 'FAIL', value, through[:7], x, 'monthly from weekly', last_full, 'after the newest week: phantom')
            else:
                self.R.add(page, label, 'freshness', 'PASS', value, through[:7], x, 'monthly from weekly', last_full)
            return
        pk = self.norm_period(s, through, freq)
        if freq == 'weekly' and not src_weekly:
            pk = through
        if freq == 'quarterly' and s.newest and pk and len(pk) == 10:
            m = int(pk[5:7]); pk = '%s-%02d-01' % (pk[:4], (m - 1) // 3 * 3 + 1)
        self.fresh(page, label, s, pk, freq, value, 'file')

    def gdpnow(self, page, label, vtxt, through, s):
        if s is None: return self.unverified(page, label + ': GDPNOW', vtxt, through, 'GDPNOW', 'nowcast', 'the source could not be read')
        q = s.newest; rows = [r for r in s.rows if r[0] == q and r[2] == '9999-12-31']
        upd = rows[0][1] if rows and rows[0][1] else None
        pn = parse_num(vtxt)
        self.compare(page, label + ': GDPNOW', pn[0] if pn else None, s.on(self.build_day).get(q), pn[1] if pn else 0, 'GDPNOW', q, 'level (newest update)')
        if upd and through[:10] != upd:
            st = 'WARN' if upd >= self.build_day else 'FAIL'
            self.R.add(page, label + ': GDPNOW', 'freshness', st, vtxt, through[:10], 'GDPNOW', 'update day', upd,
                       'shows the update of %s; the newest update is %s' % (through[:10], upd))
        else:
            self.R.add(page, label + ': GDPNOW', 'freshness', 'PASS', vtxt, through[:10], 'GDPNOW', 'update day', upd)
        self.remember(page, label + ': GDPNOW', 'GDPNOW', vtxt, through[:10])

    def calendar_rows(self):
        t = self.read('ops/release_calendar.json')
        out = {}
        try:
            for r in json.loads(t)['rows']:
                out[((r.get('link') or '').strip('/'), r.get('name'))] = r
        except Exception:
            pass
        return out

    # ---- the detector
    def detector_state(self):
        if hasattr(self, '_S'): return self._S
        t = self.read('detector/index.html'); S = None
        if t:
            i = t.find('const S = ')
            if i >= 0:
                try: S, _ = json.JSONDecoder().raw_decode(t[i + 10:])
                except Exception: S = None
        if S is None:
            j = self.read('bhs_state.json')
            S = json.loads(j) if j else None
        self._S = S
        if S and S.get('built_at'): self.build_day = S['built_at'][:10]
        return S

    READINGS = [  # (start of the reading's text, series, period kind, transform or None, the lag the transformation needs)
        ('route: insured unemployment (not seasonally adjusted, 4-week sum)', 'CCNSA', 'week', None, 55),
        ('route: job openings (JOLTS)', 'JTSJOL', 'month', None, 12),
        ('route: S&P 500 against its close 365 days', 'SP500', 'day', 'sp_yoy', None),
        ('route: industrial production', 'INDPRO', 'month', 'vs_high12_pct', 12),
        ("route: Moody's Baa yield", 'BAA', 'month', 'vs_low12', 12),
        ('route: unemployment rate, the two-month average', 'UNRATE', 'month', None, 3),
        ('route: payrolls, the newest print', 'PAYEMS', 'month', 'vs_high12', 12),
        ("count door: the unemployed count's first print", 'UNEMPLOY', 'month', None, 12),
        ('count door: initial or insured claims', 'ICSA', 'week', None, None),
        ('fed-shock door', 'FEDFUNDS', 'month', 'diff1', 1),
        ('job-losers door: unemployed job losers', 'LNS13023621', 'month', None, 12),
        ("job-losers door's witness", 'GS10', 'month', 'spread:GS1', None),
        ('E22 leg A: insured unemployment', 'CCSA', 'week', None, 3),
        ('E22 legs A and S: the federal funds rate', 'FEDFUNDS', 'month', 'diff12', 12),
        ('E22 leg S: the S&P 500', 'SP500', 'day', None, None),
    ]

    def detector(self):
        S = self.detector_state()
        if not S: self.R.add('detector', 'state', 'inventory', 'FAIL', detail='no detector state on the page'); return
        bd = self.build_day
        # consistency of the public JSON with the page
        j = self.read('bhs_state.json')
        if j:
            B = json.loads(j)
            for k in ('built_at', 'readings', 'feeds', 'feed_value_dates', 'through', 'standing'):
                if json.dumps(B.get(k), sort_keys=True) != json.dumps(S.get(k), sort_keys=True):
                    self.R.add('detector', 'bhs_state.json: ' + k, 'consistency', 'FAIL', detail='the public JSON differs from the page')
        # the readings
        for r in S.get('readings') or []:
            obj = r.get('object', ''); lab = obj.split(',')[0][:90]
            spec = next((x for x in self.READINGS if obj.startswith(x[0])), None)
            if not spec:
                self.R.add('detector', lab, 'inventory', 'WARN', r.get('reading'), r.get('through'), detail='a reading with no source mapping: not checked'); continue
            _, sid, kind, tr, lag = spec
            s = self.S(sid)
            th = r.get('through') or ''
            pk = th[:10] if kind in ('week', 'day') else th[:7] + '-01'
            if s is None:
                self.unverified('detector', lab, r.get('reading'), pk, sid, tr, 'the source could not be read'); continue
            need = None
            if lag and kind == 'month': need = (lambda L: (lambda d: madd(d[:7], -L) + '-01'))(lag)
            if lag and kind == 'week': need = (lambda L: (lambda d: (D(d) - dt.timedelta(weeks=L)).isoformat()))(lag)
            self.fresh('detector', lab, s, pk, kind, r.get('reading'), tr or 'reading', need)
            if tr and r.get('reading') is not None:
                dec = len(repr(float(r['reading'])).split('.')[1]) if '.' in repr(float(r['reading'])) else 0
                tol = 0.5 * 10 ** (-max(dec, 0)) + 1e-9
                if tr.startswith('spread:'):
                    exp, why = self.recompute('spread', [sid, tr.split(':')[1]], pk, bd)
                else:
                    exp, why = self.recompute(tr, [sid], pk, bd)
                self.compare('detector', lab, float(r['reading']), exp, tol, sid, pk, tr, why or '')
            elif r.get('reading') is not None:
                self.R.add('detector', lab, 'value', 'WARN', r.get('reading'), pk, sid, 'derived', None,
                           'first-print reading with no recipe here: its period is checked, its value is not recomputed')
            self.remember('detector', lab, sid, r.get('reading'), pk)
            nk = r.get('next')
            if nk and re.match(r'\d{4}-', nk):
                self.next_check('detector', lab + ' (next)', nk, [sid], pk)
        # the feed values the detector reads (first prints of the NSA claims)
        for sid, f in (S.get('feed_value_dates') or {}).items():
            s = self.S(sid)
            if s is None: self.unverified('detector', 'feed ' + sid, f.get('value'), f.get('date'), sid, 'first print', 'the source could not be read'); continue
            self.fresh('detector', 'feed ' + sid, s, f.get('date'), 'weekly', f.get('value'), 'first print')
            rel = f.get('released') or bd
            exp = s.on(rel).get(f.get('date'))
            self.compare('detector', 'feed ' + sid, f.get('value'), exp, 0.5, sid, f.get('date'), 'first print (the vintage of %s)' % rel)
            self.remember('detector', 'feed ' + sid, sid, f.get('value'), f.get('date'))
        # the dates the detector says it is current through
        TH = {'claims': 'ICSA', 'insured_rate': 'IURSA', 'unemployment_rate': 'UNRATE', 'vacancy': 'JTSJOL', 'sp500': 'SP500'}
        for k, v in (S.get('through') or {}).items():
            if k in TH:
                s = self.S(TH[k]); pk = v if TH[k] in ('ICSA', 'IURSA', 'SP500') else v[:7] + '-01'
                self.fresh('detector', 'current through: ' + k, s, pk, '', v, 'through')
            elif isinstance(v, str):
                self.R.add('detector', 'current through: ' + k, 'freshness', 'WARN', v, detail='no publisher series to check it against (listed)')
        # the daily reading: nothing after the build day, nothing older than its cadence
        ser = S.get('series') or {}
        if ser.get('dates'):
            last = ser['dates'][-1]
            st = 'FAIL' if last > bd else 'PASS'
            self.R.add('detector', 'reading series: last day', 'phantom', st, ser['values'][-1], last, 'BHRREALTIME', None, bd,
                       'a point after the build day' if st == 'FAIL' else '')
            gap = (D(bd) - D(last)).days
            self.R.add('detector', 'reading series: last day', 'cadence', 'FAIL' if gap > 4 else 'PASS', ser['values'][-1], last,
                       detail='the daily reading has not moved for %d days' % gap if gap > 4 else '')
        sm = S.get('series_monthly') or {}
        if sm.get('dates'):
            self.R.add('detector', 'monthly series: last month', 'phantom', 'FAIL' if sm['dates'][-1] > bd[:7] else 'PASS', None, sm['dates'][-1])
        # the feeds (the data page's detector rows are built from them): same numbers both places
        dp = self.read('data/index.html') or ''
        for f in S.get('feeds') or []:
            if f.get('value') and f.get('value') not in htmlmod.unescape(dp):
                self.R.add('detector', 'feed: ' + f.get('name', '')[:60], 'consistency', 'FAIL', f.get('value'),
                           detail='the detector shows a value the data page does not')
            if f.get('next') and re.match(r'\d{4}-', f['next']):
                ids = [x.strip() for x in (f.get('ids') or '').split(',') if x.strip()]
                self.next_check('detector', 'feed: ' + f.get('name', '')[:60] + ' (next)', f['next'], ids[:1],
                                (f.get('through') or '') + ('-01' if len(f.get('through') or '') == 7 else ''))

    # ---- /state-onset/
    def state_onset(self):
        t = self.read('state-onset/index.html')
        if t is None: return
        i = t.find('const ALL = ')
        if i < 0: self.R.add('state-onset', 'data', 'inventory', 'FAIL', detail='no state data on the page'); return
        ALL, _ = json.JSONDecoder().raw_decode(t[i + 12:])
        for st, a in sorted(ALL.items()):
            ur = self.S(st + 'UR', '2025-01-01')
            ser = a.get('series') or {}
            dates = ser.get('dates') or []
            last = dates[-1] if dates else None
            lab = '%s chronology: last month' % st
            if ur is None or not ur.dates:
                self.unverified('state-onset', lab, last, last, st + 'UR', 'month', 'the source could not be read', 'freshness')
            else:
                newest = mkey(ur.newest)
                if last and last > newest:
                    self.R.add('state-onset', lab, 'phantom', 'FAIL', last, last, st + 'UR', None, newest,
                               'a point for %s but the newest State unemployment rate is %s: carried forward' % (last, newest))
                else:
                    self.fresh('state-onset', lab, ur, (last or '') + '-01', 'monthly', last, 'month')
                for k, v in (('now.last_month', (a.get('now') or {}).get('last_month')), ('dg.rt', (a.get('dg') or {}).get('rt')),
                             ('sahm: last month', ((a.get('sahm') or {}).get('dates') or [None])[-1])):
                    if v and v > newest:
                        self.R.add('state-onset', '%s %s' % (st, k), 'phantom', 'FAIL', v, v, st + 'UR', None, newest, 'after the newest published month')
                    elif v and last and v != last and k == 'now.last_month':
                        self.R.add('state-onset', '%s %s' % (st, k), 'carried forward', 'FAIL', v, v, None, None, last, 'the label is not the chart\'s last month')
            self.remember('state-onset', lab, st + 'UR', last, last)
            c = (a.get('through') or {}).get('claims')
            if c:
                ic = self.dol_series(st, 'ic') or self.S(st + 'ICLAIMS', '2026-01-01')
                self.fresh('state-onset', '%s claims through' % st, ic, c, 'weekly', c, 'week')
            # a provisional point must say so
            if ser.get('provisional') is True and not re.search(r'provisional', t[:i] + t[i + 12:], re.I):
                self.R.add('state-onset', st, 'estimate', 'FAIL', detail='a provisional point the page does not label')

    # ---- /stress-map/
    def stress_map(self):
        t = self.read('stress-map/index.html')
        if t is None: return
        m = re.search(r'<script[^>]*id="data"[^>]*>(.*?)</script>', t, re.S)
        if not m: self.R.add('stress-map', 'data', 'inventory', 'FAIL', detail='no map data on the page'); return
        J = json.loads(m.group(1)); V = J.get('v2') or {}; PV = J.get('prov') or {}; thru = V.get('thru') or {}
        # the newest State month (every State's own unemployment rate) and the newest State claims week
        urs = {st: self.S(st + 'UR', '2025-01-01') for st in STATES}
        ics = {st: (self.dol_series(st, 'ic') or self.S(st + 'ICLAIMS', '2026-01-01')) for st in STATES}
        um = [mkey(s.newest) for s in urs.values() if s and s.dates]
        iw = {st: s.newest for st, s in ics.items() if s and s.dates}
        if um:
            nm = max(um)
            for k, v in (('thru.state', thru.get('state')), ('last_v4', J.get('last_v4')), ('prov.v4_last', PV.get('v4_last'))):
                if not v: continue
                st = 'PASS' if v == nm else ('FAIL' if v > nm else 'FAIL')
                self.R.add('stress-map', k, 'freshness' if v < nm else 'phantom' if v > nm else 'freshness', st, v, v, 'xxUR', 'month', nm,
                           '' if st == 'PASS' else ('stale: the States have %s' % nm if v < nm else 'after the newest State month %s' % nm))
                self.remember('stress-map', k, 'xxUR', v, v)
        else:
            self.unverified('stress-map', 'thru.state', thru.get('state'), thru.get('state'), 'xxUR', 'month', 'no State rate could be read', 'freshness')
        if iw:
            nw = max(iw.values())
            wt = PV.get('weeks_through')
            if wt:
                st = 'PASS' if wt == nw else 'FAIL'
                self.R.add('stress-map', 'provisional weeks through', 'freshness', st, wt, wt, 'xxICLAIMS', 'week', nw,
                           '' if st == 'PASS' else ('stale' if wt < nw else 'after the newest week: phantom'))
                if PV.get('last') and PV['last'] > mkey(wt):
                    self.R.add('stress-map', 'provisional last month', 'phantom', 'FAIL', PV['last'], PV['last'], None, None, mkey(wt),
                               'a provisional month after the newest week')
                else:
                    self.R.add('stress-map', 'provisional last month', 'phantom', 'PASS', PV.get('last'), PV.get('last'), None, None, mkey(wt))
                if J.get('last') and J['last'] > max(PV.get('last') or '', thru.get('state') or ''):
                    self.R.add('stress-map', 'last month', 'phantom', 'FAIL', J['last'], J['last'], detail='after every input')
                else:
                    self.R.add('stress-map', 'last month', 'phantom', 'PASS', J.get('last'), J.get('last'))
            for st, c in sorted((PV.get('carried') or {}).items()):
                own = iw.get(st)
                if own is None:
                    self.unverified('stress-map', 'carried ' + st, c.get('week'), c.get('week'), st + 'ICLAIMS', 'week', 'the source could not be read')
                elif c.get('week') != own:
                    self.R.add('stress-map', 'carried ' + st, 'carried forward', 'FAIL', c.get('week'), c.get('week'), st + 'ICLAIMS', 'week', own,
                               'carries the week of %s but the State has published %s' % (c.get('week'), own))
                else:
                    self.R.add('stress-map', 'carried ' + st, 'carried forward', 'PASS', c.get('week'), c.get('week'), st + 'ICLAIMS', 'week', own,
                               'labelled on the page (Amendment 4): the State\'s newest published week')
        # national payrolls by industry, State payrolls by industry
        p = self.S('PAYEMS')
        if p and thru.get('ind_nat'):
            self.fresh('stress-map', 'thru.ind_nat', p, thru['ind_nat'] + '-01', 'monthly', thru['ind_nat'], 'month')
        na = [self.S(x + 'NA', '2025-01-01') for x in ('AL', 'CA', 'WY')]
        na = [s for s in na if s and s.dates]
        if na and thru.get('ind_st'):
            s = max(na, key=lambda s: s.newest)
            self.fresh('stress-map', 'thru.ind_st', s, thru['ind_st'] + '-01', 'monthly', thru['ind_st'], 'month')
        # county unemployment (BLS LAUS; Los Angeles County as the probe) and county jobs (QCEW)
        if thru.get('county_laus'):
            j = self.src.bls(['LAUCN060370000000003'], self.now.year - 1)
            if j and j.get('LAUCN060370000000003'):
                nm = max(j['LAUCN060370000000003'])
                v = thru['county_laus']
                self.R.add('stress-map', 'thru.county_laus', 'freshness', 'PASS' if v == nm else 'FAIL', v, v, 'LAUCN060370000000003', 'month', nm,
                           '' if v == nm else ('stale' if v < nm else 'after the newest county month'))
            else:
                self.unverified('stress-map', 'thru.county_laus', thru['county_laus'], thru['county_laus'], 'BLS LAUS county', 'month', 'the BLS API could not be read', 'freshness')
        cq = V.get('cqlast') or thru.get('county_qcew')
        if cq:
            y, mo = int(cq[:4]), int(cq[5:7]); q = (mo - 1) // 3 + 1
            ny, nq = (y, q + 1) if q < 4 else (y + 1, 1)
            has = self.src.qcew_has(ny, nq)
            if has is True:
                self.R.add('stress-map', 'county jobs (QCEW) through', 'freshness', 'FAIL', cq, cq, 'QCEW', 'quarter', '%dQ%d' % (ny, nq), 'stale: QCEW has published %dQ%d' % (ny, nq))
            elif has is False:
                self.R.add('stress-map', 'county jobs (QCEW) through', 'freshness', 'PASS', cq, cq, 'QCEW', 'quarter', '%dQ%d not yet published' % (ny, nq))
            else:
                self.unverified('stress-map', 'county jobs (QCEW) through', cq, cq, 'QCEW', 'quarter', 'the QCEW API could not be read', 'freshness')

    # ---- /forecaster/
    def forecaster(self):
        t = self.read('forecaster/state.json')
        if t is None: return
        F = json.loads(t); rd = F.get('readings') or {}; bd = self.build_day
        for k, pair in (('spread_10y_3m', ('GS10', 'TB3MS')), ('spread_10y_1y', ('GS10', 'GS1'))):
            r = rd.get(k)
            if not r: continue
            pk = r['month'] + '-01'
            a, b = self.S(pair[0]), self.S(pair[1])
            if a is None or b is None:
                self.unverified('forecaster', k, r.get('value'), r.get('month'), '-'.join(pair), 'spread', 'the source could not be read'); continue
            both = sorted(set(a.dates) & set(b.dates))
            # a month's mean is known the 1st of the next month: the current month is not complete
            both = [x for x in both if x[:7] < bd[:7]]
            self.fresh_ratio('forecaster', k, pk, both, a, b, r.get('value'))
            exp, why = self.recompute('spread', list(pair), pk, bd)
            self.compare('forecaster', k, r.get('value'), exp, 0.005 + 1e-9, '-'.join(pair), pk, 'GS10 minus %s, monthly' % pair[1], why or '')
            self.remember('forecaster', k, '-'.join(pair), r.get('value'), r.get('month'))
        iu = rd.get('insured_unemployment')
        if iu:
            s = self.S('IURSA')
            self.fresh('forecaster', 'insured unemployment rate', s, iu.get('week'), 'weekly', iu.get('rate'), 'first print')
            if s:
                exp = s.on(iu.get('released') or bd).get(iu.get('week'))
                self.compare('forecaster', 'insured unemployment rate', iu.get('rate'), exp, 0.05 + 1e-9, 'IURSA', iu.get('week'),
                             'first print (the vintage of %s)' % iu.get('released'))
            self.remember('forecaster', 'insured unemployment rate', 'IURSA', iu.get('rate'), iu.get('week'))
        if (rd.get('war_surge') or {}).get('value') is not None:
            self.R.add('forecaster', 'war surge', 'value', 'WARN', rd['war_surge']['value'], detail='a derived defense-spending gap: not recomputed (listed)')


# ------------------------------------------------------------------------------------------------------------------- run
def download_live(base, dest):
    os.makedirs(dest, exist_ok=True)
    for p in LIVE_PAGES:
        url = base.rstrip('/') + '/' + p + '?t=%d' % time.time()
        out = os.path.join(dest, p); os.makedirs(os.path.dirname(out), exist_ok=True)
        for i in range(3):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=60) as r:
                    open(out, 'wb').write(r.read()); break
            except urllib.error.HTTPError as e:
                if e.code == 404: break
                time.sleep(5)
            except Exception:
                time.sleep(5)
    return dest


KEYS = os.path.join(ROOT, 'ops', 'state', 'source_gate_keys.json')


def warm_cache(path, fred_key=''):
    """1052 speed: the FRED sources this run's prefetch read (s2/source_gate.py --prefetch-to, started before the build while the site
    builds). Kept: FRED answers only (observations and release calendars) of series FRED itself says it has NOT updated since the
    prefetch (one fred/series/updates call; if that call fails nothing is kept). Everything else - a failed fetch, the BLS API, the
    G.17 file, the ETA 539 file, QCEW, and every FRED series updated since - is fetched again by the gate, exactly as without it."""
    from zoneinfo import ZoneInfo
    try: c = json.load(open(path))
    except Exception: return None
    at = c.pop('_meta:prefetched_ct', None)
    c = {k: v for k, v in c.items() if (k.startswith('fred:') or k.startswith('rel:')) and not k.endswith(':err') and v is not None}
    if not at or not fred_key: return None
    try:
        st = (dt.datetime.strptime(at, '%Y%m%d%H%M') - dt.timedelta(minutes=5)).strftime('%Y%m%d%H%M')
        q = urllib.parse.urlencode(dict(api_key=fred_key, file_type='json', filter_value='all', start_time=st,
                                        end_time=(dt.datetime.now(ZoneInfo('America/Chicago')) + dt.timedelta(hours=1)).strftime('%Y%m%d%H%M'), limit=1000))
        with urllib.request.urlopen(urllib.request.Request('https://api.stlouisfed.org/fred/series/updates?' + q, headers={'User-Agent': UA}), timeout=40) as r:
            d = json.load(r)
        if 'seriess' not in d or int(d.get('count', 0)) >= 1000: return None
        changed = {x['id'] for x in d['seriess']}
    except Exception:
        return None
    return {k: v for k, v in c.items() if k.split(':')[1] not in changed}


def prefetch(out_path, keys_path=KEYS, workers=3, spacing=0.75, prev=None):
    """1052 speed: fetch, in parallel and politely (one call every `spacing` seconds across all threads: 80 a minute, under FRED's 120
    for the key every job shares; a 429 makes every thread wait). Only FRED sources are fetched: the gate re-reads the rest itself, every source the last gate read, into a cache the gate then starts from (--warm). The
    gate reads the same sources from the same publishers; it only no longer waits for them one by one after the build."""
    from concurrent.futures import ThreadPoolExecutor
    from zoneinfo import ZoneInfo
    keys = [k for k in json.load(open(keys_path)) if k.startswith('fred:') or k.startswith('rel:')]
    src = Sources(os.environ.get('FRED_API_KEY', '').strip(), os.environ.get('BLS_API_KEY', '').strip(), budget_s=600)
    src.spacing = spacing
    # 1052 speed (16 Nov 2026): THE LAST RUN'S SOURCES, KEPT. The answers the previous gate read (its --cache-out, restored from GitHub's
    # cache) are kept only for FRED series FRED itself lists as NOT updated since they were read (one fred/series/updates call, as the
    # gate's --warm does); everything else is fetched now. The stamp written is the time of that check, so the gate's own --warm check
    # covers the whole span from the first read to the gate. No previous cache, or a failed check: everything is fetched, as before.
    t_ct = dt.datetime.now(ZoneInfo('America/Chicago')).strftime('%Y%m%d%H%M')
    kept = warm_cache(prev, src.fred_key) if prev and os.path.exists(prev) else None
    if kept:
        src.c.update(kept); n_kept = len(kept)
    else:
        n_kept = 0
    today = dt.datetime.now(ZoneInfo('America/New_York')).date().isoformat()
    def one(k):
        p = k.split(':')
        try:
            if p[0] == 'fred': src.fred(p[1], p[2])
            elif p[0] == 'rel': src.release_dates(p[1], today)
            elif p[0] == 'bls': src.bls(p[1].split(','), int(p[2]))
            elif p[0] == 'g17': src.g17(p[1])
            elif p[0] == 'dol539': src.dol539()
            elif p[0] == 'qcew': src.qcew_has(int(p[1]), int(p[2]))
        except Exception: pass
    t0 = time.time()   # t_ct (above): FRED's stamps are Central time
    with ThreadPoolExecutor(max_workers=workers) as ex: list(ex.map(one, [k for k in keys if k not in src.c]))
    src.c['_meta:prefetched_ct'] = t_ct
    src.save(out_path)
    print('source gate prefetch: %d of %d sources in %.0fs, %d calls (%d kept from the last run, FRED reporting them unchanged)' % (sum(1 for k in src.c if not k.endswith(':err')) - 1, len(keys), time.time() - t0, src.calls, n_kept))


def run(site, mode='warn', pages=None, sources_in=None, sources_out=None, now=None, out=None, verified_path=None,
        fred_key=None, bls_key=None, quiet=False, write_verified=True, warm=None, cache_out=None):
    t0 = time.time()
    from zoneinfo import ZoneInfo
    t0_ct = (dt.datetime.now(ZoneInfo('America/Chicago')) - dt.timedelta(minutes=1)).strftime('%Y%m%d%H%M')
    fk = fred_key if fred_key is not None else os.environ.get('FRED_API_KEY', '').strip()
    cache = json.load(open(sources_in)) if sources_in and os.path.exists(sources_in) else (warm_cache(warm, fk) if warm else None)
    src = Sources(fk,
                  bls_key if bls_key is not None else os.environ.get('BLS_API_KEY', '').strip(),
                  cache=cache, offline=bool(sources_in))
    now = now or dt.datetime.now(dt.timezone.utc)
    verified_path = verified_path or os.path.join(ROOT, 'ops', 'state', 'source_gate_verified.json')
    try: verified = json.load(open(verified_path))
    except Exception: verified = {}
    R = Report()
    g = Gate(site, src, now, verified, R)
    g.detector_state()     # sets the build day from the built state
    pages = pages or ['home', 'data', 'detector', 'state', 'stress', 'forecaster']
    fns = {'home': g.home, 'data': g.data_page, 'detector': g.detector, 'state': g.state_onset, 'stress': g.stress_map, 'forecaster': g.forecaster}
    for p in pages:
        try:
            fns[p]()
        except Exception as e:      # a gate that crashes on a page holds that page: it never passes silently
            import traceback
            R.add(p, 'the gate itself', 'crash', 'FAIL', detail='%s: %s | %s' % (type(e).__name__, e, traceback.format_exc().splitlines()[-3][:200]))
    if sources_out: src.save(sources_out)
    if cache_out and not sources_in:   # 1052 speed: what this gate read, stamped with its start, for the next run's prefetch (--prev)
        try:
            os.makedirs(os.path.dirname(os.path.abspath(cache_out)), exist_ok=True)
            json.dump(dict({k: v for k, v in src.c.items() if k.startswith('fred:') or k.startswith('rel:')}, **{'_meta:prefetched_ct': t0_ct}), open(cache_out, 'w'))
        except OSError:
            pass
    if not sources_in and write_verified:   # 1052 speed: the sources this gate read, for the next run's prefetch
        try:
            os.makedirs(os.path.dirname(KEYS), exist_ok=True)
            json.dump(sorted(k for k in src.c if not k.endswith(':err')), open(KEYS, 'w'), indent=0)
        except OSError:
            pass
    fails = [r for r in R.rows if r['status'] == 'FAIL']
    warns = [r for r in R.rows if r['status'] == 'WARN']
    unver = [r for r in R.rows if r['status'] == 'UNVERIFIED']
    hold = bool(fails) and mode == 'hold'
    decision = 'HOLD' if hold else ('PASS' if not fails else 'WARN-ONLY (would hold)')
    rep = dict(gate='source gate (s2/source_gate.py, collection 1052)', mode=mode, decision=decision, site=site,
               build_day=g.build_day, checked_at=now.strftime('%Y-%m-%d %H:%M UTC'), seconds=round(time.time() - t0, 1),
               source_calls=src.calls, source_errors=src.errors, counts=R.counts(),
               totals=dict(checks=len(R.rows), figures=len(set((r['page'], r['label']) for r in R.rows)), fail=len(fails),
                           warn=len(warns), unverified=len(unver), passed=sum(1 for r in R.rows if r['status'] == 'PASS')),
               failures=fails, rows=R.rows)
    if out:
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        json.dump(rep, open(out, 'w'), indent=1, default=str)
    # the verified store: a figure is remembered only when nothing failed (a held build is not a verified one)
    if write_verified and not fails and not sources_in:
        bad = {(r['page'], r['label']) for r in R.rows if r['status'] in ('UNVERIFIED',)}
        for k, v, p in g.figures:
            pg, lab = k.split('|')[:2]
            if (pg, lab) not in bad:
                verified[k] = {'value': v, 'period': p, 'verified': now.strftime('%Y-%m-%d %H:%M UTC')}
        try:
            os.makedirs(os.path.dirname(verified_path), exist_ok=True)
            json.dump(verified, open(verified_path, 'w'), indent=1, sort_keys=True, default=str)
        except OSError:
            pass
    if not quiet:
        print('source gate (%s mode): %d checks on %d figures in %.0fs, %d source calls: %d PASS, %d FAIL, %d WARN, %d UNVERIFIED'
              % (mode, rep['totals']['checks'], rep['totals']['figures'], rep['seconds'], src.calls, rep['totals']['passed'],
                 len(fails), len(warns), len(unver)))
        for pg, c in sorted(R.counts().items()):
            print('  %-24s %s' % (pg, ', '.join('%s %d' % kv for kv in sorted(c.items()))))
        for r in fails[:60]:
            print('  FAIL %-22s %-55s %-15s %s' % (r['page'], (r['label'] or '')[:55], r['check'], (r['detail'] or '')[:170]))
        if len(fails) > 60: print('  ... and %d more FAILs (out/source_gate_report.json)' % (len(fails) - 60))
        if src.errors: print('  sources not reached: %s' % ', '.join(sorted(src.errors)[:20]))
        if hold:
            print('HOLD source gate: %d published figure(s) disagree with their source or are stale (first: %s %s - %s). Nothing is '
                  'published; the live site keeps the last good build.' % (len(fails), fails[0]['page'], fails[0]['label'],
                                                                         (fails[0]['detail'] or '')[:120]))
        elif fails:
            print('source gate WARN mode: %d FAIL(s) would hold this build in hold mode; published anyway (report-only).' % len(fails))
        else:
            print('source gate: every checked figure matches its source and is current.')
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--site'); ap.add_argument('--live')
    ap.add_argument('--mode'); ap.add_argument('--pages')
    ap.add_argument('--sources-in'); ap.add_argument('--sources-out')
    ap.add_argument('--now'); ap.add_argument('--out', default=os.path.join(WS, 'out', 'source_gate_report.json'))
    ap.add_argument('--verified'); ap.add_argument('--no-verified-write', action='store_true')
    ap.add_argument('--live-dir', help='where --live keeps the downloaded pages (default: a new temporary folder)')
    ap.add_argument('--prefetch-to', help='1052 speed: fetch every source the last gate read into this file, then stop')
    ap.add_argument('--prev', help='1052 speed: with --prefetch-to, the last gate\'s --cache-out (FRED answers FRED reports unchanged are kept)')
    ap.add_argument('--cache-out', help='1052 speed: write what this gate read (FRED answers, stamped) for the next run\'s prefetch')
    ap.add_argument('--warm', help='1052 speed: start from the sources a --prefetch-to of this run fetched (online: anything missing is fetched)')
    a = ap.parse_args()
    if a.prefetch_to:
        prefetch(a.prefetch_to, prev=a.prev); return
    mode = a.mode
    if not mode:
        try: mode = json.load(open(os.path.join(ROOT, 'ops', 'source_gate.json'))).get('mode', 'warn')
        except Exception: mode = 'hold'      # the setting cannot be read: the safe side
    site = a.site
    if a.live:
        import tempfile
        site = download_live(a.live, a.live_dir or tempfile.mkdtemp(prefix='live_site_'))
    if not site:
        site = os.path.join(ROOT, 'data', '105_bristow_hall_system_2026-09-08', 'site', 'public')
    now = dt.datetime.strptime(a.now, '%Y-%m-%d %H:%M').replace(tzinfo=dt.timezone.utc) if a.now else None
    try:
        rep = run(site, mode, a.pages.split(',') if a.pages else None, a.sources_in, a.sources_out, now, a.out, a.verified,
                  write_verified=not a.no_verified_write and not a.live, warm=a.warm, cache_out=a.cache_out)
    except Exception as e:
        print('HOLD source gate: the gate itself failed (%s: %s); nothing is published' % (type(e).__name__, e) if mode == 'hold'
              else 'source gate (warn mode) crashed: %s: %s' % (type(e).__name__, e))
        sys.exit(10 if mode == 'hold' else 0)
    sys.exit(10 if rep['decision'] == 'HOLD' else 0)


if __name__ == '__main__':
    main()
