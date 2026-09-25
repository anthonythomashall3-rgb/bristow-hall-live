"""THE BRISTOW HALL SYSTEM — the refresh (collection 105). v3.55 copy (16 September 2026): also refreshes every carried-leg channel, confirmer and first-print file, and runs bhs_build_v355.py against the staged version file. Pulls the current print of every series the rule reads,
writes it where the lab reads it (keeping a dated copy of what it replaces), appends today's vintage to the six
ALFRED tables where it carries something new, extends the first-print files, rebuilds the release calendars and the
two objects that live in cache/objects.pkl, then runs bhs_build.py unless told not to. The FRED key is read from
local.env inside this process and is never printed (Rule 12.6). Run from the collection's workspace:
    python3 bhs_update.py [--no-build]
Transport is curl, as in collection 25's fetcher.

Audit of 8 September 2026 (Rule Zero): until then the refresh left three things behind. The first-print file of the
weekly claims (collection 45) was never extended, so a new week entered the current file and not the rule's
first-print objects; the insured-rate base series in cache/objects.pkl stopped at its cached end; the JOLTS and
labour-force vintage tables and the three release calendars (relcal_*.csv) were not refreshed. All four are done here
now. The first prints of new claims weeks come from ALFRED's initial releases (output_type=4), which on the release
day are the advance figures just published; the release day is ALFRED's realtime_start."""
import sys
import os, sys, json, subprocess, datetime, glob, shutil, io, pickle, csv
import pandas as pd, numpy as np
HOME=os.path.expanduser('~'); MNT=os.path.join(HOME,'mnt','Onset Detector Data')
ENV=os.path.join(MNT,'onset-detector-new-2026-08-23','live_data','config','local.env')
KEY=None
for line in open(ENV):
    if line.startswith('FRED_API_KEY='): KEY=line.strip().split('=',1)[1].strip().strip('"').strip("'")
assert KEY and len(KEY)==32, 'no FRED key in local.env'
W=os.path.join(MNT,'24_bristow_rule_lab','workspace'); D=os.path.join(W,'lab','data','fred_weekly')
C25=os.path.join(MNT,'25_fred_daily_weekly'); AL=os.path.join(MNT,'onset-detector-new-2026-08-23','27_realtime_vintages','alfred_all_vintages')
C45=os.path.join(MNT,'45_dol_first_prints_2026-09','national_first_prints.csv')
COL=os.path.join(MNT,'105_bristow_hall_system_2026-09-08'); today=datetime.date.today().isoformat()
BK=os.path.join(COL,'live','backup_'+today); os.makedirs(BK,exist_ok=True); os.makedirs('cache',exist_ok=True)
REPORT=[]
# ---- 17 September 2026 (Anthony: "make each refresh take seconds, 100% accurate"): pull only what can have changed.
# ---- The day's first run pulls everything (the safety net against a calendar error or an unscheduled revision) and
# ---- records each series' last observation; later runs pull a FRED series only on a day its release publishes, and
# ---- only until its last observation has moved since the day's first run. The Department's weekly series are due on
# ---- claims days; the daily rates every business day. A series with no calendar on file is always pulled.
FULL_MARK=os.path.join('cache','full_refresh_'+today); FULL=(not os.path.exists(FULL_MARK)) or ('--full' in sys.argv)
_DS_PATH=os.path.join('cache','daystart_last_'+today+'.json')
try: DAYSTART=json.load(open(_DS_PATH))
except Exception: DAYSTART={}
try: _CAL=json.load(open(os.path.join('cache','leg_release_dates.json')))
except Exception: _CAL={}
_ALIAS={'NDMANEMP':'UNRATE','CLF16OV':'UNRATE','PERMIT':'HOUST','SAHMREALTIME':'UNRATE','SP500':None}
try:
    sys.path.insert(0,os.getcwd()); import bhs_schedule as _bs
    _EV={k_ for k_,_ in _bs.events(datetime.date.today())}
except Exception as _e: _EV={'claims'}; print('schedule not read for the gate:',_e)
_CLAIMS_TODAY='claims' in _EV
class _Skip(Exception): pass
def _last_date_of(path):
    try:
        with open(path,'rb') as _f:
            _f.seek(0,2); _n=_f.tell(); _f.seek(max(0,_n-400)); _tail=_f.read().decode('utf-8','replace').strip().splitlines()
        for _ln in reversed(_tail):
            if _ln[:4].isdigit(): return _ln.split(',')[0][:10]
    except Exception: pass
    return None
def _not_advanced(sid,path):
    if path is None or sid not in DAYSTART: return True
    _now=_last_date_of(path)
    return _now is None or _now==DAYSTART[sid]
def due(sid,path=None,kind=None):
    """whether to pull this series on this run"""
    if FULL: return True
    if _META_OK and sid in _KNOWN:   # FRED's own word (see the change check below): pull when its stamp is not the one we
        u_,e_=_KNOWN[sid]            # last pulled at, or when it holds an observation our file does not; otherwise nothing has changed
        if _SEEN.get(sid)!=u_: return True
        if path is not None and e_:
            _now=_last_date_of(path)
            if _now is not None and _now<e_: return True
        return False
    if kind=='claims': return _CLAIMS_TODAY and _not_advanced(sid,path)
    if kind=='daily': return datetime.date.today().weekday()<5 and _not_advanced(sid,path)
    _a=_ALIAS.get(sid,sid)
    if _a is None: return True
    ds=(_CAL.get(_a) or {}).get('dates')
    if ds is None: return True
    # A CALENDAR THAT HAS RUN OUT MEANS PULL, NEVER SKIP (20 September 2026, collection 274). cache/leg_release_dates.json
    # was rebuilt by the leg tier's refresh, which went out with the tier in v3.59; its last dates fall between October and
    # December 2026. Past a series' last date, "today is not one of its release days" is a fact about the file and not
    # about the release, and on a run where FRED's own change check has failed this rule is the only one left.
    if today>max(ds): return True
    if today not in ds: return False
    return _not_advanced(sid,path)
SKIPPED=[]
import time as _time0; _T0=_time0.time(); _TIMING=open(os.path.join('out','bhs_update_timing.txt'),'w') if os.path.isdir('out') else None
def say(*a):
    t=' '.join(str(x) for x in a); print(t); REPORT.append(t)
    if _TIMING:   # 17 September 2026: every line stamped with the seconds since the run began, so the slow steps show
        try: _TIMING.write('%7.1fs  %s\n'%(_time0.time()-_T0,t)); _TIMING.flush()
        except Exception: pass
