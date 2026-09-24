"""THE BRISTOW HALL SYSTEM — the release schedule, and the launchd job that follows it (no one in the loop).

The rule reads five releases. Their timing, Eastern:
  weekly claims (DOL)             Thursdays 8:30 ET; a Wednesday when the Thursday is a federal holiday
  Employment Situation (BLS)      8:30 ET on the dated Fridays
  JOLTS (BLS)                     10:00 ET on the dated days
  New Residential Construction    8:30 ET on the dated days
  H.15 (Federal Reserve)          4:15 PM ET every business day, carrying the PREVIOUS business day's rates; the
                                  rule reads the Friday week, complete on the first business day of the next week
  S&P 500                         4:00 PM ET close; the closer reads it on the claims release day
  the day's close (v3.27)         every weekday 4:20 and 5:00 PM ET: the search week (Google Trends, yesterday's
                                  datum known this morning) is read with today's S&P 500 close, so the sudden stop
                                  can fire on any trading day; a weekday with no close (a market holiday) rebuilds
                                  nothing. These runs are not on the page's release list.
Where the dates come from, in order: cache/claims_release_dates.csv and cache/release_schedule.csv (FRED's release
calendar, fetched by bhs_calendar_fetch.py at the first run of each month, which lists the year ahead as soon as the
agencies publish it; the Census and BLS schedules read by hand on 8 September 2026 are in the same file); beyond
them, the usual timing (Thursdays with the federal-holiday move; the first Friday; five weeks and seventeen days
after the month) marked "expected" until the calendar confirms it.

The Mac runs bhs_run.sh right after each release, with two later attempts in case FRED posts late (a run that finds
nothing new does not rebuild): claims 8:35, 8:50, 9:20 ET; the employment report and housing starts the same;
JOLTS 10:05, 10:20, 10:50 ET; the H.15 week 4:20 and 5:00 PM ET on the first business day of each week; the S&P
close 4:20 and 5:00 PM ET on claims days; and, from v3.27, the day's close 4:20 and 5:00 PM ET on every weekday.
Times are converted to the Mac's local zone when the job is written. launchd cannot carry a year, so dated entries
recur; the runner asks `--why` first and does nothing when no slot has passed since the last completed run. A Mac
asleep at a slot's time misses it; launchd folds every missed slot into one firing on wake, whatever the day or hour,
and `--why` then names the missed slots (cache/last_done, written by bhs_run.sh --mark-done, is the reference), so
the work of every slot is done at the wake. The job runs under caffeinate -s -i so a run begun on a wake finishes.
Only `sudo pmset -a disablesleep 1` (Anthony's to run) makes the slots fire at their own times with the lid closed.

    python3 bhs_schedule.py            print the next 90 days of runs
    python3 bhs_schedule.py --why      print the slots passed since the last completed run, or today's releases (exit 3 if none)
    python3 bhs_schedule.py --mark-done   write cache/last_done (bhs_run.sh does this at the end of every completed run)
    python3 bhs_schedule.py --install  write ~/Library/LaunchAgents/com.bristowhall.system.plist and load it
    python3 bhs_schedule.py --calendar N   print the next N days as JSON (date, time ET, kind, what, expected)
"""
import os, sys, csv, datetime, subprocess, plistlib, json
from zoneinfo import ZoneInfo
HERE=os.path.dirname(os.path.abspath(__file__))
COL=os.path.dirname(HERE)
SCHED=os.path.join(HERE,'cache','release_schedule.csv'); CLAIMS=os.path.join(HERE,'cache','claims_release_dates.csv')
LABEL='com.bristowhall.system'
PLIST=os.path.expanduser('~/Library/LaunchAgents/%s.plist'%LABEL)
RUN=os.path.join(HERE,'bhs_run.sh')
ET=ZoneInfo('America/New_York')

