"""NEXT PUBLISHED, WITH ITS TIME, FOR EVERY DATA-PAGE ROW (15 November 2026, collection 1052; Anthony 12:34 PT: "EVERY SINGLE NEXT
PUBLISHED ROW NEEDS THE EXACT TIME IT IS NEXT PUBLISHED AND THERE SHOULD BE NO GAPS"). Called by bhs_site.py at every build.
  A publisher's series : the publisher's next release day (FRED's release calendar, ops/cache/fred_release_dates.json, refreshed at
                         every update run; or the publisher's own schedule page, s2/tool_inputs.py CAL) at the publisher's clock
                         (ops/release_times_measured.json: the stated hour, or where none is stated the measured one).
  A history layer      : the next release of the live series it continues in.
  A static file        : the next scheduled live-tools run, which restores and re-checks it.
  A Bristow-Hall layer : the first scheduled run that rebuilds it after the next release of its inputs (live-tools.yml crons, UTC;
                         update.yml at the release slots of site/public/run_slots.json).
upcoming(spec) -> sorted aware datetimes (New York), the first after now first. No AI, nothing typed but the keys."""
import os, re, json, datetime as dt
from zoneinfo import ZoneInfo
ET = ZoneInfo('America/New_York'); UTC = dt.timezone.utc
HERE = os.path.dirname(os.path.abspath(__file__)); COL = os.path.dirname(os.path.dirname(HERE)); REPO = os.path.dirname(os.path.dirname(COL))
def _j(p, d):
    try: return json.load(open(p))
    except Exception: return d
TIMES = (_j(os.path.join(REPO, 'ops', 'release_times_measured.json'), {}) or {}).get('publishers', {})
FRD = _j(os.path.join(REPO, 'ops', 'cache', 'fred_release_dates.json'), {})
SER = _j(os.path.join(REPO, 'ops', 'cache', 'fred_series_release.json'), {})
CALR = {re.sub(r'\s+', ' ', str(r.get('ids', '')).lower()).strip(): r for r in (_j(os.path.join(COL, 'site', 'public', 'ops', 'release_calendar.json'), {}) or {}).get('rows', [])}
SLOTS = (_j(os.path.join(COL, 'site', 'public', 'run_slots.json'), {}) or {}).get('slots', [])
RID_PUB = {50: 'bls_empsit', 10: 'bls_cpi', 192: 'bls_jolts', 112: 'bls_state', 180: 'dol_claims', 53: 'bea', 54: 'bea', 282: 'bea', 110: 'bea',
           13: 'fed_g17', 18: 'fed_h15', 219: 'cfnai', 465: 'dallas_wei', 386: 'gdpnow', 456: 'sahm', 109: 'philly_state', 148: 'census_bps'}
# the tool_inputs keys -> (publisher clock, FRED release whose days it follows or None for the CAL list)
KEY = {'bls_state': ('bls_state', 112), 'bls_cpi': ('bls_cpi', 10), 'bls_metro': ('bls_metro', None), 'bls_qcew': ('bls_qcew', None), 'bea_spi': ('bea', 110),
       'census_bps': ('census_bps', None), 'census_cps': ('census_cps', None), 'eta539': ('eta539', 180), 'fred:109': ('philly_state', 109), 'fred:50': ('bls_empsit', 50)}


def _cron_lines(wf):
    try: return re.findall(r"cron:\s*'([^']+)'", open(os.path.join(REPO, '.github', 'workflows', wf)).read())
    except Exception: return []


def _dows(f):
    out = set()
    for part in f.split(','):
        if part == '*': return set(range(7))
        if '-' in part: a, b = part.split('-'); out |= set(range(int(a), int(b) + 1))
        else: out.add(int(part))
    return out


def cron_times(wf, after, n=6):
    """the next n firings of a workflow's cron lines after `after` (aware), in New York time"""
    res = []
    for ln in _cron_lines(wf):
        mi, hh, _dm, _mo, dw = ln.split()
        ds = _dows(dw); a = after.astimezone(UTC)
        for k in range(0, 15):
            d = (a + dt.timedelta(days=k)).replace(hour=int(hh), minute=int(mi), second=0, microsecond=0)
            if d > a and ((d.weekday() + 1) % 7) in ds: res.append(d.astimezone(ET))
    return sorted(set(res))[:n]


def _at(day, hm):
    y, m, d = map(int, day[:10].split('-')); h, mi = map(int, hm.split(':'))
    return dt.datetime(y, m, d, h, mi, tzinfo=ET)