def fred(series,**params):
    q='&'.join(f'{k}={v}' for k,v in params.items())
    url=f'https://api.stlouisfed.org/fred/series/observations?series_id={series}&api_key={KEY}&file_type=json&{q}'
    for _try in range(4):   # v3.55: FRED answers 429 when the standing collector is also drawing on the key; wait and retry
        r=subprocess.run(['curl','-sSL','-m','40',url],capture_output=True,text=True)
        if r.returncode!=0:   # 17 Sep 2026: a run right after the Mac wakes finds no network for a few seconds; wait and retry rather than fail the run
            if _try<3: import time as _t; _t.sleep(15*(_try+1)); continue
            raise RuntimeError(f'curl failed for {series}')
        try: d=json.loads(r.stdout)
        except Exception: d={'error_code':'403','error_message':'FRED answered without JSON (edge block?)'}   # Akamai's Access Denied page, seen 17 Sep 2026
        if 'observations' in d or str(d.get('error_code')) not in ('429','403'): break
        import time as _t; _t.sleep(30*(_try+1))
    if 'observations' not in d: raise RuntimeError(f'FRED error for {series}: {str(d)[:80].replace(KEY,"***")}')
    s=pd.Series({o['date']:(np.nan if o['value']=='.' else float(o['value'])) for o in d['observations']})
    s.index=pd.to_datetime(s.index); return s.sort_index()
def alfred_first(series,start='2000-01-01'):
    """ALFRED's initial release of every observation from `start`: value and the day it was released"""
    q=f'output_type=4&realtime_start=1776-07-04&realtime_end=9999-12-31&observation_start={start}'
    url=f'https://api.stlouisfed.org/fred/series/observations?series_id={series}&api_key={KEY}&file_type=json&{q}'
    for _try in range(4):   # v3.55: FRED answers 429 when the standing collector is also drawing on the key; wait and retry
        r=subprocess.run(['curl','-sSL','-m','40',url],capture_output=True,text=True)
        if r.returncode!=0:   # 17 Sep 2026: a run right after the Mac wakes finds no network for a few seconds; wait and retry rather than fail the run
            if _try<3: import time as _t; _t.sleep(15*(_try+1)); continue
            raise RuntimeError(f'curl failed for {series}')
        try: d=json.loads(r.stdout)
        except Exception: d={'error_code':'403','error_message':'FRED answered without JSON (edge block?)'}   # Akamai's Access Denied page, seen 17 Sep 2026
        if 'observations' in d or str(d.get('error_code')) not in ('429','403'): break
        import time as _t; _t.sleep(30*(_try+1))
    if 'observations' not in d: raise RuntimeError(f'ALFRED error for {series}: {str(d)[:80].replace(KEY,"***")}')
    obs=[o for o in d['observations'] if o['value']!='.']
    return pd.DataFrame({'first':[float(o['value']) for o in obs],'release':[o['realtime_start'] for o in obs]},index=pd.to_datetime([o['date'] for o in obs])).sort_index()
def backup(path):
    if not os.path.exists(path): return
    dst=os.path.join(BK,os.path.basename(path))
    try:   # 17 Sep 2026: a read-only source (the lab's HOUST vintage table, once a symlink) left a read-only backup that the next copy could not overwrite
        if os.path.exists(dst): os.chmod(dst,0o644)
    except Exception: pass
    shutil.copy2(path,dst)
    try: os.chmod(dst,0o644)
    except Exception: pass
# ---- 17 September 2026 (Anthony: "as fast as possible, as safe as possible"): before any series is pulled, FRED is asked
# ---- what it has changed. cache/fred_meta.json keeps every tracked series' last-updated stamp and last observation as
# ---- FRED states them ('known') beside the stamp it carried when we last pulled it ('seen'); due() pulls a series when the
# ---- two differ, or when FRED holds an observation our file does not, and leaves it alone when FRED itself says nothing
# ---- has changed - a revision on an unscheduled day is caught within the hour, and a quiet hour pulls nothing. The
# ---- stamps come from one call listing everything FRED updated since the last complete check (fred/series/updates);
# ---- on the day's first run, when no complete baseline is on file, or when that list runs past a thousand series (a
# ---- bulk update), one call per release (fred/release/series; one per series for releases of more than a thousand)
# ---- rebuilds the whole picture. A call that fails leaves its series on the release-calendar rule above - never on a
# ---- stale stamp - and the baseline is rebuilt on the next run.
_META_PATH=os.path.join('cache','fred_meta.json')
try: _META=json.load(open(_META_PATH))
except Exception: _META={}
_KNOWN=_META.setdefault('known',{}); _SEEN=_META.setdefault('seen',{}); _BIG=_META.setdefault('big',{}); _RIDS=_META.setdefault('rid',{})
_META_OK=False; _PULLED={}; _FAILED=set()   # series pulled this run (with the last observation now on file) and series whose pull failed
def _fred_json(url,m=40):
    import time as _t
    for _try in range(4):
        r_=subprocess.run(['curl','-sSL','-m',str(m),url],capture_output=True,text=True)
        if r_.returncode!=0:
            if _try<3: _t.sleep(5*(_try+1)); continue
            return None
        try: d_=json.loads(r_.stdout)
        except Exception: d_={'error_code':'403'}
        if 'error_code' not in d_: return d_
        if str(d_.get('error_code')) not in ('429','403'): return None
        _t.sleep(20*(_try+1))
    return None
def _tracked():
    """series -> release id for every FRED series this refresh pulls: the leg channels from cache/leg_release_dates.json,
    the 53 state insured rates by one call each, once"""
    try: _l=json.load(open(os.path.join('cache','leg_release_dates.json')))
    except Exception: _l={}
    for s_,e_ in _l.items():
        if e_.get('rid'): _RIDS[s_]=e_['rid']
    for f_ in sorted(glob.glob(os.path.join(D,'*INSUREDUR.csv'))):
        s_=os.path.basename(f_)[:-4]
        if s_ not in _RIDS:
            d_=_fred_json(f'https://api.stlouisfed.org/fred/series/release?series_id={s_}&api_key={KEY}&file_type=json')
            r_=((d_ or {}).get('releases') or [{}])[0].get('id')
            if r_: _RIDS[s_]=r_
    return dict(_RIDS)
