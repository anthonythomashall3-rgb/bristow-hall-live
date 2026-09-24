"""THE RUN SLOTS - when the live update runs, from the release calendar (v3.60, 21 September 2026, collection 278;
Anthony: "MAKE SURE THAT THERE ARE NO ERRORS IN THE LIVE UPDATING FUNCTION ... AND THAT OUR LIVE UPDATING IS SCHEDULED
ON DATA RELEASE DATES AND TIMES").

The site is updated by a GitHub Actions run (update.yml). GitHub's own scheduler proved unable to start it on time: its
firings came two to four hours late on 18 and 19 September and stopped altogether after 19 September 17:10Z, so the
08:50 run of Monday 21 September never happened. The runs are therefore started from outside, at the release times this
file lists: a Cloudflare Worker (cloud/worker, a Cron Trigger every five minutes), which reads this list from the
published site and starts a run only when a slot has passed since the build the site carries and no run is under way (up
to three times a slot, eight minutes apart); GitHub's own schedule stays on as the second line, and runs only when the
site is behind a slot. Nothing depends on the Mac (Anthony, 21 September 2026). A slot whose build is
already on the site costs nothing.

The slots, New York time, from bhs_schedule.py's release calendar (FRED's calendars for the jobs report, JOLTS, housing
starts and the weekly claims, the federal-holiday moves, the front page's release days, and the G.17 days the activity
opener read from FRED):
    an 8:30 release (weekly claims, the employment report, housing starts, a front-page series)     8:50 and 9:30
    G.17 industrial production, 9:15                                                                 9:30 and 10:50
    JOLTS, 10:00                                                                                     10:20 and 10:50
    the EIA weekly petroleum report, Wednesday 10:30                                                 10:50
    every weekday, midday (the OFR financial stress index; the mortgage survey on Thursday)          12:45
    every weekday, the day's close (the S&P 500 at 4:00, the H.15 at 4:15, the search week at 5:00)  5:05 PM
    Saturday                                                                                         10:05
The second slot of a release catches a publisher, or FRED, posting late. A run takes about three minutes, so a release
is on the site within about fifteen minutes of its slot.

Writes ../site/public/run_slots.json (published with the site): built_at (the build the page carries, New York time),
version, and the slots from three days back (a weekend's missed Saturday slot is still seen on Monday) to three
weeks ahead (New York time, UTC, and what each is for). Never fails the
run: on an error the file is removed, and the dispatchers fall back to their own weekday times (8:50, 9:30, 10:50,
12:45 and 5:05 PM; Saturday 10:05).
    python3 s2/run_slots.py        (from the workspace; run_cloud.sh and bhs_run.sh run it after bhs_site.py)
    python3 s2/run_slots.py --print   the next seven days' slots, readable
"""
import os, sys, json, datetime
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__)); WS = os.path.dirname(HERE)
OUT = os.path.normpath(os.path.join(WS, '..', 'site', 'public', 'run_slots.json'))
STATE = os.path.normpath(os.path.join(WS, '..', 'site', 'public', 'bhs_state.json'))
ET = ZoneInfo('America/New_York')
# the release's own time (bhs_schedule.TIMES) -> the run slots after it, New York time
AFTER = {'08:30': ['08:50', '09:30'], '09:15': ['09:30', '10:50'], '10:00': ['10:20', '10:50'], '10:30': ['10:50'],
         '16:15': ['17:05']}
WEEKDAY = {'12:45': 'midday (the OFR financial stress index; the mortgage survey on Thursday)',
           '17:05': "the day's close (the S&P 500 at 4:00, the H.15 at 4:15, the Treasury statement, the search week at 5:00)"}
SATURDAY = {'10:05': 'the weekend refresh'}
DAYS_BACK, DAYS_AHEAD = 3, 21
FALLBACK = "weekdays 08:50, 09:30, 10:50, 12:45 and 17:05; Saturday 10:05 (New York time)"


def slots(S, today):
    out = {}
    for i in range(-DAYS_BACK, DAYS_AHEAD + 1):
        d = today + datetime.timedelta(days=i)
        for k, exp in S.events(d):
            t = S.TIMES.get(k)
            if k == 'hourly' or t not in AFTER:
                continue
            name = {'claims': 'weekly claims (DOL, 8:30 ET)', 'h15': 'the H.15 week (Federal Reserve, 4:15 PM ET)'}.get(k, S.NAMES.get(k, k))
            if exp:
                name += ' - expected, not yet on the calendar'
            for hm in AFTER[t]:
                out.setdefault((d, hm), []).append(name)
        if d.weekday() < 5:
            for hm, why in WEEKDAY.items():
                out.setdefault((d, hm), []).append(why)
        elif d.weekday() == 5:
            for hm, why in SATURDAY.items():
                out.setdefault((d, hm), []).append(why)
    rows = []
    for (d, hm), why in sorted(out.items()):
        h, m = map(int, hm.split(':'))
        t = datetime.datetime(d.year, d.month, d.day, h, m, tzinfo=ET)
        rows.append(dict(ny=t.strftime('%Y-%m-%d %H:%M'), utc=t.astimezone(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                         why=list(dict.fromkeys(why))))
    return rows


def main():
    os.chdir(WS)                      # bhs_schedule reads its calendars relative to the workspace
    sys.path.insert(0, WS)
    import bhs_schedule as S
    today = datetime.datetime.now(ET).date()
    rows = slots(S, today)
    if '--print' in sys.argv:
        for r in rows:
            if r['ny'][:10] >= today.isoformat() and r['ny'][:10] <= (today + datetime.timedelta(days=7)).isoformat():
                print(r['ny'], ' | '.join(r['why']))
        return
    st = json.load(open(STATE))
    built = st.get('built_at')
    datetime.datetime.strptime(built, '%Y-%m-%d %H:%M')     # the dispatchers compare this string; it must be exact
    doc = dict(built_at=built, version=st.get('version'), zone='America/New_York',
               generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
               rule=('a run is started when a slot has passed since built_at and no run is under way, at most three times for '
                     'one slot, eight minutes apart; the Cloudflare Worker checks every five minutes and GitHub\'s own schedule '
                     'is the second line; nothing depends on the Mac'),
               fallback=FALLBACK, slots=rows)
    tmp = OUT + '.tmp'
    json.dump(doc, open(tmp, 'w'), indent=0); os.replace(tmp, OUT)
    nxt = [r for r in rows if r['ny'] > datetime.datetime.now(ET).strftime('%Y-%m-%d %H:%M')]
    print('run slots: %d from %s to %s; next %s (%s); the page carries the build of %s' % (
        len(rows), rows[0]['ny'], rows[-1]['ny'], nxt[0]['ny'] if nxt else None, '; '.join(nxt[0]['why']) if nxt else '-', built))


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        try:
            if '--print' not in sys.argv and os.path.exists(OUT): os.remove(OUT)
        except Exception:
            pass
        print('run slots: FAILED (%s: %s); run_slots.json removed, the dispatchers use their weekday times' % (type(e).__name__, e))
        sys.exit(0)