# 1116i (17 Nov 2026; Anthony: "close the thing still open"): THE G.17 ANNUAL REVISION IS ISSUED AT NOON (the Board's G.17 page: "The monthly releases are issued at 9:15 a.m. The annual revision is issued at noon"). A G.17 day FRED lists that the Board's monthly schedule (ops/cache/agency_calendars.json) does not, in a year that schedule covers, is the annual revision: 12:00, not 9:15.
_AG17 = set(((_j(os.path.join(REPO, 'ops', 'cache', 'agency_calendars.json'), {}) or {}).get('g17') or {}).get('dates') or [])
def _hm(rid, day):
    if rid == 13 and _AG17 and day[:4] in {x[:4] for x in _AG17} and day[:10] not in _AG17: return '12:00'
    return TIMES[RID_PUB[rid]]['hm']


def _days(rid, extra=()):
    return sorted(set(((FRD.get(str(rid)) or {}).get('dates') or []) if rid else []) | set(extra))


def publisher(key, now, cal_days=()):
    """upcoming release times of a tool_inputs key or a publisher key with its days"""
    if key == 'eta5159':                                   # the Department rewrites the file every day at its measured clock
        return [_at((now + dt.timedelta(days=k)).date().isoformat(), TIMES['eta5159']['hm']) for k in range(0, 4)]
    pub, rid = KEY.get(key, (key, None))
    return [_at(d, TIMES[pub]['hm']) for d in _days(rid, cal_days)]


def from_calendar(ids):
    """a detector or disturbance row: its release (or rule) as ops/calendar_build.py resolves its ids; the clock is the publisher's"""
    r = CALR.get(re.sub(r'\s+', ' ', str(ids).lower()).strip())
    if r is None:
        first = re.split(r'[,/ ]+', str(ids).strip())[0].upper()
        rid = (SER.get(first) or {}).get('release_id')
        return [_at(d, _hm(rid, d)) for d in _days(rid)] if rid in RID_PUB else []
    rid = r.get('release_id')
    if rid in RID_PUB:
        return [_at(d, _hm(rid, d)) for d in _days(rid, [t['ny'][:10] for t in r.get('times', []) if not t.get('expected')])]
    src = str(r.get('source', ''))
    if 'rule_day7' in src:   # Baa: FRED posts the month's average the first business day of the next month (measured clock), the days of the H.15 monthly post
        days = [t['ny'][:10] for t in (CALR.get('fedfunds') or {}).get('times', [])]
        return [_at(d, TIMES['fred_baa']['hm']) for d in days]
    return [dt.datetime.strptime(t['ny'], '%Y-%m-%d %H:%M').replace(tzinfo=ET) for t in r.get('times', [])]   # the market close, the H.15 month


def upcoming(spec, now=None, inputs=()):
    """spec: ('pub', key) | ('cal', ids) | ('static',) | ('derived_state',) | ('derived_detector',) | ('inputs', [rids])"""
    now = now or dt.datetime.now(ET); k = spec[0]
    if k == 'pub': ts = publisher(spec[1], now, spec[2] if len(spec) > 2 else ())
    elif k == 'cal': ts = from_calendar(spec[1])
    elif k == 'inputs': ts = sorted(t for rid in spec[1] if rid in RID_PUB for t in [_at(d, _hm(rid, d)) for d in _days(rid)])
    elif k == 'static': ts = cron_times('live-tools.yml', now)
    elif k == 'derived_state':   # the first live-tools run after the next release of any input of the State chain
        nxt = min([t for t in inputs if t > now] or [now]); ts = cron_times('live-tools.yml', nxt)
    elif k == 'derived_detector':  # the detector is rebuilt at the release slots; the stress map's copy at the next live-tools run after
        sl = sorted(dt.datetime.strptime(s['ny'], '%Y-%m-%d %H:%M').replace(tzinfo=ET) for s in SLOTS if s.get('ny'))
        nxt = next((t for t in sl if t > now), now); ts = cron_times('live-tools.yml', nxt)
    else: ts = []
    return sorted(t for t in set(ts) if t > now)


def fmt(t):
    """'Nov 19, 2026, 8:30 AM ET'"""
    return '%s %d, %d, %d:%02d %s ET' % (t.strftime('%b'), t.day, t.year, t.hour % 12 or 12, t.minute, 'AM' if t.hour < 12 else 'PM')