def _meta_slow(rids):
    """every tracked series' stamp, one call per release (one per series in a release of more than a thousand); the
    series of a release that did not answer are dropped from the picture, so the calendar rule governs them"""
    by_={}
    for s_,r_ in rids.items(): by_.setdefault(str(r_),[]).append(s_)
    def one_(r_):
        sids_=by_[r_]; got_={}
        if r_ not in _BIG:
            d_=_fred_json(f'https://api.stlouisfed.org/fred/release/series?release_id={r_}&api_key={KEY}&file_type=json&limit=1000')
            if d_ is None: return r_,None
            if int(d_.get('count',0))>1000: _BIG[r_]=int(d_['count'])
            else:
                ex_={x_['id']:x_ for x_ in d_.get('seriess',[])}
                for s_ in sids_:
                    if s_ in ex_: got_[s_]=[ex_[s_].get('last_updated'),ex_[s_].get('observation_end')]
                return r_,got_
        for s_ in sids_:
            d_=_fred_json(f'https://api.stlouisfed.org/fred/series?series_id={s_}&api_key={KEY}&file_type=json')
            if d_ is None: return r_,None
            x_=(d_.get('seriess') or [{}])[0]
            if x_.get('id'): got_[s_]=[x_.get('last_updated'),x_.get('observation_end')]
        return r_,got_
    from concurrent.futures import ThreadPoolExecutor as _TPEm
    with _TPEm(max_workers=3) as ex_: res_=list(ex_.map(one_,list(by_)))
    ok_=True
    for r_,got_ in res_:
        if got_ is None:
            ok_=False
            for s_ in by_[r_]: _KNOWN.pop(s_,None)
        else: _KNOWN.update(got_)
    return ok_
def _meta_fast(rids,asof):
    """the series FRED updated since the last complete check, in one call; None when the call failed or the list runs
    past a thousand series"""
    from zoneinfo import ZoneInfo as _ZI
    ct_=_ZI('America/Chicago'); now_=datetime.datetime.now(ct_)   # FRED's stamps are Central time
    st_=(datetime.datetime.strptime(asof,'%Y%m%d%H%M').replace(tzinfo=ct_)-datetime.timedelta(minutes=20)).strftime('%Y%m%d%H%M')
    et_=(now_+datetime.timedelta(hours=1)).strftime('%Y%m%d%H%M')
    d_=_fred_json(f'https://api.stlouisfed.org/fred/series/updates?api_key={KEY}&file_type=json&filter_value=all&start_time={st_}&end_time={et_}&limit=1000')
    if d_ is None or 'seriess' not in d_ or int(d_.get('count',0))>1000: return None
    n_=0
    for x_ in d_['seriess']:
        if x_['id'] in rids: _KNOWN[x_['id']]=[x_.get('last_updated'),x_.get('observation_end')]; n_+=1
    return n_
try:
    from zoneinfo import ZoneInfo as _ZI0
    _rids=_tracked(); _asof=_META.get('asof'); _how='calendar rule'
    _now_c=datetime.datetime.now(_ZI0('America/Chicago')).strftime('%Y%m%d%H%M')
    if FULL or not _asof or any(s_ not in _KNOWN for s_ in _rids):
        _META_OK=_meta_slow(_rids); _how='every release asked'; _META['asof']=_now_c if _META_OK else None
    else:
        _n=_meta_fast(_rids,_asof)
        if _n is None: _META_OK=_meta_slow(_rids); _how='every release asked (the list since the last check ran long)'; _META['asof']=_now_c if _META_OK else None
        else: _META_OK=True; _META['asof']=_now_c; _how=f'{_n} updated since {_asof[8:10]}:{_asof[10:12]} CT'
    json.dump(_META,open(_META_PATH,'w'))
    _EVER=set(_META.get('ever',[]))   # the series this refresh has pulled at some run (a tracked series pulled elsewhere is not reported as changed)
    _chg=[s_ for s_ in _rids if s_ in _KNOWN and s_ in _EVER and _SEEN.get(s_)!=_KNOWN[s_][0]]
    say(f'FRED change check: {len(_rids)} series tracked; {len(_chg)} changed since last pulled ({_how})'+('' if _META_OK else '; a release did not answer: the calendar rule governs this run')+(': '+', '.join(_chg[:12])+(' ...' if len(_chg)>12 else '') if _chg and _META_OK and not FULL else ''))
except Exception as e: _META_OK=False; say(f'FRED change check failed ({e}); the calendar rule governs this run')
KEEP_BEYOND={'UMCSENT'}   # FRED carries this a month late at the source's request; the source's own newer months are kept (17 September 2026)
def refresh_series(series,path,start='1900-01-01',quiet=False,kind=None):
    """replace a date,value csv with the current print of the whole series; report what moved (quiet: return the line).
    Not due on this run (see due()): the file stands and the series in it is returned."""
    old=None
    if os.path.exists(path):
        try: old=pd.read_csv(path).iloc[:,:2]; old.columns=['date','value']; old['date']=pd.to_datetime(old['date'],errors='coerce'); old=old.set_index('date')['value']
        except Exception: old=None
    if old is not None and not due(series,path,kind):
        SKIPPED.append(series); return (old,'') if quiet else old
    if series not in DAYSTART: DAYSTART[series]=_last_date_of(path)
    new=fred(series,observation_start=start)
    backup(path)
    out=new.dropna().rename('value').to_frame(); out.index.name='date'
    if series in KEEP_BEYOND and old is not None:   # months the source has published ahead of FRED (UMCSENT: the press page, s2/live_sources.py) stay
        extra=old.dropna(); extra=extra[extra.index>out.index.max()]
        if len(extra): out=pd.concat([out,extra.rename('value').to_frame()]); out.index.name='date'
    out.to_csv(path); _PULLED[series]=str(out.index.max().date())
    o_last=None if old is None or old.dropna().empty else old.dropna().index[-1].date()
    msg=f'{series:14s} {str(o_last):>10s} -> {out.index.max().date()}  ({len(out)} obs)'
    if quiet: return new,msg
    say(msg); return new