# ---- federal holidays (observed), for the claims move ----
def nth_weekday(y,m,wd,n):
    d=datetime.date(y,m,1); d+=datetime.timedelta(days=(wd-d.weekday())%7); return d+datetime.timedelta(weeks=n-1)
def last_weekday(y,m,wd):
    d=datetime.date(y+(m==12),(m%12)+1,1)-datetime.timedelta(days=1); return d-datetime.timedelta(days=(d.weekday()-wd)%7)
def observed(d):
    if d.weekday()==5: return d-datetime.timedelta(days=1)
    if d.weekday()==6: return d+datetime.timedelta(days=1)
    return d
def federal_holidays(y):
    fixed=[datetime.date(y,1,1),datetime.date(y,6,19),datetime.date(y,7,4),datetime.date(y,11,11),datetime.date(y,12,25)]
    return {observed(d) for d in fixed}|{nth_weekday(y,1,0,3),nth_weekday(y,2,0,3),last_weekday(y,5,0),nth_weekday(y,9,0,1),nth_weekday(y,10,0,2),nth_weekday(y,11,3,4)}
def thanksgiving(y): return nth_weekday(y,11,3,4)

# ---- the calendars on disk ----
def dated():
    rows={}
    if os.path.exists(SCHED):
        for r in csv.DictReader(open(SCHED)):
            try: d=datetime.date.fromisoformat(r['release_date'])
            except Exception: continue
            rows.setdefault(d,set()).add(r['series'])
    return rows
def claims_days():
    out=set()
    if os.path.exists(CLAIMS):
        for r in csv.DictReader(open(CLAIMS)):
            try: out.add(datetime.date.fromisoformat(r['release_date']))
            except Exception: pass
    return out
def dated_through():
    ds=dated(); return max(ds) if ds else None
def claims_through():
    c=claims_days(); return max(c) if c else None

# ---- the usual timing, for dates beyond the calendars ----
def expected_monthly(kind,y,m):
    """the release day for reference month (y,m) when no calendar covers it"""
    ny,nm=(y+(m==12),(m%12)+1)
    if kind=='UNRATE':
        d=nth_weekday(ny,nm,4,1)
        if d in federal_holidays(ny): d-=datetime.timedelta(days=1)
        return d
    mend=datetime.date(ny,nm,1)-datetime.timedelta(days=1)
    d=mend+datetime.timedelta(days=33 if kind=='JTSJOL' else 17)
    while d.weekday()>=5 or d in federal_holidays(d.year): d+=datetime.timedelta(days=1)
    return d

def tiles_days():
    """the days a series the FRONT PAGE shows is published (cache/tiles_release_dates.csv, written by
    s2/home_tiles.py from FRED's own release calendar). CPI is the case that made this necessary: it is not a series
    the rule reads, so no run was scheduled for it and the page waited for the day's close."""
    p=os.path.join('cache','tiles_release_dates.csv'); out=set()
    if not os.path.exists(p): return out
    for line in open(p).read().splitlines()[1:]:
        try: out.add(datetime.date.fromisoformat(line.split(',')[1]))
        except Exception: pass
    return out

NAMES={'tiles':'a series the front page shows (8:30 ET)','UNRATE':'Employment Situation (BLS, 8:30 ET)','JTSJOL':'JOLTS (BLS, 10:00 ET)','HOUST':'housing starts (Census, 8:30 ET)','search':"the day's close: the S&P 500 with the search week (v3.27; 4:00 PM ET)",
       'hourly':'the hourly refresh','eiaw':'the EIA weekly petroleum report (Wednesday 10:30 ET)'}
TIMES={'tiles':'08:30','claims':'08:30','UNRATE':'08:30','HOUST':'08:30','JTSJOL':'10:00','h15':'16:15','search':'16:15','hourly':'hourly','eiaw':'10:30','g17':'09:15'}
WHAT={'claims':'Weekly claims (initial claims, continued claims, insured unemployment rate), Department of Labor',
      'UNRATE':'Employment Situation (unemployment rate, factory hours, nondurable employment), BLS',
      'JTSJOL':'JOLTS (job openings), BLS','HOUST':'Housing starts (New Residential Construction), Census',
      'h15':'H.15 selected interest rates for the week just ended (commercial paper and bill rates), Federal Reserve'}
