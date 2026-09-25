#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""THE RELEASE CALENDAR AND THE UPDATE SCHEDULE, FOR WHATEVER VERSION OF THE TOOL IS LIVE (ops/; 22 September 2026, 306).

Anthony, 22 September 2026: "WE ARE ALWAYS CORRECT ON THE DAY AND TIME THAT THE NEW DATA COMES ... WE NEED TO ALWAYS KNOW
THE EXACT DAYS AND TIMES OF THE NEXT DATA RELEASES ALWAYS AND EXACTLY ... AND WE NEED UPDATES WHEN THERE IS ACTUALLY A
REQUIREMENT FOR AN UPDATE NOT AT RANDOM TIMES BUT AT SPECIFIC TIMES TO ACTUALLY UPDATE THE SITE".

What was wrong. The data page's "Next published" day was worked out once per build and by the day only, so a release day
that had passed kept showing until the next build. The run schedule (the tool's s2/run_slots.py) still carried slots for
sources the tool stopped reading when the leg tier was retired (v3.57/v3.59): every weekday at 12:45 (the OFR stress
index, the mortgage survey), Wednesday 10:50 (the EIA oil report), Saturday 10:05; a 5:05 PM run on market holidays; JOLTS
days read at 8:50 (JOLTS is out at 10:00); and a second fixed run after every release even when the first had the data.

What this does, after every build:
 1. THE CALENDAR. Every row of the data page and every front-page tile (what the site shows is what must be current): for
    each FRED series among its ids, the FRED release that carries it and that release's scheduled days (the agencies' own
    calendars as FRED lists them; fetched once a day; cached in ops/cache, so an outage costs nothing), with the agency's
    clock time (RELEASE_TIME). Inputs FRED does not schedule follow the rule tool.json names (the S&P 500 close on NYSE
    trading days, the H.15 week, the FOMC's decision days, the Google Trends morning, the ETA 539 month). Every row always
    knows at least its next three releases: past the last day an agency has published, the next ones are projected from
    the same month a year earlier (the same weekday, the same week of the month) and marked "expected", and they turn into
    the agency's own days the day FRED lists them. For each row it keeps the schedule that holds the day the build gave.
 2. WHAT IS STILL DUE. A release whose time has passed but whose row has not moved is "waiting" (ops/state/pending.json):
    it is looked for again 30 and 90 minutes later and then at every scheduled run until it comes; the phone is told.
 3. THE SCHEDULE (site/public/run_slots.json, which the Cloudflare starter follows): one run 20 minutes after each timed
    release (FRED posts within minutes; releases that fall together are one run); one run at 5:05 PM on NYSE trading days
    for the S&P 500 close (and, on the same run, the H.15 week, the FOMC's afternoon, the Google searches); a 9:05 AM run on
    a day a rule-dated month becomes public when nothing else runs that day; the look-agains of step 2; and, only while the
    S&P 500 is near the sudden stop's market line, a 9:05 AM run every day for that day's Google searches (tool.json
    conditional_slots). Nothing else. Slots closer than 15 minutes are one run.
 4. The site gets site/public/ops/release_calendar.json; the data page and the front page roll a passed "next" day forward in
    the reader's browser, with its time (ops/site/next_published.js).
Never fails the run: on any error it says so, and the tool's own slot list stands.

    python3 ops/calendar_build.py            (from the repository root; the workflow runs it after the checks)
    python3 ops/calendar_build.py --print    every row's next releases, readable
    python3 ops/calendar_build.py --slots    the schedule for the next seven days, readable (writes nothing)
"""
import datetime as dt
import html
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo

ET = ZoneInfo('America/New_York')
UTC = dt.timezone.utc
OPS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(OPS)
DEFAULT_TOOL = {'data_page': 'data/105_bristow_hall_system_2026-09-08/site/public/data/index.html',
                'home_page': 'data/105_bristow_hall_system_2026-09-08/site/public/index.html',
                'state': 'data/105_bristow_hall_system_2026-09-08/site/public/bhs_state.json',
                'site_public': 'data/105_bristow_hall_system_2026-09-08/site/public',
                'run_slots': 'data/105_bristow_hall_system_2026-09-08/site/public/run_slots.json'}
try:
    TOOL = dict(DEFAULT_TOOL, **json.load(open(os.path.join(OPS, 'tool.json'))))
except Exception as _e:                      # a broken tool.json must not stop the calendar: the last known paths
    print('calendar: ops/tool.json could not be read (%s); using the built-in paths' % _e)
    TOOL = dict(DEFAULT_TOOL)
CACHE = os.path.join(OPS, 'cache')
SER_CACHE = os.path.join(CACHE, 'fred_series_release.json')
REL_CACHE = os.path.join(CACHE, 'fred_release_dates.json')
PENDING = os.path.join(OPS, 'state', 'pending.json')
HORIZON_DAYS = 400
LAG_MIN = 20            # a release is read 20 minutes after its time
CLOSE_HM = '17:05'      # the market-close run on NYSE trading days
MERGE_MIN = 15          # slots closer than this are one run
MIN_FUTURE = 3          # every row always knows at least its next three releases
RETRY_MIN = (30, 90)    # a release due and not in is looked for again 30 and 90 minutes after it was found missing
SLOT_BACK, SLOT_AHEAD = 3, 21

# The clock time, Eastern, of each FRED release a tool reads. FRED's calendar gives the day; the agency gives the hour.
# Checked 22 September 2026 against the publishers' own pages. A release not in the table keeps its day, without a time.
RELEASE_TIME = {
    10: '08:30',    # Consumer Price Index (BLS)
    13: '09:15',    # G.17 Industrial Production and Capacity Utilization (Federal Reserve Board)
    18: '16:15',    # H.15 Selected Interest Rates (Federal Reserve Board)
    27: '08:30',    # New Residential Construction (Census)
    46: '08:30',    # Producer Price Index (BLS)
    50: '08:30',    # Employment Situation (BLS)
    53: '08:30',    # Gross Domestic Product (BEA)
    54: '08:30',    # Personal Income and Outlays (BEA)
    101: '14:00',   # FOMC Press Release
    112: '10:00',   # State Employment and Unemployment (BLS; the schedule page says 10:00 AM beside every date) - v3.72's state rates
    180: '08:30',   # Unemployment Insurance Weekly Claims Report (Department of Labor)
    192: '10:00',   # Job Openings and Labor Turnover Survey (BLS)
    219: '08:30',   # Chicago Fed National Activity Index ("released at 8:30 a.m. ET on scheduled days")
    456: '09:32',   # Sahm Rule Recession Indicators: a FRED series, posted after the Bureau's 8:30 jobs report - FRED's own clock is
                    # used (fred_clock; 8:58-11:45 AM ET since 2025, median of the last nine 9:32); this is only the fallback
    386: '12:01',   # GDPNow as the tool reads it (FRED GDPNOW, every update a vintage): FRED's clock is used (10:31 AM-12:41 PM ET,
                    # median 12:01, ten updates since 2025: nine archived, one seen live 17 September 2026); the Atlanta Fed publishes no hour. Was 17:05 (the close run) until
                    # 23 September 2026 (358): a time the page showed as "next published" that was ours, not the publisher's
    465: '11:30',   # Weekly Economic Index: the Dallas Fed publishes it "at or shortly after 10:30 a.m. CT" on Thursdays
                    # (11:30 AM ET; audit-0924). Was 11:45 until 25 Sep 2026. FRED posts it about nine minutes later (11:39 both
                    # Thursdays read), so the run reads it after that (ops/tool.json calendar_read_lag_min)
}
NO_SLOT = set()     # a release read at a run the day already has gets no slot of its own (GDPNow had none until 358)
# where a time is not the publisher's own announced hour, the page and the message say whose it is (22 September 2026,
# collection 306; Anthony: "make sure that everything includes a release day and time ... and all the release days and
# times are 100% accurate")
TIME_NOTE = {456: "FRED's posting clock, the median of its last nine posts (the Bureau publishes the jobs report at 8:30)",
             386: "FRED's posting clock, the median of its last nine posts (the Atlanta Fed publishes no hour)"}
RULE_NOTE = {'nyse_close': 'the market close', 'daily_next_morning': 'no published hour; read next morning',
             'month_end_plus_21': "the rule's 21-day lag",
             'fred_every_day': "FRED's daily post, at its measured clock (every day, weekends included)",
             'utc_day_end': "the day's end in UTC, 8 PM ET in summer and 7 PM in winter (the tool reads Google's days in UTC); Google publishes no hour"}
# a slot is made only for a release with a publisher's clock: the S&P close is read at 5:05 PM with the day's searches,
# the ETA 539 month has its own 9:05 rule, and Google publishes no hour
RULE_SLOTS = {'nyse_close': False, 'daily_next_morning': False, 'month_end_plus_21': False, 'h15_week': True, 'fomc': True,
              'h15_daily': True, 'fred_every_day': False, 'utc_day_end': False}
FIRST_IN_MONTH = {27}          # New Residential Construction: the construction report (FRED also lists the sales day)
SHORT = {10: 'CPI', 13: 'industrial production (G.17)', 18: 'H.15 rates', 27: 'housing starts', 50: 'the jobs report', 53: 'GDP (BEA)', 386: 'GDPNow',
         101: 'the FOMC statement', 180: 'weekly claims', 192: 'JOLTS (job openings)', 219: 'the Chicago Fed index',
         456: 'the Sahm rule (FRED)'}
RULE_SHORT = {'h15_week': 'the H.15 week (paper and bill rates)', 'fomc': 'the FOMC statement', 'nyse_close': 'the S&P 500 close',
              'daily_next_morning': 'Google searches', 'month_end_plus_21': 'state breadth (the ETA 539 month)',
              'h15_daily': 'the H.15 rates (daily post)', 'fred_every_day': 'the fed funds target (FRED, daily)',
              'utc_day_end': 'Google searches'}

# FRED'S OWN POSTING CLOCK (23 September 2026, collection 358; Anthony: "MAKE SURE THAT ALL THE NEXT RELEASE DAYS ARE ACCURATE AND
# EVERYTHING THAT HAS TO DO WITH THE DATA IS ACCURATE"). The live tool reads FRED, and FRED posts some releases well after the
# agency publishes them: the Employment Situation at 8:46-9:31 AM ET (median 9:12, twenty releases since January 2025) against the
# Bureau's 8:30, the CPI at 8:39-10:10 AM, the state rates at about 1:10 PM against 10:00, GDPNow at 10:31 AM-12:41 PM. Measured
# from FRED's "Updated" stamps on its own series pages as the Internet Archive captured them (358/code/wayback_updated.py), then
# kept current at each run from the release's representative series (its last_updated, on the release's own days; every day for
# a daily series). Two uses. Where FRED is the publisher the tool reads (its daily target range, the Sahm series, GDPNow), the
# page shows FRED's clock - the median of its last nine posts. And the run that reads a release is timed after FRED's usual post
# (the 75th percentile of the last nine, plus five minutes), with "waiting" dated from then, so a run is not spent before FRED has
# the data (a jobs-report run at 8:50 found nothing on FRED on most release days since January 2025).
FRED_POSTED = os.path.join(OPS, 'state', 'fred_posted.json')
FRED_SERIES = {10: 'CPIAUCSL', 13: 'INDPRO', 18: 'DCPN30', 27: 'HOUST', 50: 'UNRATE', 53: 'GDPC1', 101: 'DFEDTARU', 112: 'CAUR',
               180: 'ICSA', 189: 'SP500', 192: 'JTSJOL', 219: 'CFNAIMA3', 386: 'GDPNOW', 456: 'SAHMREALTIME',
               465: 'WEI'}                        # 366 (24 Sep 2026): the Weekly Economic Index, Thursdays (FRED's stamp 17 Sep: 11:39 ET)
FRED_PUBLISHES = {101, 386, 456}                   # FRED's post is the publication the tool reads: the page shows FRED's clock
                                                   # (the WEI left it 25 Sep 2026: the Dallas Fed publishes it at its own hour)
FRED_READ = {10, 13, 27, 50, 53, 112, 192, 219, 386, 456, 465}   # the tool takes these from FRED (claims: from the Department's PDF)
FRED_DAILY = {18, 101, 189}                   # a post every (business) day
POSTS_KEPT, POSTS_USED = 40, 9


def _mins(hm):
    h, m = map(int, hm[:5].split(':'))
    return 60 * h + m


def fred_clock(rid, q=0.5):
    """FRED's usual posting clock for a release (HH:MM New York): the q-quantile of its first post on each of its last nine
    posting days; None while fewer than three are known"""
    posts = sorted((((jload(FRED_POSTED, {}) or {}).get(str(rid)) or {}).get('posts') or []))
    first = {}
    for p in posts:
        first.setdefault(p[:10], p)                # a day's first post is the release; a later one the same day is a touch
    mins = sorted(_mins(first[d][11:16]) for d in sorted(first)[-POSTS_USED:])
    if len(mins) < 3:
        return None
    v = mins[min(len(mins) - 1, int(round(q * (len(mins) - 1))))]
    return '%02d:%02d' % (v // 60, v % 60)


def observe_fred_posts(allow_fetch, rc, today):
    """each run: for a release due today or yesterday (every daily one), its representative series' last_updated, kept when new
    and on one of the release's own days. Never fails the run."""
    if not allow_fetch:
        return
    doc = jload(FRED_POSTED, {}) or {}
    changed, near = False, {today.isoformat(), (today - dt.timedelta(days=1)).isoformat()}
    for rid, sid in FRED_SERIES.items():
        days_ = set((rc.get(str(rid)) or {}).get('dates') or [])
        if rid not in FRED_DAILY and not (days_ & near):
            continue
        try:
            lu = ((fred('series', series_id=sid).get('seriess') or [{}])[0]).get('last_updated', '')
            t = dt.datetime.strptime(lu[:19], '%Y-%m-%d %H:%M:%S').replace(tzinfo=dt.timezone(dt.timedelta(hours=int(lu[19:22]))))
            et = t.astimezone(ET).strftime('%Y-%m-%d %H:%M')
        except Exception:
            continue
        if rid not in FRED_DAILY and et[:10] not in days_:
            continue                                   # a touch off the release's days is not a release post
        ent = doc.setdefault(str(rid), {'series': sid, 'posts': []})
        if et not in ent['posts']:
            ent['posts'] = sorted(ent['posts'] + [et])[-POSTS_KEPT:]
            changed = True
    if changed:
        doc['_what'] = ('FRED\'s posting clock (New York) per release: its representative series\' last_updated on the release\'s '
                        'own days, seeded 23 September 2026 from FRED\'s archived series pages (358/code/wayback_updated.py) and '
                        'extended at every run by ops/calendar_build.py')
        jsave(FRED_POSTED, doc)


def read_lag(rid, hm):
    """minutes from the agency's hour to FRED's usual post (its 75th percentile), for a release the tool reads from FRED"""
    if rid not in FRED_READ or not hm:
        return 0
    q = fred_clock(rid, 0.75)
    return max(0, _mins(q) - _mins(hm)) if q else 0


def now_et():
    return dt.datetime.now(ET)


def jload(p, default):
    try:
        with open(p) as f:
            return json.load(f)
    except Exception:
        return default


def jsave(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(obj, f, indent=1, sort_keys=True)
    os.replace(tmp, p)


def fred_key():
    k = os.environ.get('FRED_API_KEY', '').strip()
    if k:
        return k
    for rel in (TOOL.get('keys_file') or 'data/onset-detector-new-2026-08-23/live_data/config/local.env',):
        try:
            for line in open(os.path.join(ROOT, rel)):
                if line.startswith('FRED_API_KEY='):
                    return line.split('=', 1)[1].strip().strip('"').strip("'")
        except OSError:
            pass
    return ''


def fred(path, **q):
    key = fred_key()
    if not key:
        raise RuntimeError('no FRED key')
    q.update(api_key=key, file_type='json')
    url = 'https://api.stlouisfed.org/fred/%s?%s' % (path, urllib.parse.urlencode(q))
    last = None
    for i in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'bhr-ops-calendar'})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:  # never print the url: it carries the key
            last = 'HTTP %s' % e.code
            if 400 <= e.code < 500 and e.code != 429:
                break
            time.sleep(2 + 3 * i)
        except Exception as e:
            last = '%s' % type(e).__name__
            time.sleep(2 + 3 * i)
    raise RuntimeError('FRED %s failed (%s)' % (path, last))


# ------------------------------------------------------------------------------------------------ holidays and days
def nth_weekday(y, m, wd, n):
    d = dt.date(y, m, 1)
    d += dt.timedelta(days=(wd - d.weekday()) % 7)
    return d + dt.timedelta(weeks=n - 1)


def last_weekday(y, m, wd):
    d = dt.date(y + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1)
    return d - dt.timedelta(days=(d.weekday() - wd) % 7)


def easter(y):                       # the Anonymous Gregorian algorithm
    a, b, c = y % 19, y // 100, y % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    return dt.date(y, (h + l - 7 * m + 114) // 31, (h + l - 7 * m + 114) % 31 + 1)


def federal_holidays(y):
    def obs(d):
        return d - dt.timedelta(days=1) if d.weekday() == 5 else (d + dt.timedelta(days=1) if d.weekday() == 6 else d)
    fixed = [dt.date(y, 1, 1), dt.date(y, 6, 19), dt.date(y, 7, 4), dt.date(y, 11, 11), dt.date(y, 12, 25), dt.date(y + 1, 1, 1)]
    return {d for d in (obs(x) for x in fixed) if d.year == y} | {nth_weekday(y, 1, 0, 3), nth_weekday(y, 2, 0, 3), last_weekday(y, 5, 0),
                                                                  nth_weekday(y, 9, 0, 1), nth_weekday(y, 10, 0, 2), nth_weekday(y, 11, 3, 4)}


def nyse_holidays(y):
    out = set()
    nyd = dt.date(y, 1, 1)
    if nyd.weekday() == 6:
        out.add(nyd + dt.timedelta(days=1))
    elif nyd.weekday() < 5:
        out.add(nyd)                  # a Saturday New Year's Day is not moved to the Friday (NYSE rule 7.2)
    for d in (dt.date(y, 6, 19), dt.date(y, 7, 4), dt.date(y, 12, 25)):
        out.add(d - dt.timedelta(days=1) if d.weekday() == 5 else (d + dt.timedelta(days=1) if d.weekday() == 6 else d))
    out |= {nth_weekday(y, 1, 0, 3), nth_weekday(y, 2, 0, 3), easter(y) - dt.timedelta(days=2), last_weekday(y, 5, 0),
            nth_weekday(y, 9, 0, 1), nth_weekday(y, 11, 3, 4)}
    return out


def trading_day(d):
    return d.weekday() < 5 and d not in nyse_holidays(d.year)


def business_day(d):
    return d.weekday() < 5 and d not in federal_holidays(d.year)


def at(day, hm):
    h, m = map(int, hm.split(':'))
    return dt.datetime(day.year, day.month, day.day, h, m, tzinfo=ET)


def days(start, n):
    for i in range(n):
        yield start + dt.timedelta(days=i)


# ------------------------------------------------------------------------------------------------------ the rules
ALLOW_FETCH = [True]


def rule_times(rule, today):
    """(list of (aware datetime, expected), time known?, frequency) for the rows FRED does not schedule. Every rule now
    carries its clock: the NYSE close at 4:00 PM, the H.15 week at 4:15 PM, the FOMC statement at 2:00 PM, a day's Google
    searches the next morning, a rule-dated month on the morning it becomes public (RULE_NOTE says whose hour it is)."""
    if rule == 'nyse_close':
        return [(at(d, '16:00'), False) for d in days(today - dt.timedelta(days=7), 120) if trading_day(d)], True, 'daily'
    if rule == 'h15_week':             # the week's rates are complete on the first business day of the next week, 4:15 PM
        out = []
        for d in days(today - dt.timedelta(days=7), HORIZON_DAYS):
            if business_day(d):
                prior = [d - dt.timedelta(days=i) for i in range(1, d.weekday() + 1)]
                if all(not business_day(p) for p in prior):
                    out.append((at(d, '16:15'), False))
        return out, True, 'weekly'
    if rule == 'fomc':
        listed = sorted({dt.date.fromisoformat(x) for x in TOOL.get('fomc_decision_days', []) + agency_dates('fomc', ALLOW_FETCH[0], today)})
        out = [(at(d, '14:00'), False) for d in listed]
        last = max(listed) if listed else today
        while len([t for t, _ in out if t.date() > today]) < MIN_FUTURE:       # past the Board's list: six weeks apart, expected
            last += dt.timedelta(days=42)
            while last.weekday() != 2:
                last += dt.timedelta(days=1)
            out.append((at(last, '14:00'), True))
        return out, True, 'irregular'
    if rule == 'daily_next_morning':   # a day's index is known the next morning
        return [(at(d, '09:00'), False) for d in days(today - dt.timedelta(days=2), 120)], True, 'daily'
    # 23 September 2026 (collection 358; Anthony on DFEDTARU: "THIS IS INACCURATE!!! IT UPDATES DAILY!!!"): three daily sources
    # given their real cadence. FRED posts the target range every day, weekends included, at 8:01 AM ET (51 archived stamps
    # since 2025: 8:01-8:30); an FOMC decision reaches it in the next morning's post (all seven changes since 2024). The Board
    # posts the H.15 every business day at 4:15 PM ET (FRED 4:16), with the prior business day's rates. Google's days, as the
    # tool reads them (tz=0), end at midnight UTC: 8 PM ET in summer, 7 PM in winter.
    if rule == 'fred_every_day':
        hm = fred_clock(101) or '08:01'
        return [(at(d, hm), False) for d in days(today - dt.timedelta(days=2), 120)], True, 'daily'
    if rule == 'h15_daily':
        return [(at(d, '16:15'), False) for d in days(today - dt.timedelta(days=7), 120) if business_day(d)], True, 'daily'
    if rule == 'utc_day_end':
        return [((dt.datetime(d.year, d.month, d.day, tzinfo=UTC) + dt.timedelta(days=1)).astimezone(ET), False)
                for d in days(today - dt.timedelta(days=2), 120)], True, 'daily'
    if rule == 'month_end_plus_21':    # a month is read 21 days after it ends (the tool's own rule), by the 9:05 AM run at the latest
        out, d = [], dt.date(today.year, today.month, 1) - dt.timedelta(days=62)
        for _ in range(16):
            end = dt.date(d.year + (d.month == 12), d.month % 12 + 1, 1) - dt.timedelta(days=1)
            out.append((at(end + dt.timedelta(days=21), '09:05'), False))
            d = end + dt.timedelta(days=1)
        return out, True, 'monthly'
    return [], False, 'irregular'


# ------------------------------------------------------------------------------------------- the agencies' own pages
# Where an agency publishes further ahead than FRED lists, its own page is read too (once a day, cached): on 22 September
# 2026 the Board's G.17 page listed every 2027 date while FRED stopped at 16 December 2026, and the FOMC calendar runs a
# year ahead. BLS's pages refuse scripts; FRED carries BLS's days as soon as BLS publishes them.
AGENCY_CACHE = os.path.join(CACHE, 'agency_calendars.json')
G17_URL = 'https://www.federalreserve.gov/releases/g17/release_dates.htm'
FOMC_URL = 'https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm'
MONTHS = {m: i + 1 for i, m in enumerate(['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
                                          'September', 'October', 'November', 'December'])}
MON3 = {k[:3]: v for k, v in MONTHS.items()}


def fetch_page(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (bhr-ops-calendar)'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode('utf-8', 'replace')


def parse_g17(t):
    txt = html.unescape(re.sub(r'<[^>]+>', ' ', t))
    out = set()
    for d, mon, y in re.findall(r'\b(\d{1,2})-([A-Z][a-z]+)-(\d{4})\b', txt):
        if mon in MONTHS:
            try:
                out.add(dt.date(int(y), MONTHS[mon], int(d)).isoformat())
            except ValueError:
                pass
    return sorted(out)


def parse_fomc(t):
    heads = [(m.start(), int(m.group(1))) for m in re.finditer(r'(\d{4}) FOMC Meetings', t)]
    out = set()
    for m in re.finditer(r'class="[^"]*fomc-meeting__month[^"]*"[^>]*>\s*<strong>([^<]+)</strong>.*?class="[^"]*fomc-meeting__date[^"]*"[^>]*>([^<]+)<', t, re.S):
        yrs = [y for pos, y in heads if pos < m.start()]
        if not yrs:
            continue
        year = max(((pos, y) for pos, y in heads if pos < m.start()))[1]
        mon, day = m.group(1).strip(), m.group(2).strip()
        if '(' in day:
            continue                                  # notation votes and unscheduled meetings are not decision days
        day = day.replace('*', '')
        parts = [x for x in re.split(r'[-/]', day) if x.strip().isdigit()]
        mons = [MON3.get(x.strip()[:3]) for x in mon.split('/')]
        if not parts or not mons or None in mons:
            continue
        last_day, last_mon = int(parts[-1]), mons[-1]
        try:
            out.add(dt.date(year, last_mon, last_day).isoformat())
        except ValueError:
            pass
    return sorted(out)


def agency_dates(kind, allow_fetch, today):
    c = jload(AGENCY_CACHE, {}) or {}
    ent = c.get(kind) or {}
    if allow_fetch and (ent.get('fetched') != today.isoformat() or FORCE[0]):
        try:
            t = fetch_page(G17_URL if kind == 'g17' else FOMC_URL)
            ds = parse_g17(t) if kind == 'g17' else parse_fomc(t)
            if len(ds) >= 8:
                ent = {'fetched': today.isoformat(), 'dates': ds, 'url': G17_URL if kind == 'g17' else FOMC_URL}
                c[kind] = ent
                jsave(AGENCY_CACHE, c)
        except Exception as e:
            print('calendar: the %s page was not read (%s); the cached days stand' % (kind, type(e).__name__))
    return ent.get('dates', [])


# --------------------------------------------------------------------------------------------------- FRED lookups
def release_of(series, cache, allow_fetch):
    ent = cache.get(series)
    if ent:                                  # found or not found, a lookup holds for 30 days
        age = (dt.date.today() - dt.date.fromisoformat(ent.get('fetched', '2000-01-01'))).days
        if age < 30 or not allow_fetch:
            return ent.get('release_id'), ent.get('name', '')
    if not allow_fetch:
        return (ent or {}).get('release_id'), (ent or {}).get('name', '')
    try:
        j = fred('series/release', series_id=series)
        rel = (j.get('releases') or [None])[0]
        cache[series] = {'release_id': rel['id'] if rel else None, 'name': rel['name'] if rel else '',
                         'fetched': dt.date.today().isoformat()}
    except Exception as e:
        # a 4xx for a series never found is "not a FRED series"; a mapping once found is never dropped by an error
        if 'HTTP 4' in str(e) and not (ent or {}).get('release_id'):
            cache[series] = {'release_id': None, 'name': '', 'fetched': dt.date.today().isoformat(), 'note': 'not a FRED series'}
        return (ent or {}).get('release_id'), (ent or {}).get('name', '')
    return cache[series]['release_id'], cache[series]['name']


FORCE = [False]
# A NEW VERSION OF THE TOOL RE-CHECKS EVERYTHING (22 September 2026, collection 306; Anthony: "EVERYTIME I MENTION A NEW
# VERSION ON THE LIVE SITE ... ALWAYS RECHECK THE DATA SCHEDULES AND MAKE SURE THEYRE ACCURATE AND THE DATA PAGE ... AND
# OUR LIVE UPDATER"). A port can add a row, rename one, move a link or change what the page shows, so the run that
# publishes a new version asks every agency calendar again and checks every link again, whatever was cached today.
VERSION_CHANGED = [None]
LAST_VERSION = os.path.join(CACHE, 'last_version.json')
GLITCH = []          # releases whose FRED answer looked wrong this run (reported in the message)      # a release is overdue: every calendar is asked again at this run (a postponement shows at once)


def release_dates(rid, cache, allow_fetch, today):
    key = str(rid)
    ent = cache.get(key)
    fresh = ent and ent.get('fetched') == today.isoformat() and ent.get('span', 0) >= 400 and not FORCE[0]
    if allow_fetch and not fresh:
        try:
            j = fred('release/dates', release_id=rid, include_release_dates_with_no_data='true',
                     realtime_start=(today - dt.timedelta(days=430)).isoformat(), realtime_end='9999-12-31',
                     sort_order='asc', limit=1000)
            ds = sorted({x['date'] for x in j.get('release_dates', [])})
            fut_new = [d for d in ds if d > today.isoformat()]
            fut_old = [d for d in (ent or {}).get('dates', []) if d > today.isoformat()]
            sus = (ent or {}).get('suspect') or {}
            if fut_old and len(fut_new) < max(1, len(fut_old) // 2) and not (sus.get('dates') == ds and sus.get('day') != today.isoformat()):
                # an agency moves a day or two; it does not drop half its calendar in one day. Keep what was known until a
                # second fetch on another day gives the same short answer (then it is real: a shutdown's postponements)
                print('calendar: FRED release %s answered %d future days where %d were known; kept the known ones for now' % (rid, len(fut_new), len(fut_old)))
                GLITCH.append('FRED release %s answered a short calendar; the known days were kept' % rid)
                ent = dict(ent, suspect={'dates': ds, 'day': today.isoformat()})
                cache[key] = ent
            else:
                cache[key] = {'fetched': today.isoformat(), 'dates': ds, 'span': 430}
                ent = cache[key]
        except Exception as e:
            print('calendar: FRED release %s not refreshed (%s); the cached days stand' % (rid, e))
    return (ent or {}).get('dates', [])


def project(ds, rid, today, need):
    """(date, expected) days after the last day FRED lists, so the row knows at least `need` future releases.
    Weekly releases: the same weekday a week on, a holiday moving it to the business day before (the claims' Wednesday).
    Monthly releases: the same weekday in the same week of the month as a year earlier, moved off weekends and holidays."""
    if not ds:
        return []
    fut = [d for d in ds if d > today]
    if len(fut) >= need:
        return []
    gaps = sorted((b - a).days for a, b in zip(ds, ds[1:]))
    med = gaps[len(gaps) // 2] if gaps else 30
    out, last = [], ds[-1]
    if med <= 8:                                         # weekly
        d = last
        while len(fut) + len(out) < need:
            d += dt.timedelta(days=7)
            x = d
            while not business_day(x):
                x -= dt.timedelta(days=1)
            out.append((x, True))
        return out
    y, m = last.year, last.month
    recent = ds[-12:]
    wds = [d.weekday() for d in recent]
    modal = max(set(wds), key=wds.count)                 # the agency's usual weekday (Friday for the jobs report)
    while len(fut) + len(out) < need and len(out) < 24:
        y, m = (y + (m == 12), m % 12 + 1)
        prev = [d for d in ds if d.year == y - 1 and d.month == m]
        if prev:
            p = prev[0]
            cands = [nth_weekday(y - 1, m, modal, n) for n in range(1, 6)]
            cands = [c for c in cands if c.month == m]
            nth = min(range(len(cands)), key=lambda i: abs((cands[i] - p).days)) + 1   # the week of the month it fell in
            x = nth_weekday(y, m, modal, nth)
            if x.month != m:
                x = last_weekday(y, m, modal)
        else:
            doms = sorted(d.day for d in ds[-12:])
            x = dt.date(y, m, min(doms[len(doms) // 2], 28))
        while not business_day(x):
            x += dt.timedelta(days=1)
        if x > today:
            out.append((x, True))
    return out


AGENCY_FOR = {13: 'g17'}      # FRED release -> the agency page that lists its days further ahead


def fred_times(rid, dates, today):
    """(list of (aware datetime, expected), time known?, frequency), or None for a daily data series (not a schedule)"""
    ds = [dt.date.fromisoformat(x) for x in dates]
    if rid in AGENCY_FOR:
        ag = [dt.date.fromisoformat(x) for x in agency_dates(AGENCY_FOR[rid], ALLOW_FETCH[0], today)]
        ag = [d for d in ag if d >= today - dt.timedelta(days=430)]
        if ag:
            months = {(d.year, d.month) for d in ag}
            ds = sorted(set(ag) | {d for d in ds if (d.year, d.month) not in months})
    window = [d for d in ds if today - dt.timedelta(days=30) <= d <= today]
    if len(window) > 12:                         # a date every business day: not a release calendar
        return None
    if rid in FIRST_IN_MONTH:
        first = {}
        for d in ds:
            first.setdefault((d.year, d.month), d)
        ds = sorted(first.values())
    hm = RELEASE_TIME.get(rid)
    if rid in FRED_PUBLISHES:                    # FRED is the publisher the tool reads: its own measured clock (358)
        hm = fred_clock(rid) or hm
    gaps = sorted((b - a).days for a, b in zip(ds, ds[1:]))
    med = gaps[len(gaps) // 2] if gaps else 30
    freq = 'weekly' if med <= 8 else ('monthly' if med <= 45 else 'irregular')
    out = [(at(d, hm or '08:30'), False) for d in ds] + [(at(d, hm or '08:30'), True) for d, _ in project(ds, rid, today, MIN_FUTURE)]
    return out, hm is not None, freq, rid not in NO_SLOT, TIME_NOTE.get(rid)


# ------------------------------------------------------------------------------------------------------- the pages
ROW_RE = re.compile(r'<tr\b([^>]*\bdata-ids="[^"]*"[^>]*)>(.*?)</tr>', re.I | re.S)
LINK_RE = re.compile(r'<a [^>]*href="([^"]+)"', re.I)
ATTR_RE = re.compile(r'data-([a-z]+)="([^"]*)"', re.I)


def norm(s):
    return re.sub(r'\s+', ' ', html.unescape(s or '').strip().lower())


def parse_rows(text):
    rows = []
    for m in ROW_RE.finditer(text or ''):
        a = {k.lower(): html.unescape(v) for k, v in ATTR_RE.findall(m.group(1))}
        if a.get('ids'):
            link = LINK_RE.search(m.group(2) or '')
            rows.append({'ids': norm(a['ids']), 'name': a.get('name', ''), 'next': a.get('next', ''),
                         'through': a.get('through', ''), 'value': a.get('value', ''), 'legs': a.get('legs', ''),
                         'link': html.unescape(link.group(1)) if link else ''})
    return rows


def page_rows(path):
    try:
        return parse_rows(open(path, encoding='utf-8').read())
    except OSError:
        return []


def home_rows(path):
    """the front page's tiles: {sid, next} from its inline data"""
    try:
        t = open(path, encoding='utf-8').read()
        m = re.search(r'"tiles":(\[.*?\])\s*[,}]', t, re.S)
        return [{'ids': norm(x.get('sid', '')), 'name': x.get('lab', ''), 'next': x.get('next', ''), 'through': '', 'value': x.get('val', '')}
                for x in json.loads(m.group(1)) if x.get('sid')] if m else []
    except Exception:
        return []


def git_text(rel):
    sha = os.environ.get('OPS_BASE') or os.environ.get('GITHUB_SHA') or 'HEAD'
    try:
        r = subprocess.run(['git', 'show', '%s:%s' % (sha, rel)], cwd=ROOT, capture_output=True, timeout=60)
        return r.stdout.decode('utf-8', 'replace') if r.returncode == 0 else ''
    except Exception:
        return ''


TOKEN_RE = re.compile(r'^[A-Z][A-Z0-9_]{1,29}$')


def tokens(ids):
    raw = re.split(r'[,/;]|\s+', ids.upper())
    return [t for t in (x.strip() for x in raw) if TOKEN_RE.match(t)]


def rule_for(ids):
    rules = {norm(k): v for k, v in (TOOL.get('calendar_rules') or {}).items()}
    if ids in rules:
        return rules[ids]
    for k, v in rules.items():
        if k.endswith('*') and ids.startswith(k[:-1]):
            return v
    return None


def rule_all(rule, today):
    """rule_times plus whether a run is scheduled for it and whose hour it is"""
    tt, known, freq = rule_times(rule, today)
    return tt, known, freq, RULE_SLOTS.get(rule, True), RULE_NOTE.get(rule)


GAPS = []        # anything the site shows without a release day, a time or a link (reported in the message)


def link_gaps(rows, cal_rows, allow_fetch, today, force=False):
    """every row of the data page must link to its source, and a FRED row's link must be that series' page. Reachability
    is checked once a day and only complains about a page that is gone (404/410) or a host that does not resolve: the
    Bureau, the Department and Google answer 403 or 429 to any script, which says nothing about the link."""
    out, to_check = [], []
    cache = jload(os.path.join(CACHE, 'link_check.json'), {}) or {}
    checked = cache.get('day') == today.isoformat() and not force
    bad = dict(cache.get('bad', {}))
    for r in rows:
        url = (r.get('link') or '').strip()
        if not url:
            out.append('%s has no link on the data page' % (r['ids'][:40]))
            continue
        toks = tokens(r['ids'])
        m = re.search(r'fred\.stlouisfed\.org/(?:series|graph)/?\??(?:id=)?([A-Z0-9_^]+)?', url, re.I)
        if m and m.group(1) and toks and m.group(1).upper() not in [x.upper() for x in toks]:
            out.append('%s links to FRED series %s' % (r['ids'][:40], m.group(1)))
        if url.lower().startswith('http'):
            to_check.append((url, r['ids'][:30]))
    if allow_fetch and not checked and to_check:
        def look(job):
            url, ids = job
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (bhr-ops-link-check)'}, method='HEAD')
                with urllib.request.urlopen(req, timeout=12) as rr:
                    rr.read(0)
                return url, None
            except urllib.error.HTTPError as e:
                # 403/429/500 say the host refuses scripts (the Bureau, the Department and Google all do), not that the link is dead
                return url, ('%s (%s)' % (e.code, ids)) if e.code in (404, 410) else None
            except urllib.error.URLError as e:
                return url, ('the address does not resolve (%s)' % ids) if 'Name or service not known' in str(e) else None
            except Exception:
                return url, None
        try:
            import concurrent.futures as _cf
            with _cf.ThreadPoolExecutor(max_workers=8) as ex:
                results = list(ex.map(look, list({u: i for u, i in to_check}.items())))
        except Exception:
            results = []
        for url, why in results:
            if why:
                bad[url] = why
            else:
                bad.pop(url, None)
        if results:
            jsave(os.path.join(CACHE, 'link_check.json'), {'day': today.isoformat(), 'bad': bad})
    out += ['the link for %s is dead: %s' % (v.split('(')[-1].rstrip(')'), k) for k, v in bad.items()]
    return out


def build(allow_fetch=True):
    ALLOW_FETCH[0] = allow_fetch
    today = now_et().date()
    sc, rc = jload(SER_CACHE, {}), jload(REL_CACHE, {})
    rows = page_rows(os.path.join(ROOT, TOOL['data_page'])) + home_rows(os.path.join(ROOT, TOOL.get('home_page', '')))
    seen, out = set(), []
    for r in rows:
        if r['ids'] in seen:
            continue
        seen.add(r['ids'])
        cands = []                                   # (label, [(t, expected)], time_known, release id, freq, slots, note)
        rule = rule_for(r['ids'])
        if rule and rule.startswith('fred:'):
            rid = int(rule.split(':')[1])
            ft = fred_times(rid, release_dates(rid, rc, allow_fetch, today), today)
            if ft:
                cands.append(('FRED release %d' % rid, ft[0], ft[1], rid, ft[2], ft[3], ft[4]))
        elif rule:
            tt, known, freq, slots, note = rule_all(rule, today)
            if tt:
                cands.append(('rule: ' + rule, tt, known, None, freq, slots, note))
        else:
            for tok in tokens(r['ids']):
                rid, rname = release_of(tok, sc, allow_fetch)
                if rid is None:
                    continue
                ft = fred_times(rid, release_dates(rid, rc, allow_fetch, today), today)
                if ft:
                    cands.append(('FRED release %d (%s)' % (rid, rname), ft[0], ft[1], rid, ft[2], ft[3], ft[4]))
        if not cands:
            # NOTHING THE SITE SHOWS MAY BE WITHOUT A RELEASE DAY (22 September 2026, collection 306): a row a new version
            # adds whose inputs FRED does not schedule needs a line in tool.json calendar_rules; until it has one the
            # message says so at every run.
            GAPS.append('%s (%s) has no release calendar - add a rule in ops/tool.json calendar_rules' % (r['ids'][:40], (r.get('name') or '?')[:30]))
            continue
        bn = r.get('next', '')
        pick = [c for c in cands if bn and any(t.date().isoformat() == bn for t, _ in c[1])]
        if not pick:
            nowx = now_et()
            pick = sorted(cands, key=lambda c: min([t for t, _ in c[1] if t > nowx] or [dt.datetime.max.replace(tzinfo=ET)]))[:1]
        label, tt, known, rid, freq, slots, tnote = pick[0]
        lo, hi = now_et() - dt.timedelta(days=10), now_et() + dt.timedelta(days=HORIZON_DAYS)
        seen_t, clean = set(), []
        for t, exp in sorted(tt, key=lambda x: x[0]):
            if lo <= t <= hi and t not in seen_t:
                seen_t.add(t)
                clean.append((t, exp))
        nxt = next(((t, e) for t, e in clean if t > now_et()), None)
        rlag = read_lag(rid, nxt[0].strftime('%H:%M') if nxt else RELEASE_TIME.get(rid)) if rid else 0
        _rl = {norm(k): v for k, v in (TOOL.get('calendar_read_lag_min') or {}).items()}.get(r['ids'])
        if _rl is not None:                          # a row read from a later post than its release (tool.json; 24 Sep 2026)
            rlag = int(_rl)
        short = SHORT.get(rid) or RULE_SHORT.get(label.replace('rule: ', '')) or (r['name'][:40] if r['name'] else r['ids'])
        confirmed = [t for t, e in clean if t > now_et() and not e]
        if not nxt:
            GAPS.append('%s (%s) has no next release day' % (r['ids'][:40], short))
        elif not known:
            GAPS.append('%s (%s) has a release day with no clock time' % (r['ids'][:40], short))
        out.append({'ids': r['ids'], 'name': r['name'], 'source': label, 'release_id': rid, 'time_known': known,
                    'time_note': tnote, 'slots': bool(slots), 'link': r.get('link', ''), 'read_lag_min': rlag,
                    'fred_clock': fred_clock(rid) if rid in FRED_SERIES else None,
                    'freq': freq, 'short': short, 'build_next': bn, 'through': r.get('through', ''),
                    'agrees_with_build': (not bn) or any(t.date().isoformat() == bn for t, _ in clean),
                    'confirmed_through': confirmed[-1].strftime('%Y-%m-%d') if confirmed else None,
                    'times': [{'ny': t.strftime('%Y-%m-%d %H:%M'), 'utc': t.astimezone(UTC).strftime('%Y-%m-%dT%H:%M:%SZ'),
                               'expected': bool(e)} for t, e in clean],
                    'next_ny': nxt[0].strftime('%Y-%m-%d %H:%M') if nxt else None, 'next_expected': bool(nxt and nxt[1])})
    if allow_fetch:
        jsave(SER_CACHE, sc)
        jsave(REL_CACHE, rc)
    try:
        observe_fred_posts(allow_fetch, rc, today)     # FRED's posting clock, kept current (358)
    except Exception as e:
        print('calendar: FRED posting clock not updated (%s)' % type(e).__name__)
    fomc = TOOL.get('fomc_decision_days', [])
    return {'generated_utc': dt.datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ'), 'zone': 'America/New_York',
            'what': ('Every data-page and front-page row: its coming release times, New York and UTC. Days from FRED\'s '
                     'release calendars (the agencies\' own), refreshed daily; hours from the agencies, and FRED\'s own '
                     'measured posting clock where FRED is the publisher the tool reads (fred_clock; read_lag_min is how long '
                     'after the agency\'s hour FRED usually has a release, which times the run that reads it); rows FRED does '
                     'not schedule follow the rule named; past an agency\'s published days, the next ones are projected and '
                     'marked expected. Pages show the first time after the reader\'s clock.'),
            'fomc_list_ends': fomc[-1] if fomc else None, 'rows': out}


# ---------------------------------------------------------------------------------------------- what is still due
WATCHED = ('FRED release', 'rule: h15_week', 'rule: nyse_close')     # not the FOMC row: its data-through moves every day
EXPIRE_DAYS = 7


def pending_update(cal, new_rows, old_rows, prev_built):
    """ops/state/pending.json: releases whose time has passed and whose row has not moved. Returns (pending, came_in)."""
    st = jload(PENDING, {}) or {}
    nowx = now_et()
    last = st.get('last_check_ny') or prev_built or (nowx - dt.timedelta(hours=6)).strftime('%Y-%m-%d %H:%M')
    try:
        last_t = dt.datetime.strptime(last[:16], '%Y-%m-%d %H:%M').replace(tzinfo=ET)
    except Exception:
        last_t = nowx - dt.timedelta(hours=6)
    last_t = max(last_t, nowx - dt.timedelta(days=4))
    thr_new, thr_old = {}, {}
    for rows_, d_ in ((new_rows, thr_new), (old_rows, thr_old)):
        for r in rows_:                          # the data page's rows: the first that carries a through-date (tiles carry none)
            if r.get('through') and r['ids'] not in d_:
                d_[r['ids']] = r['through']
    pend = {(p['ids'], p['due_ny']): p for p in st.get('pending', [])}
    came = []
    for k, p in list(pend.items()):
        cur = thr_new.get(p['ids'])
        if cur is None or cur > p.get('through_before', ''):
            came.append(dict(p, came_in=nowx.strftime('%Y-%m-%d %H:%M'), through_now=cur))
            del pend[k]
    for r in cal['rows']:
        if not r['source'].startswith(WATCHED) or r['ids'] not in thr_new:
            continue
        for x in r['times']:
            if x.get('expected'):
                continue                         # a projected day is not a promise: only the agency's own days are waited for
            t = dt.datetime.strptime(x['ny'], '%Y-%m-%d %H:%M').replace(tzinfo=ET)
            eff = t + dt.timedelta(minutes=15) if r['source'].startswith('rule: nyse_close') else t
            eff += dt.timedelta(minutes=int(r.get('read_lag_min') or 0))   # due on FRED only after FRED's usual post (358)
            if not (last_t < eff <= nowx - dt.timedelta(minutes=5)):
                continue
            before = thr_old.get(r['ids'], thr_new[r['ids']])
            if thr_new[r['ids']] > before:
                came.append({'ids': r['ids'], 'short': r['short'], 'due_ny': x['ny'], 'came_in': nowx.strftime('%Y-%m-%d %H:%M')})
                continue
            key = (r['ids'], x['ny'])
            if key not in pend:
                pend[key] = {'ids': r['ids'], 'short': r['short'], 'due_ny': x['ny'], 'expected_day': x.get('expected', False),
                             'through_before': before, 'since_ny': nowx.strftime('%Y-%m-%d %H:%M')}
    # a release the next one has overtaken is dropped (its row moved on, or a newer one is waited for); an entry older than
    # a week is set aside as expired (said in the message) so an agency's cancelled release cannot be waited for forever
    keep, expired = {}, list(st.get('expired', []))[-20:]
    for (ids, due), p in sorted(pend.items(), key=lambda kv: kv[0][1]):
        try:
            age = (nowx - dt.datetime.strptime(p['due_ny'][:16], '%Y-%m-%d %H:%M').replace(tzinfo=ET)).days
        except Exception:
            age = 0
        if age > EXPIRE_DAYS:
            expired.append(dict(p, expired_ny=nowx.strftime('%Y-%m-%d %H:%M')))
            continue
        keep[ids] = p
    doc = {'last_check_ny': (nowx - dt.timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M'),
           'pending': sorted(keep.values(), key=lambda p: p['due_ny']), 'expired': expired[-20:],
           'came_in': came[-20:],
           'what': 'releases whose time passed without their row moving: looked for again 30 and 90 minutes after they '
                   'were found missing, then at every scheduled run (ops/calendar_build.py)'}
    jsave(PENDING, doc)
    return doc['pending'], came


# ------------------------------------------------------------------------------------------------- the schedule
def conditional_days(state):
    """the tool's conditional slots (tool.json): e.g. while the S&P 500 is near the sudden stop's market line.
    A rule whose reading no longer exists under that name is dead - a new version can rename it - so it is reported."""
    out = []
    for c in TOOL.get('conditional_slots') or []:
        found = False
        for rd in (state or {}).get('readings') or []:
            if c.get('reading_contains', '\0') in str(rd.get('object', '')):
                found = True
                try:
                    ratio = float(rd.get('ratio'))
                except Exception:
                    break
                if ratio >= float(c.get('ratio_at_least', 1)):
                    out.append((c, ratio))
                break
        if not found and (state or {}).get('readings'):
            GAPS.append('the conditional-run rule in ops/tool.json matches no reading any more ("%s") - the version may have '
                        'renamed it; that run is not being scheduled' % (c.get('reading_contains', '')[:60]))
    return out


def schedule(cal, state, pending):
    nowx = now_et()
    lo, hi = nowx - dt.timedelta(days=SLOT_BACK), nowx + dt.timedelta(days=SLOT_AHEAD)
    raw = []                                             # (aware time, why)
    for r in cal['rows']:
        if not r.get('slots', r['time_known']):
            continue
        for x in r['times']:
            t = dt.datetime.strptime(x['ny'], '%Y-%m-%d %H:%M').replace(tzinfo=ET)
            if not (lo - dt.timedelta(hours=2) <= t <= hi):
                continue
            if t.strftime('%H:%M') >= '14:00' and trading_day(t.date()):
                continue                                 # an afternoon release on a trading day: the 5:05 PM run reads it
            lag = int(r.get('read_lag_min') or 0)        # FRED's usual post after the agency's hour (358); 0 where not read from FRED
            run_t = t + dt.timedelta(minutes=max(LAG_MIN, lag + 5))
            if trading_day(t.date()) and run_t.strftime('%H:%M') >= '16:45':
                continue                                 # FRED's usual post comes near the close: the 5:05 PM run reads it
            why = '%s (%s ET%s%s)' % (r['short'], t.strftime('%I:%M %p').lstrip('0'),
                                      ('; FRED by about %s' % (t + dt.timedelta(minutes=lag)).strftime('%I:%M %p').lstrip('0')) if lag > LAG_MIN else '',
                                      ', expected' if x.get('expected') else '')
            raw.append((run_t, why))
    d = lo.date()
    while d <= hi.date():
        if trading_day(d):
            raw.append((at(d, CLOSE_HM), "the S&P 500 close (with the day's H.15 post and the day's other afternoon data)"))
        d += dt.timedelta(days=1)
    # the rule-dated month is read by 9:05 AM on its day, whatever else runs that day (358: the page shows that time, so it
    # must be kept; until 23 September 2026 the run was added only when no other run was due that day, which could leave the
    # month to the 5:05 PM close)
    for r in cal['rows']:
        if r['source'] != 'rule: month_end_plus_21':
            continue
        for x in r['times']:
            t = dt.datetime.strptime(x['ny'], '%Y-%m-%d %H:%M').replace(tzinfo=ET)
            if lo <= t <= hi:
                raw.append((at(t.date(), '09:05'), '%s becomes public (the rule\'s 21-day lag)' % r['short']))
    for c, ratio in conditional_days(state):
        for k in range(0, 4):
            day = nowx.date() + dt.timedelta(days=k)
            for hm in c.get('every_day_at', ['09:05']):
                raw.append((at(day, hm), '%s (the reading stands at %.0f%% of its line)' % (c.get('why', 'a conditional run'), ratio * 100)))
    for p in pending:
        try:
            s0 = dt.datetime.strptime(p['since_ny'][:16], '%Y-%m-%d %H:%M').replace(tzinfo=ET)
        except Exception:
            continue
        for mnt in RETRY_MIN:
            t = s0 + dt.timedelta(minutes=mnt)
            if t > nowx and t.hour < 20:
                raw.append((t, 'look again: %s (due %s, not yet posted)' % (p['short'], p['due_ny'][11:])))
    raw = [(t, w) for t, w in raw if lo <= t <= hi]
    raw.sort(key=lambda x: x[0])
    groups = []                                          # [first time, run time, reasons]
    for t, w in raw:
        t = t.replace(minute=(t.minute // 5) * 5, second=0, microsecond=0)
        if groups and (t - groups[-1][0]).total_seconds() <= MERGE_MIN * 60 and t.date() == groups[-1][0].date():
            groups[-1][1] = max(t, groups[-1][1])            # the run waits for the latest release of its group
            groups[-1][2].append(w)
        else:
            groups.append([t, t, [w]])
    return [{'ny': t.strftime('%Y-%m-%d %H:%M'), 'utc': t.astimezone(UTC).strftime('%Y-%m-%dT%H:%M:%SZ'),
             'why': list(dict.fromkeys(w))} for _, t, w in groups]


def write_slots(slots, state):
    path = os.path.join(ROOT, TOOL['run_slots'])
    old = jload(path, {}) or {}
    doc = {'built_at': (state or {}).get('built_at') or old.get('built_at'), 'version': (state or {}).get('version') or old.get('version'),
           'zone': 'America/New_York',
           'generated_utc': dt.datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ'),
           'rule': ('a run is started when a slot has passed since built_at and no run is under way, at most three times for '
                    'one slot, eight minutes apart; the Cloudflare Worker checks every five minutes and GitHub\'s own schedule '
                    'is the second line; nothing depends on the Mac'),
           'made_by': ('ops/calendar_build.py (22 September 2026): a run 20 minutes after each release the site shows, the S&P '
                       '500 close at 5:05 PM on NYSE trading days, a look-again only for a release that is due and not posted; '
                       'nothing else'),
           'fallback': 'weekdays 08:50, 09:35, 10:20 and 17:05 (New York time), used only if this list cannot be read',
           'slots': slots}
    jsave(path, doc)


def main():
    out_dir = os.path.join(ROOT, TOOL['site_public'], 'ops')
    st = jload(os.path.join(ROOT, TOOL['state']), {}) or {}
    # WHEN THE CALENDAR IS ASKED (22 September 2026; Anthony: "should the release dates system only update when a new point
    # of data has released for that series?"). A new data point does not change a schedule: the next day is already on it.
    # What changes one is an agency's announcement - a holiday move, a shutdown's postponements, next year's calendar - which
    # comes on its own day. So the calendars are asked once a day, at the first run that happens anyway (a dozen look-ups,
    # about two seconds, never a run of its own), and again at every run while a release is overdue, so a postponement is
    # seen the moment it matters.
    prev_v = (jload(LAST_VERSION, {}) or {}).get('version')
    if st.get('version') and prev_v and st['version'] != prev_v:
        VERSION_CHANGED[0] = '%s -> %s' % (prev_v, st['version'])
        print('ops calendar: a new version is live (%s): every release calendar and every link is checked again' % VERSION_CHANGED[0])
    FORCE[0] = bool((jload(PENDING, {}) or {}).get('pending')) or bool(VERSION_CHANGED[0])
    cal = build(allow_fetch='--offline' not in sys.argv)
    cal['tool_version'], cal['built_at'] = st.get('version'), st.get('built_at')
    if '--print' in sys.argv:
        for r in cal['rows']:
            print('%-30s %-26s next %-16s%s build %-10s confirmed to %s %s' % (
                r['ids'][:30], (r['short'] or '')[:26], r['next_ny'], ' (exp)' if r['next_expected'] else '      ',
                r['build_next'], r['confirmed_through'], '' if r['agrees_with_build'] else 'DISAGREES'))
        return
    new_rows = page_rows(os.path.join(ROOT, TOOL['data_page'])) + home_rows(os.path.join(ROOT, TOOL.get('home_page', '')))
    old_rows = parse_rows(git_text(TOOL['data_page']))
    old_state = {}
    try:
        old_state = json.loads(git_text(TOOL['state']) or '{}')
    except Exception:
        pass
    if '--slots' in sys.argv:
        pend = (jload(PENDING, {}) or {}).get('pending', [])
        nowx = now_et()
        for s in schedule(cal, st, pend):
            if nowx.strftime('%Y-%m-%d') <= s['ny'][:10] <= (nowx + dt.timedelta(days=7)).strftime('%Y-%m-%d'):
                print(s['ny'], ' | '.join(s['why']))
        return
    jsave(os.path.join(out_dir, 'release_calendar.json'), cal)
    DISAGREE[:] = ['%s: the tool says %s, the calendar %s' % (r['short'], r['build_next'], (r['next_ny'] or '?')[:10])
                   for r in cal['rows'] if not r['agrees_with_build']]
    fomc_future = [x for x in sorted(set(TOOL.get('fomc_decision_days', []) + agency_dates('fomc', False, now_et().date())))
                   if x > now_et().date().isoformat()]
    if len(fomc_future) < 3:
        GLITCH.append('FOMC calendar: only %d decision days known ahead' % len(fomc_future))
    LINKS[:] = link_gaps(page_rows(os.path.join(ROOT, TOOL['data_page'])), cal['rows'], '--offline' not in sys.argv,
                         now_et().date(), force=bool(VERSION_CHANGED[0]))
    if st.get('version'):
        jsave(LAST_VERSION, {'version': st['version'], 'seen_utc': dt.datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ'),
                             'what': 'the version the last calendar was built for; a change re-checks every calendar and link'})
    pend, came = pending_update(cal, new_rows, old_rows, (old_state or {}).get('built_at'))
    waiting = {p['ids']: p['due_ny'] for p in pend}
    for r in cal['rows']:                        # the pages show "not yet published" for these instead of rolling forward
        r['waiting_since_due'] = waiting.get(r['ids'])
    jsave(os.path.join(out_dir, 'release_calendar.json'), cal)
    slots = schedule(cal, st, pend)
    write_slots(slots, st)
    nowx = now_et().strftime('%Y-%m-%d %H:%M')
    nxt = [s for s in slots if s['ny'] > nowx]
    short = [r['ids'] for r in cal['rows'] if len([x for x in r['times'] if x['ny'] > nowx]) < MIN_FUTURE]
    COUNTS.update(rows=len(cal['rows']), timed=sum(1 for r in cal['rows'] if r['time_known']),
                  linked=sum(1 for r in page_rows(os.path.join(ROOT, TOOL['data_page'])) if (r.get('link') or '').strip()))
    if GAPS:
        print('ops calendar: WHAT THE SITE SHOWS WITHOUT A FULL RELEASE DAY AND TIME: ' + '; '.join(GAPS))
    if LINKS:
        print('ops calendar: links to check: ' + '; '.join(LINKS))
    print('ops calendar: %d rows (%d with clock times); %d waiting%s; schedule of %d runs, next %s (%s)%s' % (
        len(cal['rows']), sum(1 for r in cal['rows'] if r['time_known']), len(pend),
        (' (' + ', '.join('%s due %s' % (p['short'], p['due_ny'][5:]) for p in pend) + ')') if pend else '',
        len(slots), nxt[0]['ny'] if nxt else None, '; '.join(nxt[0]['why'])[:120] if nxt else '-',
        ('; fewer than %d future days for: %s' % (MIN_FUTURE, ', '.join(short))) if short else ''))


DISAGREE = []
LINKS = []
COUNTS = {}


def status(ok, why=''):
    try:
        jsave(os.path.join(OPS, 'out', 'calendar_status.json'), {'ok': ok, 'why': why, 'disagree': DISAGREE[:6], 'glitch': GLITCH[:6],
                                                                'gaps': GAPS[:6], 'links': LINKS[:4], 'version_change': VERSION_CHANGED[0],
                                                                'rows': COUNTS.get('rows'), 'timed': COUNTS.get('timed'), 'linked': COUNTS.get('linked'),
                                                                'utc': dt.datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')})
    except Exception:
        pass


if __name__ == '__main__':
    try:
        main()
        status(True)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print('ops calendar: FAILED (%s: %s); what is published stands (the tool\'s own slot list)' % (type(e).__name__, e))
        status(False, '%s: %s' % (type(e).__name__, str(e)[:200]))
    sys.exit(0)