# ---- weekly claims objects (current print) ----
# ONE SERIES MAY NOT STOP THE RULE (20 September 2026, collection 274): a FRED error on one of these used to end the
# update, and the site then stood still - with the rule's other inputs current, and the next release possibly the call.
# The series stays as it was, it is named in _FAILED so the next run pulls it again, and the off-Mac watchdog pushes
# once a day if what the site holds falls behind the Department's own schedule.
for s in ['ICSA','CCSA','IURSA']:
    try: refresh_series(s,os.path.join(D,f'{s}.csv'),kind='claims')
    except Exception as e: say(f'{s:14s} NOT refreshed ({e})'); _FAILED.add(s)
# the 53 state insured rates three at a time (17 September 2026: one slow FRED afternoon took them from 20 s to 140 s
# one by one); the lines are printed in the fixed order once all are in
def _one_state(f):
    sid=os.path.basename(f)[:-4]
    try: return refresh_series(sid,f,quiet=True,kind='claims')[1]
    except Exception as e: _FAILED.add(sid); return f'{sid}: {e}'
from concurrent.futures import ThreadPoolExecutor as _TPE0
with _TPE0(max_workers=3) as _ex0:
    for _m in _ex0.map(_one_state,sorted(glob.glob(os.path.join(D,'*INSUREDUR.csv')))):
        if _m: say(_m)
# ---- the weekly claims FIRST PRINTS: collection 45, extended from ALFRED's initial releases ----
try:
    if not FULL and not _CLAIMS_TODAY: raise _Skip('not a claims day')
    N=pd.read_csv(C45,dtype=str)
    have_ic=set(N[N.icsa.notna()&(N.icsa!='')].ic_week_ended); have_iu=set(N[N.iur_sa.notna()&(N.iur_sa!='')].iu_week_ended)
    A=alfred_first('ICSA',start='2026-01-01'); U=alfred_first('IURSA',start='2026-01-01'); C=alfred_first('CCSA',start='2026-01-01')
    rows={}                                    # one row per release day: the initial-claims week and the insured week it carried
    def row(rel):
        if rel not in rows: rows[rel]=dict(release=pd.Timestamp(rel).strftime('%m%d%y'),ic_week='',icsa='',icsa_prev_rev='',icnsa='',iu_week='',iur_sa='',iusa='',iunsa='',kind='alfred',release_date=rel,ic_week_ended='',iu_week_ended='')
        return rows[rel]
    for w,r in A.iterrows():
        wk=w.strftime('%Y-%m-%d')
        if wk in have_ic:
            e=N[(N.ic_week_ended==wk)&(N.kind=='dol_pdf')]
            if len(e):
                same=abs(float(e.icsa.iloc[0])-float(r['first']))<0.5; say(f"first prints: ALFRED initial release for the week ending {wk} ({float(r['first']):.0f}) {'agrees with' if same else 'DIFFERS FROM'} the Department's release ({float(e.icsa.iloc[0]):.0f}) filed earlier"+('' if same else ' - kept as filed; check'))
                N.loc[e.index,'kind']='dol_pdf+alfred'; N.to_csv(C45,index=False)
            continue
        x=row(r['release']); x.update(ic_week=w.strftime('%B %-d'),icsa=str(float(r['first'])),ic_week_ended=wk)
    for w,r in U.iterrows():
        wk=w.strftime('%Y-%m-%d')
        if wk in have_iu: continue
        x=row(r['release']); x.update(iu_week=w.strftime('%B %-d'),iur_sa=str(float(r['first'])),iu_week_ended=wk,iusa=(str(float(C.loc[w,'first'])) if w in C.index else ''))
    for x in rows.values():                    # a release carries the insured week seven days before its claims week
        if not x['iu_week_ended'] and x['ic_week_ended']: x['iu_week_ended']=(pd.Timestamp(x['ic_week_ended'])-pd.Timedelta(days=7)).strftime('%Y-%m-%d')
        if not x['ic_week_ended'] and x['iu_week_ended']: x['ic_week_ended']=(pd.Timestamp(x['iu_week_ended'])+pd.Timedelta(days=7)).strftime('%Y-%m-%d')
    rows=list(rows.values())
    if rows:
        backup(C45); N=pd.concat([N,pd.DataFrame(rows)],ignore_index=True); N['_rd']=pd.to_datetime(N.release_date); N=N.sort_values(['_rd','release']).drop(columns='_rd'); N.to_csv(C45,index=False)
        say(f'first prints: {len(rows)} release(s) appended to collection 45 from ALFRED initial releases: {[(x["release_date"],x["ic_week_ended"],x["icsa"],x["iu_week_ended"],x["iur_sa"]) for x in rows]}')
    else: say(f'first prints: collection 45 already carries every week ALFRED has (through {A.index.max().date()}, released {A["release"].iloc[-1]})')
except _Skip as e: SKIPPED.append('first prints')
except Exception as e: say(f'first prints: NOT extended ({e})')
# ---- the same first prints from the Department's own release on the release day (bhs_dol_press.py), when FRED/ALFRED lag ----
try:
    if not FULL and not _CLAIMS_TODAY: raise _Skip('not a claims day')
    from bhs_dol_press import dol_press_extend
    dol_press_extend(C45,say)
except _Skip as e: SKIPPED.append('DOL release')
except Exception as e: say(f'DOL release: NOT read ({e})')
# ---- the search week (v3.27): Google searches for unemployment, daily, stitched onto the history (collection 108) ----
try:
    import subprocess
    _c108=os.path.join(MNT,'108_high_frequency_speed_2026-09-10')
    if not FULL:
        _lastd=_last_date_of(os.path.join(_c108,'google_trends','live','unemp_stitched_daily.csv')) or ''
        if _lastd>=(datetime.date.today()-datetime.timedelta(days=1)).isoformat(): raise _Skip('history through '+_lastd)
    # THE INTERPRETER, AND WHY (20 September 2026, collection 274). This ran the collection's own virtual environment,
    # which exists on the Mac and not in the cloud bundle, so on the runner the search week - one of the rule's own
    # inputs, and its fastest - failed on a missing file every run and was never refreshed. The venv is used where it
    # is; anywhere else the interpreter running this, which now has pytrends in requirements.txt. The wait is shorter
    # than the Mac's: Google refuses a data-centre address more often than a home one, and the job has twenty minutes.
    _py=os.path.join(_c108,'.venv','bin','python')
    if not os.path.exists(_py): _py=sys.executable
    _r=subprocess.run([_py,os.path.join(_c108,'scripts','trends_live.py')],capture_output=True,text=True,timeout=300)
    for _ln in (_r.stdout.strip().splitlines() or [_r.stderr.strip()[-120:] or 'search week: no output']): say(_ln)   # one line per term (v3.29); 'appended' on any of them is new data