KIND={'claims':'claims','UNRATE':'jobs','JTSJOL':'jolts','HOUST':'starts','h15':'h15','g17':'production'}
WHAT['g17']='G.17 Industrial Production and Capacity Utilization (industrial production, as the activity opener reads it), Federal Reserve'   # v3.60 (collection 278)
NAMES['g17']='G.17 industrial production (Federal Reserve, 9:15 ET)'
# ask 59 (24 Sep 2026, ops-0924): v3.73 put GDPC1 and GDPNOW on the calendar without release times, and every run of this scheduler
# stopped at KeyError 'GDPNOW'. GDPC1 (BEA, 8:30 ET) gets its time; a series with no set time (GDPNOW posts when the
# Atlanta Fed reruns its model; the hourly refresh reads it) is skipped by the job's slots instead of crashing them.
TIMES['GDPC1']='08:30'; NAMES['GDPC1']='GDP (BEA, 8:30 ET)'
def _g17_days():
    # the release days s2/activity_opener.py read from FRED's calendar (release 13); none when the file is absent
    try:
        import json as _j
        return {datetime.date.fromisoformat(d) for d in _j.load(open(os.path.join(HERE,'out','activity_opener_state.json'))).get('g17_dates',[])}
    except Exception: return set()

def events(day):
    """the releases on a day: list of (series key, expected flag)"""
    out=[]
    cd=claims_days(); ct=claims_through()
    if ct and day<=ct:
        if day in cd: out.append(('claims',False))
    else:
        if day.weekday()==3 and day not in federal_holidays(day.year): out.append(('claims',True))
        if day.weekday()==2 and (day+datetime.timedelta(days=1)) in federal_holidays(day.year): out.append(('claims',True))
    # the H.15 week: the daily H.15 posts each day's rates on the NEXT business day at 4:15 PM ET, so a week's
    # averages are complete on the first business day of the following week (the Monday; the Tuesday after a
    # Monday holiday). Audit of 8 September 2026: the first version ran on the Friday, a day before the data.
    if day.weekday()<5 and day not in federal_holidays(day.year):
        earlier=[day-datetime.timedelta(days=i) for i in range(1,day.weekday()+1)]
        if all(e in federal_holidays(e.year) for e in earlier): out.append(('h15',False))
    ds=dated(); dt=dated_through()
    for s in sorted(ds.get(day,())): out.append((s,False))
    if dt is None or day>dt:
        for kind in ('UNRATE','HOUST','JTSJOL'):
            for back in (1,2,3):
                y,m=day.year,day.month
                for _ in range(back):
                    y,m=(y-(m==1),(m-2)%12+1)
                if expected_monthly(kind,y,m)==day and not any(k==kind for k,_ in out): out.append((kind,True))
    # v3.27 (10 September 2026): the search week is read every day the market closes, at that day's close, so the
    # runner is due at the close on every weekday (a market holiday appends no close and rebuilds nothing)
    if day.weekday()<5: out.append(('search',False))
    # the front page's own series (CPI among them): a run on each of their release days, so the page is current
    # within minutes of the release instead of at the day's close
    if day in tiles_days() and day.weekday()<5: out.append(('tiles',False))
    # 17 September 2026 (Anthony: no delay in the data is acceptable): an hourly refresh every day, 8:03 AM to 6:03 PM ET,
    # for the sources that post on their own clocks - the OFR index at midday, the Treasury statement at 4, the mortgage
    # survey on Thursday noon, the search index each morning, the WARN pages as the states post; a run that finds
    # nothing new does not rebuild
    out.append(('hourly',False))
    # the EIA weekly petroleum report, Wednesday 10:30 ET
    if day.weekday()==2: out.append(('eiaw',False))
    # v3.60 (Core v6): G.17 industrial production, 9:15 ET, on the days FRED's release calendar gives
    if day in _g17_days(): out.append(('g17',False))
    return out

