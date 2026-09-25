"""THE BRISTOW HALL SYSTEM — the release calendar, fetched (no one in the loop).

FRED keeps a release calendar for every release it carries, past and scheduled, and serves it through its API
(`fred/release/dates`, `include_release_dates_with_no_data=true` for the dates still to come). The rule reads four
scheduled releases; their FRED release ids (checked with `fred/series/release` on 8 September 2026):
    50   Employment Situation (BLS)                        -> UNRATE, AWHMAN, NDMANEMP, CLF16OV   reference month: the month before
    192  Job Openings and Labor Turnover Survey (BLS)      -> JTSJOL                             reference month: the month whose end is 25-48 days before
    27   New Residential Construction (Census)             -> HOUST                              reference month: the month before
    180  Unemployment Insurance Weekly Claims Report (DOL) -> ICSA, CCSA, IURSA                  weekly; the exact Thursdays, holiday moves included
(Rule Zero, 8 September 2026: the first version used release 97 for housing starts. Release 97 is New Residential
SALES, a week after the construction report; its rows are removed here and never written again.)
Release 27's calendar lists the sales report's days as well; the construction report is the first of the month's
dates, so a reference month keeps the earliest date assigned to it. Only dates from a week ago onward are taken: a
past month's day is the vintage record's business (cache/relcal_*.csv, from the ALFRED tables), and a delayed past
release (the autumn of 2025) would otherwise be assigned to the wrong month.
This script merges the monthly dates into cache/release_schedule.csv (source noted; rows from other sources kept)
and writes the weekly claims dates to cache/claims_release_dates.csv. The API key is read from local.env inside the
process and never printed (Rule 12.6). Run by bhs_run.sh at the first run of each month, or by hand:
    python3 bhs_calendar_fetch.py"""
import os, sys, csv, json, datetime, subprocess
HERE=os.path.dirname(os.path.abspath(__file__))
ENV=os.path.join(os.path.expanduser('~'),'mnt','Onset Detector Data','onset-detector-new-2026-08-23','live_data','config','local.env')
SCHED=os.path.join(HERE,'cache','release_schedule.csv'); CLAIMS=os.path.join(HERE,'cache','claims_release_dates.csv')
def key():
    for line in open(ENV):
        if line.startswith('FRED_API_KEY='): return line.split('=',1)[1].strip().strip('"').strip("'")
    raise SystemExit('no FRED_API_KEY in local.env')
K=key()
today=datetime.date.today(); since=today-datetime.timedelta(days=7)
def fred_dates(rid):
    url=('https://api.stlouisfed.org/fred/release/dates?release_id=%d&include_release_dates_with_no_data=true&realtime_start=%s&realtime_end=9999-12-31&sort_order=asc&limit=1000&file_type=json&api_key=%s'
         %(rid,(today-datetime.timedelta(days=400)).isoformat(),K))
    r=subprocess.run(['curl','-sSL','-m','60',url],capture_output=True,text=True)
    if r.returncode!=0: raise SystemExit('curl failed for release %d'%rid)
    j=json.loads(r.stdout)
    if 'release_dates' not in j: raise SystemExit('FRED answered without release_dates for release %d: %s'%(rid,str(j)[:200].replace(K,'***')))
    return sorted({datetime.date.fromisoformat(x['date']) for x in j['release_dates']})
def month_end(y,m):
    n=datetime.date(y+(m==12),(m%12)+1,1); return n-datetime.timedelta(days=1)
def prev_month(d):
    f=d.replace(day=1)-datetime.timedelta(days=1); return f.replace(day=1)
def ref_month(kind,d):
    if kind in ('UNRATE','HOUST'): return prev_month(d)
    if kind in ('GDPC1','GDPNOW'):   # v3.73: the reference quarter's first month - the quarter before the day's quarter (GDPNow: the current quarter once the advance estimate is out)
        q=datetime.date(d.year,3*((d.month-1)//3)+1,1)
        if kind=='GDPNOW' and not (d.month%3==1 and d.day<=29): return q
        return prev_month(prev_month(prev_month(q)))
    if kind=='JTSJOL':
        m=prev_month(d)
        for _ in range(4):
            gap=(d-month_end(m.year,m.month)).days
            if 25<=gap<=48: return m
            m=prev_month(m)
        return None
existing={}
if os.path.exists(SCHED):
    for r in csv.DictReader(open(SCHED)):
        if 'release_id 97' in r.get('source',''): continue          # the wrong release (New Residential Sales); dropped
        if r.get('source','').startswith('FRED') and datetime.date.fromisoformat(r['release_date'])<since: continue   # past FRED rows: the vintage record has them
        existing[(r['series'],r['reference_month'])]=r
added=0; report=[]
for kind,rid in (('UNRATE',50),('JTSJOL',192),('HOUST',27),('GDPC1',53),('GDPNOW',386)):   # v3.73 feeds (23 September 2026, collection 333): GDP (release 53) and GDPNow (386), every scheduled day kept
    ds=fred_dates(rid); fut=[d for d in ds if d>=since]
    report.append('%s: FRED lists %d dates, %d from a week ago on, last %s'%(kind,len(ds),len(fut),ds[-1].isoformat() if ds else 'none'))
    for d in fut:
        m=ref_month(kind,d)
        if m is None: continue
        k=(kind,m.isoformat()) if kind not in ('GDPC1','GDPNOW') else (kind,d.isoformat())   # v3.73: a quarter's three GDP estimates and every GDPNow update are separate days
        if k in existing: continue                                   # the earliest date of a month wins (release 27 lists the sales day too)
        existing[k]=dict(series=kind,reference_month=m.isoformat(),release_date=d.isoformat(),source='FRED release calendar, release_id %d, fetched %s'%(rid,today.isoformat())); added+=1
rows=sorted(existing.values(),key=lambda r:(r['series'],r['reference_month']))
with open(SCHED,'w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['series','reference_month','release_date','source']); w.writeheader(); w.writerows(rows)
cl=fred_dates(180); fut=[d for d in cl if d>=today]
with open(CLAIMS,'w',newline='') as f:
    w=csv.writer(f); w.writerow(['release_date','weekday','source'])
    for d in cl: w.writerow([d.isoformat(),d.strftime('%a'),'FRED release calendar, release_id 180, fetched %s'%today.isoformat()])
report.append('claims: FRED lists %d dates, %d still to come, last %s; not on a Thursday: %s'%(len(cl),len(fut),cl[-1].isoformat() if cl else 'none',[d.isoformat() for d in fut if d.weekday()!=3]))
last=max(datetime.date.fromisoformat(r['release_date']) for r in rows)
print('release schedule: %d rows added; dated schedule now through %s'%(added,last.isoformat()))
for line in report: print('  '+line)