except _Skip as e: SKIPPED.append('search week')
except Exception as e: say(f'search week: NOT refreshed ({e})')
# the Department's ETA 539 state file (the breadth object's data; collection 37's panel). Found stale on 11 September
# 2026 - built once on 4 September and never refreshed - so the panel is now extended at every run, weeks after its last
# only (the weeks in hand keep their first-published values).
try:
    if not FULL and not _CLAIMS_TODAY: raise _Skip('not a claims day')
    _r=subprocess.run([sys.executable,os.path.join('s2','state539_live.py')]+(['--force'] if FULL else []),capture_output=True,text=True,timeout=600)   # --force: the day's first run downloads the file whatever its headers say
    for _ln in (_r.stdout.strip().splitlines() or [(_r.stderr.strip()[-120:] or 'state 539: no output')]): say(_ln)
except _Skip as e: SKIPPED.append('state 539')
except Exception as e: say(f'state 539: NOT refreshed ({e})')
# the state FIRST PRINTS the breadth proposer reads (collection 45's wide file): parsed from the weekly press release
# PDF this system already downloads, because the Department's page-8 archive runs about two weeks behind (11 Sep 2026).
try:
    if not FULL and not _CLAIMS_TODAY: raise _Skip('not a claims day')
    _r=subprocess.run([sys.executable,os.path.join('s2','state_press_live.py')],capture_output=True,text=True,timeout=600)
    for _ln in (_r.stdout.strip().splitlines() or [(_r.stderr.strip()[-120:] or 'state first prints: no output')]): say(_ln)
except _Skip as e: SKIPPED.append('state first prints')
except Exception as e: say(f'state first prints: NOT refreshed ({e})')
# the home page's current readings (collection 109): the published series the programme shows beside its own indicator
try:
    _r=subprocess.run([sys.executable,os.path.join('s2','home_tiles.py')],capture_output=True,text=True,timeout=300)
    for _ln in (_r.stdout.strip().splitlines() or [(_r.stderr.strip()[-120:] or 'home tiles: no output')]): say(_ln)
except Exception as e: say(f'home tiles: NOT refreshed ({e})')
# ---- the spread's two rates ----
def _safe_refresh(series,path,**kw):   # v3.66 (22 September 2026, collection 295): one FRED error keeps the file on disk, marks the series due, and the run goes on
    try: return refresh_series(series,path,**kw)
    except Exception as e:
        say(f'{series:14s} NOT refreshed ({e})'); _FAILED.add(series)
        _o=pd.read_csv(path).iloc[:,:2]; _o.columns=['date','value']; _o['date']=pd.to_datetime(_o['date'],errors='coerce'); return _o.set_index('date')['value']
_safe_refresh('WTB3MS',os.path.join(C25,'fred_weekly','WTB3MS.csv'),kind='daily')
_safe_refresh('DCPN30',os.path.join(C25,'fred_daily','DCPN30.csv'),kind='daily')
_safe_refresh('DCPF1M',os.path.join(C25,'fred_daily','DCPF1M.csv'),kind='daily')   # the financial paper rate: the spread reads the wider of the two markets (v3.26)
_safe_refresh('PERMIT','cache/surveys/PERMIT.csv')   # the current file of building permits (v3.27): the permits half runs over its months; the vintage table gives each month's reading as of its day
# ---- the Sahm rule as FRED publishes it in real time (the page's comparator) ----
try:
    if not due('SAHMREALTIME','cache/SAHMREALTIME.csv'): raise _Skip('not a release day')
    sr=fred('SAHMREALTIME'); backup('cache/SAHMREALTIME.csv'); o_=sr.dropna().rename('SAHMREALTIME').to_frame(); o_.index.name='date'; o_.to_csv('cache/SAHMREALTIME.csv'); say(f'SAHMREALTIME    through {sr.dropna().index[-1].strftime("%Y-%m")}: {sr.dropna().iloc[-1]:.2f}')
    _PULLED['SAHMREALTIME']=sr.dropna().index[-1].strftime('%Y-%m-%d')
except _Skip as e: SKIPPED.append('SAHMREALTIME')
except Exception as e: say(f'SAHMREALTIME: fetch failed ({e})'); _FAILED.add('SAHMREALTIME')
# ---- the monthly first-print objects: append today's vintage where it carries something new ----
def _monthly_vintage(s):
    # each series inside its own try (see the claims loop above): one bad answer from FRED may not end the update
    path=os.path.join(AL,f'{s}_all_vintages.csv')
    if not os.path.exists(path): say(f'{s:14s} no vintage table at {path}'); return
    if not due(s): SKIPPED.append(s+' vintage'); return
    tab=pd.read_csv(path,index_col=0); tab.index=pd.to_datetime(tab.index)
    cur=fred(s,realtime_start=today,realtime_end=today,observation_start='1940-01-01')
    lastcol=tab.columns[-1]; lastdate=tab.index[-1]; newdate=cur.dropna().index[-1]
    changed=(newdate>lastdate) or (abs(float(cur.get(lastdate,np.nan))-float(pd.to_numeric(tab[lastcol],errors='coerce').get(lastdate,np.nan)))>1e-9 if lastdate in cur.index else False)
    if changed:
        # the vintage is named by the day this print was PUBLISHED (ALFRED's realtime_start of the newest observation),
        # not by the day the refresh ran: the release calendars (relcal_*.csv) are read off these column names
        try: vday=alfred_first(s,start=newdate.strftime('%Y-%m-%d'))['release'].iloc[-1]
        except Exception: vday=today
        backup(path); col=f'{s}_{vday.replace("-","")}'
        if col in tab.columns: tab=tab.drop(columns=[col])
        tab=tab.reindex(tab.index.union(cur.index)).sort_index(); tab=pd.concat([tab,cur.reindex(tab.index).rename(col)],axis=1)
        tab.index.name='date'; tab.to_csv(path,na_rep='')
        say(f'{s:14s} vintage {col} appended: data through {newdate.date()} (was {lastdate.date()}); published {vday}')
    else: say(f'{s:14s} no new print (through {lastdate.date()}, last vintage {lastcol})')
    _PULLED[s]=str(newdate.date())