def reasons(day):
    r=[]
    for k,exp in events(day):
        name={'claims':'weekly claims (DOL, 8:30 ET)','h15':'the H.15 week just ended (Federal Reserve, 4:15 PM ET)'}.get(k,NAMES.get(k,k))
        if k=='claims' and day.weekday()!=3: name+=' - moved by a holiday'
        r.append(name+(' (expected; not yet on the calendar)' if exp else ''))
    return r

def calendar(days):
    today=datetime.date.today(); out=[]
    for i in range(days):
        d=today+datetime.timedelta(days=i)
        for k,exp in events(d):
            if k not in WHAT: continue          # the daily close runs are not releases; the page lists releases
            out.append(dict(date=d.isoformat(),time=TIMES[k],kind=KIND[k],what=WHAT[k],expected=exp))
    return out

# ---- the launchd job ----
ATTEMPTS={'08:30':['08:33','08:45','09:20'],'10:00':['10:03','10:15','10:50'],'10:30':['10:33','10:50'],'16:15':['16:18','17:00'],'09:15':['09:18','09:30','10:50'],'close':['16:18','17:00'],
          'hourly':['%02d:03'%h for h in range(8,19)]}   # 17 Sep 2026: first attempt three minutes after the release (was five); the second at +15; hourly 8:03-18:03 ET
def local_hm(day,hm_et):
    h,m=map(int,hm_et.split(':')); t=datetime.datetime(day.year,day.month,day.day,h,m,tzinfo=ET).astimezone(); return t.hour,t.minute
def entries():
    today=datetime.date.today(); e=[]
    for i in range(420):
        d=today+datetime.timedelta(days=i)
        for k,exp in events(d):
            if k=='hourly' or TIMES.get(k) not in ATTEMPTS: continue   # ask 59: no set time, no slot
            for hm in ATTEMPTS[TIMES[k]]+(ATTEMPTS['close'] if k=='claims' else []):
                h,m=local_hm(d,hm); e.append(dict(Month=d.month,Day=d.day,Hour=h,Minute=m))
    # the hourly refresh: one entry per hour with no month or day, which launchd fires every day (converted at today's
    # offset; the entry is rewritten at each run, so a clock change is picked up the day it happens)
    for hm in ATTEMPTS['hourly']:
        h,m=local_hm(today,hm); e.append(dict(Hour=h,Minute=m))
    seen=set(); out=[]
    for x in e:
        key=(x.get('Month'),x.get('Day'),x['Hour'],x['Minute'])
        if key not in seen: seen.add(key); out.append(x)
    return out
LASTDONE=os.path.join(HERE,'cache','last_done')   # the local time bhs_run.sh last completed a run (any label)
def slot_times(day):
    out=[]
    for k,exp in events(day):
        if TIMES.get(k) not in ATTEMPTS: continue   # ask 59: 'hourly' and series with no set time
        for hm in ATTEMPTS[TIMES[k]]+(ATTEMPTS['close'] if k=='claims' else []):
            h,m=map(int,hm.split(':')); out.append((datetime.datetime(day.year,day.month,day.day,h,m,tzinfo=ET).astimezone(),k,exp))
    return out
def missed_since(last,now=None):
    """the slots between the last completed run and now, oldest first. launchd folds every slot a sleeping Mac missed
    into one firing on wake (17 September 2026: the Mac slept 06:00-07:26 PDT through the claims slots and fired once
    at 07:26); that firing may land on a weekend or a quiet hour, and it must still do the work the missed slots would
    have done - a run refreshes everything, so one run catches up all of them"""
    now=now or datetime.datetime.now().astimezone(); out=[]; d=last.date()
    while d<=now.date():
        for t,k,exp in slot_times(d):
            if last<t<=now: out.append((t,k,exp))
        d+=datetime.timedelta(days=1)
    return out