for s in ['UNRATE','HOUST','AWHMAN','NDMANEMP','JTSJOL','CLF16OV','PERMIT']:   # PERMIT from v3.27 (walk51): the housing x rate pair reads starts or permits
    try: _monthly_vintage(s)
    except Exception as e: say(f'{s:14s} vintage NOT refreshed ({e})'); _FAILED.add(s)
# ---- v3.73 (23 September 2026, collection 333): THE VINTAGE TABLES THE GRADE AND THE PAYROLL CLOSER READ - real GDP, GDPNow, industrial production, payrolls.
# ---- Every vintage FRED has published after the last column in hand is appended under its own vintage day (GDPNow prints several a
# ---- month; a vintage named by the day its print was published, not by the day this ran). A failure keeps the table in hand.
def _append_vintages(s):
    path=os.path.join(AL,f'{s}_all_vintages.csv')
    if not os.path.exists(path): say(f'{s:14s} no vintage table at {path}'); return
    if not due(s): SKIPPED.append(s+' vintages'); return
    tab=pd.read_csv(path,index_col=0); tab.index=pd.to_datetime(tab.index)
    last=pd.Timestamp(tab.columns[-1].split('_')[-1]); start=(last-pd.Timedelta(days=400)).date().isoformat()
    url=f'https://api.stlouisfed.org/fred/series/vintagedates?series_id={s}&api_key={KEY}&file_type=json&realtime_start={start}&realtime_end={today}'
    r=subprocess.run(['curl','-sSL','-m','40',url],capture_output=True,text=True)
    try: vd=json.loads(r.stdout).get('vintage_dates',[])
    except Exception: vd=[]
    new=[d for d in vd if pd.Timestamp(d)>last]
    if not new: say(f'{s:14s} no new vintage since {last.date()} (through {tab.index[-1].date()})'); _PULLED[s]=str(tab.index[-1].date()); return
    added=0
    for d in sorted(new):
        cur=fred(s,realtime_start=d,realtime_end=d,observation_start='1919-01-01').dropna()
        if not len(cur): continue
        col=f'{s}_{d.replace("-","")}'
        if added==0: backup(path)
        if col in tab.columns: tab=tab.drop(columns=[col])
        tab=tab.reindex(tab.index.union(cur.index)).sort_index(); tab=pd.concat([tab,cur.reindex(tab.index).rename(col)],axis=1); added+=1
    if added:
        tab.index.name='date'; tab.to_csv(path,na_rep=''); say(f'{s:14s} {added} vintage(s) appended, the last {new[-1]}: data through {tab.index[-1].date()}')
    _PULLED[s]=str(tab.index[-1].date())
for s in ['PAYEMS','GDPC1','GDPNOW','INDPRO']:
    try: _append_vintages(s)
    except Exception as e: say(f'{s:14s} vintages NOT refreshed ({e})'); _FAILED.add(s)
# ---- v3.73 (23 September 2026, collection 333; collection 330): THE INDEED POSTINGS INDEX, the vacancy channel's bridge through a JOLTS-dark spell. Keyless, from the
# ---- Hiring Lab's GitHub; the file in hand stands when the fetch fails or answers with something that is not the index.
try:
    _ip='cache/indeed_us_postings.csv'; _tmp=_ip+'.tmp'
    _r=subprocess.run(['curl','-sSL','-m','60','-o',_tmp,'https://raw.githubusercontent.com/hiring-lab/data/master/US/aggregate_job_postings_US.csv'],capture_output=True,text=True)
    _head=open(_tmp,encoding='utf-8',errors='replace').read(200) if os.path.exists(_tmp) else ''
    if _r.returncode==0 and _head.startswith('date,jobcountry,indeed_job_postings_index_SA'):
        os.replace(_tmp,_ip); _ln=open(_ip,encoding='utf-8',errors='replace').read().strip().splitlines(); say(f'indeed postings  {len(_ln)-1} rows, last {_ln[-1].split(",")[0]}')
    else:
        say('indeed postings  fetch failed (%s); the file in hand stands'%(_r.stderr.strip()[:80] or _head[:40]))
        if os.path.exists(_tmp): os.remove(_tmp)
except Exception as e: say(f'indeed postings  NOT refreshed ({e})')
# ---- the vacancy rate's two first-print series, straight from ALFRED's initial releases (the CLF16OV vintage table of
# collection 27 stops in 1996; output_type=4 gives every month's first print and its release day in one call) ----
for s in ['JTSJOL','CLF16OV']:
    if not due(s): SKIPPED.append('alfred_first_'+s); continue
    try:
        a=alfred_first(s,start='1940-01-01'); p_=f'cache/alfred_first_{s}.csv'
        old=pd.read_csv(p_,index_col=0) if os.path.exists(p_) else None
        if old is None or len(old)!=len(a): backup(p_); a.index.name='date'; a.to_csv(p_); say(f'alfred_first_{s}: {len(a)} months, through {a.index[-1].strftime("%Y-%m")} (released {a["release"].iloc[-1]})')
        else: say(f'alfred_first_{s}: unchanged (through {a.index[-1].strftime("%Y-%m")})')
        _PULLED[s]=a.index[-1].strftime('%Y-%m-%d')
    except Exception as e: say(f'alfred_first_{s}: NOT refreshed ({e})'); _FAILED.add(s)
# ---- the release calendars from the vintage tables (the first vintage carrying each month) ----
def release_calendar(series):
    rows=list(csv.reader(open(os.path.join(AL,series+'_all_vintages.csv')))); h=rows[0]
    vd=[pd.Timestamp(c.split('_')[-1]) for c in h[1:]]; dates=[pd.Timestamp(r[0]) for r in rows[1:]]
    out={}
    for i,m in enumerate(dates):
        for j in range(1,len(h)):
            v=rows[1+i][j]
            if v not in ('','.'): out[m]=(vd[j-1],float(v)); break
    return pd.DataFrame({'first_release':{m:a for m,(a,b) in out.items()},'first_print':{m:b for m,(a,b) in out.items()}}).sort_index()