def why_now():
    """(reasons, exit code): the slots missed since the last completed run when that is known, else today's releases"""
    try: last=datetime.datetime.fromisoformat(open(LASTDONE).read().strip())
    except Exception: last=None
    if last is not None:
        now=datetime.datetime.now().astimezone(); ms=missed_since(last,now)
        if not ms: return 'no slot since the last run at %s'%last.strftime('%a %H:%M'),3
        short={'claims':'weekly claims','h15':'the H.15 week','search':"the day's close",'tiles':'a front-page series','hourly':'the hourly refresh','eiaw':'the EIA weekly'}
        names=list(dict.fromkeys(short.get(k,NAMES.get(k,k).split(' (')[0])+' '+t.strftime('%a %H:%M') for t,k,exp in ms))
        late=(now-ms[0][0]).total_seconds()>3600
        return '; '.join(names)+(' - %d slot(s) missed while the Mac slept, caught up now'%len(ms) if late else ''),0
    r=reasons(datetime.date.today())
    return ('; '.join(r) if r else 'no release today'),(0 if r else 3)
def install():
    # caffeinate holds the Mac awake for the run's few minutes (-s on power, -i idle), so a run begun on a wake finishes
    # RunAtLoad: one run the moment the job loads - at every login, so a restart (a macOS update, a power loss) is
    # followed by a catch-up run the way a wake is
    p=dict(Label=LABEL,ProgramArguments=['/usr/bin/caffeinate','-s','-i','/bin/bash',RUN,'scheduled'],StartCalendarInterval=entries(),RunAtLoad=True,
           StandardOutPath=os.path.join(COL,'live','launchd.log'),StandardErrorPath=os.path.join(COL,'live','launchd.log'),
           EnvironmentVariables={'PATH':'/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin'})
    new=plistlib.dumps(p,sort_keys=True)
    old=open(PLIST,'rb').read() if os.path.exists(PLIST) else None
    n=len(p['StartCalendarInterval'])
    if old==new: print('launchd: schedule unchanged (%d entries; calendar through %s, claims through %s)'%(n,dated_through(),claims_through())); return
    os.makedirs(os.path.dirname(PLIST),exist_ok=True); open(PLIST,'wb').write(new)
    uid=os.getuid(); dom='gui/%d'%uid
    subprocess.run(['launchctl','bootout',dom+'/'+LABEL],capture_output=True)
    r=subprocess.run(['launchctl','bootstrap',dom,PLIST],capture_output=True,text=True)
    print(('launchd: schedule written (%d entries; calendar through %s, claims through %s); loaded'%(n,dated_through(),claims_through())) if r.returncode==0 else 'launchd: written but bootstrap said: '+(r.stderr or r.stdout).strip())

if __name__=='__main__':
    if '--why' in sys.argv:
        msg,rc=why_now(); print(msg); sys.exit(rc)
    if '--mark-done' in sys.argv:
        os.makedirs(os.path.dirname(LASTDONE),exist_ok=True); open(LASTDONE,'w').write(datetime.datetime.now().astimezone().isoformat()); sys.exit(0)
    if '--install' in sys.argv: install(); sys.exit(0)
    if '--calendar' in sys.argv:
        n=int(sys.argv[sys.argv.index('--calendar')+1]) if len(sys.argv)>sys.argv.index('--calendar')+1 else 150
        print(json.dumps(calendar(n))); sys.exit(0)
    today=datetime.date.today()
    for i in range(91):
        d=today+datetime.timedelta(days=i); r=reasons(d)
        if r: print(d.isoformat(),d.strftime('%a'),'|','; '.join(r))
    print('dated calendar through',dated_through(),'| claims calendar through',claims_through())