for s in ['HOUST','UNRATE','JTSJOL']:
    c=release_calendar(s); p_=f'cache/relcal_{s}.csv'
    old=pd.read_csv(p_,index_col=0) if os.path.exists(p_) else None
    if old is None or len(old)!=len(c) or str(old.index[-1])[:10]!=c.index[-1].strftime('%Y-%m-%d'):
        backup(p_); c.to_csv(p_); say(f'relcal_{s}: {len(c)} months, through {c.index[-1].strftime("%Y-%m")} (released {c["first_release"].iloc[-1].date()})')
    else: say(f'relcal_{s}: unchanged (through {c.index[-1].strftime("%Y-%m")})')
# ---- the vacancy rate: after December 2000 the composite is JOLTS openings over the civilian labour force ----
vp=os.path.join(W,'lab','vac','vacancy_rate_PNZ_JOLTS.csv')
vt=pd.read_csv(vp,index_col=0,parse_dates=True).iloc[:,0]
jl=_safe_refresh('JTSJOL',os.path.join(W,'lab','vac','JTSJOL.csv'),start='2000-12-01'); cl=_safe_refresh('CLF16OV',os.path.join(W,'lab','vac','CLF16OV.csv'),start='1948-01-01')
jo=(jl/cl*100).dropna()
ov=[(m,float(vt[m]),float(jo[m])) for m in vt.index[-3:] if m in jo.index]
if ov and max(abs(a-b) for _,a,b in ov)<=1e-6:
    newm=jo[jo.index>vt.index[-1]].dropna()
    if len(newm):
        backup(vp); vt=pd.concat([vt,newm]).sort_index(); vt.rename('0').to_frame().to_csv(vp)
        say(f'vacancy: {len(newm)} JOLTS month(s) appended, through {vt.index[-1].date()}')
    else: say(f'vacancy: no new JOLTS month (through {vt.index[-1].date()})')
else: say(f'vacancy: openings/labour force does not reproduce the level file on recent months {ov}; NOT appended')
# ---- the S&P 500, daily closes ----
# v3.69 (22 September 2026, collection 302; the live-ops audit): TWO SOURCES. The chart feed gives the day's close at 4:15 PM; the official close
# (S&P Dow Jones Indices, FRED SP500) is posted the next morning. A new day is taken from either - the official figure
# where both have it - so a dead feed costs at most a morning, never the market channel; an existing day is corrected to
# the official figure, or to the feed's later value where FRED has none (the audit of 8 September 2026: a run at 4:20 PM
# had kept a preliminary 7753.74 for 3 September 2026 where the close was 7747.71).
# ---- v3.69 _sp_merge START ----
def _sp_merge(sp,ys,off):
    """sp: the file's closes; ys: the feed's settled closes; off: FRED SP500. Returns (sp, fixed, added)."""
    _E=pd.Series(dtype=float,index=pd.DatetimeIndex([]))   # v3.69b: an empty source must still carry a date index
    if not len(ys): ys=_E
    if not len(off): off=_E
    fixed=[]
    for t,v in off.items():
        if t in sp.index and abs(float(sp[t])-float(v))>0.005: fixed.append((t.date().isoformat(),round(float(sp[t]),2),round(float(v),2))); sp[t]=float(v)
    for t,v in ys.items():
        if t in sp.index and t not in off.index and abs(float(sp[t])-float(v))>0.005: fixed.append((t.date().isoformat(),round(float(sp[t]),2),round(float(v),2))); sp[t]=float(v)
    last=sp.index[-1]
    add=pd.concat([off[off.index>last].astype(float),ys[(ys.index>last)&~ys.index.isin(off.index)].astype(float)]).sort_index()
    add=add[~add.index.duplicated(keep='first')]
    if len(add): sp=pd.concat([sp,add]).sort_index()
    return sp,fixed,add
# ---- v3.69 _sp_merge END ----
sp_path=os.path.join(W,'lab','speed2','data','sp500_daily_yahoo.csv')
sp=pd.read_csv(sp_path,index_col=0,parse_dates=True).iloc[:,0]
from zoneinfo import ZoneInfo
# only settled closes: today's row is a live price until the market has closed (4:00 ET; the feed settles by 4:15)
_ny=datetime.datetime.now(ZoneInfo('America/New_York')); _cut=pd.Timestamp(_ny.date() if (_ny.hour,_ny.minute)>=(16,15) else _ny.date()-datetime.timedelta(days=1))
ys=pd.Series(dtype=float)
r=subprocess.run(['curl','-sSL','-m','40','-A','Mozilla/5.0','https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?range=3mo&interval=1d'],capture_output=True,text=True)
try:
    ch=json.loads(r.stdout)['chart']['result'][0]; ts=ch['timestamp']; cl=ch['indicators']['quote'][0]['close']
    ys=pd.Series({pd.Timestamp(datetime.datetime.fromtimestamp(t,datetime.timezone.utc).date()):c for t,c in zip(ts,cl) if c is not None}).sort_index()
    ys=ys[ys.index<=_cut]
except Exception as e: say(f'S&P 500: the chart feed failed ({e}); the official close (FRED SP500) stands in')
try:
    if sp.index[-1]>_cut: backup(sp_path); _dropped=sp.index[-1].date(); sp=sp[sp.index<=_cut]; sp.rename('close').to_frame().to_csv(sp_path); say(f'S&P 500: dropped the intraday row for {_dropped} (not a close)')
    try:
        off=fred('SP500',observation_start=(datetime.date.today()-datetime.timedelta(days=45)).isoformat()).dropna()
        off=off[off.index<=_cut]
    except Exception as e: say(f'S&P 500: FRED SP500 not read ({e})'); off=pd.Series(dtype=float)
    if not len(ys) and not len(off): raise RuntimeError('neither the chart feed nor FRED SP500 answered')
    _sp2,fixed,add=_sp_merge(sp.copy(),ys,off)
    if fixed or len(add): backup(sp_path); sp=_sp2; sp.rename('close').to_frame().to_csv(sp_path)
    if fixed: say(f'S&P 500: {len(fixed)} close(s) corrected to the settled figure: {fixed}')
    if len(add): say(f'S&P 500: {len(add)} day(s) appended, through {sp.index[-1].date()} ({int(add.index.isin(off.index).sum())} official, {int((~add.index.isin(off.index)).sum())} from the feed)')
    else: say(f'S&P 500: nothing new (through {sp.index[-1].date()})')
except Exception as e: say(f'S&P 500: update failed ({e})')
# ---- cache/objects.pkl: the Sahm gap on first prints rebuilt from the refreshed vintages; the insured-rate base extended ----
sys.path.insert(0,os.getcwd()); import shim
import bristow_rule_v3 as B
from mini import first_prints
o=pickle.load(open('cache/objects.pkl','rb')); g_old=o['sahm']; changed=False
g_new=B.sahm_gap(first_prints('UNRATE'))
common=g_old.index.intersection(g_new.index); dev=float((g_old[common]-g_new[common]).abs().max()) if len(common) else 0.0
# the stored series begins in 1949 (the reconstruction before ALFRED's vintages); only months after its end are added
if dev<=1e-6 and g_new.index[-1]>g_old.index[-1]:
    o['sahm']=pd.concat([g_old,g_new[g_new.index>g_old.index[-1]]]).sort_index(); changed=True; say(f'Sahm gap: extended to {o["sahm"].index[-1].date()} (history kept from {o["sahm"].index[0].date()})')
elif dev<=1e-6: say(f'Sahm gap: unchanged (through {g_old.index[-1].date()})')
else: say(f'Sahm gap: rebuilt series differs from the stored one by {dev:.4f} on the overlap; NOT replaced')
# the insured rate (current file) that the first prints overwrite: extend it with the weeks after its cached end, so a
# new week reaches the rule's insured-rate objects (the first-print file supplies the advance figure for those weeks)
iu_cur=pd.read_csv(os.path.join(D,'IURSA.csv')).iloc[:,:2]; iu_cur.columns=['d','v']; iu_cur['d']=pd.to_datetime(iu_cur['d']); iu_cur=iu_cur.set_index('d')['v'].astype(float).dropna()
base=o['iursa']; add=iu_cur[iu_cur.index>base.index.max()]
if len(add): o['iursa']=pd.concat([base,add]).sort_index(); changed=True; say(f'insured rate base: {len(add)} week(s) appended, through {o["iursa"].index.max().date()}')
else: say(f'insured rate base: unchanged (through {base.index.max().date()})')
if changed: backup('cache/objects.pkl'); pickle.dump(o,open('cache/objects.pkl','wb'))

# ---- v3.59 (20 September 2026; Anthony: "remove the leg channels from ... our autoupdating part of the website if they are no
# ---- longer in use"): the leg tier's refresh (v3.55-v3.56: sixty-odd FRED channels, the pink sheet, the non-FRED live sources,
# ---- the high-frequency channels, the legs M/A/P rebuild, the WARN scrape, the leg release calendar) is gone with the tier
# ---- (retired in v3.57, collection 260). Of those folders the current tool reads two files, for the damage index: the
# ---- unemployment rate as published today (186/data/UNRATE.csv) and its first prints (186/vintages/UNRATE_firstprint.csv).
C186=os.path.join(MNT,'186_realtime_channels_2026-09-15')
say('---- the damage index\'s unemployment rate ----')
try: refresh_series('UNRATE',os.path.join(C186,'data','UNRATE.csv'))
except Exception as e: say(f'UNRATE          NOT refreshed ({e})'); _FAILED.add('UNRATE')
for s in ['UNRATE']:
    p_=os.path.join(C186,'vintages',s+'_firstprint.csv')
    if not os.path.exists(p_): say(f'{s} firstprint: no file'); continue
    if not due(s): SKIPPED.append(s+' firstprint'); continue
    try:
        old=pd.read_csv(p_); old['date']=pd.to_datetime(old['date']); last=old['date'].max()
        a=alfred_first(s,start=(last+pd.DateOffset(months=1)).strftime('%Y-%m-%d')); a=a[a.index>last]
        if len(a):
            backup(p_); add=pd.DataFrame({'date':a.index.strftime('%Y-%m-%d'),'published':a['release'].values,'value':a['first'].values})
            pd.concat([old.assign(date=old['date'].dt.strftime('%Y-%m-%d')),add]).to_csv(p_,index=False)
            say(f'{s} firstprint: +{len(a)} month(s), through {a.index[-1].strftime("%Y-%m")} (released {a["release"].iloc[-1]})')
        else: say(f'{s} firstprint: unchanged (through {last.strftime("%Y-%m")})')
        _PULLED[s]=(a.index[-1] if len(a) else last).strftime('%Y-%m-%d')
    except Exception as e: say(f'{s} firstprint: NOT refreshed ({e})'); _FAILED.add(s)
if SKIPPED: say(f'left as they stand: {len(SKIPPED)} series/steps'+(' (FRED reports no change since they were last pulled; the rest not due by the calendar)' if _META_OK else ' (not due by the calendar; the day\'s first run pulled everything)'))
try:   # the stamps of the series pulled whole this run (their file now holds FRED's last observation), so the next run leaves them alone until FRED changes them
    _n_st=0
    for _s,_l in _PULLED.items():
        if _s in _FAILED or _s not in _KNOWN: continue
        if _l is None or not _KNOWN[_s][1] or _l>=_KNOWN[_s][1]: _SEEN[_s]=_KNOWN[_s][0]; _n_st+=1
    _META['ever']=sorted(set(_META.get('ever',[]))|set(_PULLED))
    json.dump(_META,open(_META_PATH,'w'))
    if _n_st or _FAILED: say(f'FRED stamps: {_n_st} series recorded as pulled'+(f'; {len(_FAILED)} failed and stay due: {", ".join(sorted(_FAILED))}' if _FAILED else ''))
except Exception as _e: say(f'FRED stamps not saved: {_e}')
try: json.dump(DAYSTART,open(_DS_PATH,'w'))
except Exception as _e: say(f'day-start snapshot not written: {_e}')
if FULL: open(FULL_MARK,'w').write(datetime.datetime.now().isoformat(timespec='seconds')); say('full refresh: every series pulled (the day\'s first run)')
open(os.path.join(COL,'live',f'refresh_{today}.txt'),'w').write('\n'.join(REPORT)+'\n')
if '--no-build' not in sys.argv:
    r=subprocess.run([sys.executable,'bhs_build.py'],capture_output=True,text=True)
    tail=[l for l in r.stdout.splitlines() if not l.endswith(' obs')][-24:]
    print('\n'.join(tail)); print('build rc',r.returncode)
    if r.returncode!=0: print(r.stderr[-1500:])
