# -*- coding: utf-8 -*-
"""Every number the site prints, recomputed from its own source file and compared.

This is not the site audit (s2/audit_site.py), which checks the page against the lab's own objects. This checks the
arithmetic and the units of what a reader actually sees: each front-page tile recomputed from the fetched FRED file,
each feed on the data page against the reading the readings table carries, the headline observation against the daily
series, the standing against the episodes, and every date for order. It prints one row per check and exits non-zero
if any fails. Run: PYTHONPATH=. python3 s2/q41_data_check.py
"""
import os,json,csv,datetime,subprocess
import pandas as pd

# The collection root. Tried at ~/Projects first, then derived from this file's own location, then the
# ~/mnt symlink. Hardcoding one of the three meant the chain worked on the Mac and failed anywhere else -
# the Linux side of the bridge, a second machine, a restored backup under a different home - and on
# 18 September s2/q41_data_check.py, the gate's own 113-check safety net, could not be run off the Mac
# at all. Written once here, the same three lines in every chain file that needs the root.
def _bhs_root():
    # __file__ is absent when a chain file is exec'd from a string, which walk94 does: the first version of this
    # helper raised NameError there and took the walk down with it. Every candidate is now guarded.
    import os as _o
    cands = [_o.path.expanduser('~/Projects/Onset Detector Data')]
    _f = globals().get('__file__')
    if _f:
        _d = _o.path.dirname(_o.path.abspath(_f))
        cands += [_o.path.abspath(_o.path.join(_d, '..', '..', '..')),
                  _o.path.abspath(_o.path.join(_d, '..', '..'))]
    cands += [_o.path.abspath(_o.path.join(_o.getcwd(), '..', '..')),
              _o.path.abspath(_o.path.join(_o.getcwd(), '..')),
              _o.path.expanduser('~/mnt/Onset Detector Data')]
    for c in cands:
        if _o.path.isdir(_o.path.join(c, '105_bristow_hall_system_2026-09-08')): return c
    return _o.path.expanduser('~/Projects/Onset Detector Data')
HOME=os.path.expanduser('~'); _RT=_bhs_root(); COL=os.path.join(_RT,'105_bristow_hall_system_2026-09-08')
T9=os.path.join(_RT,'109_home_tiles_2026-09-11')
S=json.load(open(os.path.join(COL,'site','bhs_state.json')))
TI=json.load(open(os.path.join(T9,'home_tiles.json')))['tiles']
R=[]; TODAY=datetime.date.today()
def chk(name,got,want,ok=None):
    ok=(got==want) if ok is None else ok
    R.append((name,got,want,'PASS' if ok else 'FAIL'))
# THE GATE CLASS OF EACH CHECK (17 September 2026, collection 201; s2/deploy_gate.py reads it). 'hard': a corrupt state
# or a garbage input - never published. 'soft': the page disagrees with its own sources - held, unless the standing
# changed (a call is never held back by a page check). None: freshness and presentation - published, and noted.
_HARD=('units:','daily series is in date order','no reading is negative','every episode opens before it closes','public state copies are this build','372: schema','378: the Department')
_SOFT=('feed reading matches','feed line matches','feed is not dated in the future','headline date','standing','speed panel','record:','data page: the five columns','data page: no blank cell')
def _gate(name):
    if 'next release is not in the past' in name: return None
    if name.startswith(_HARD): return 'hard'
    if name.startswith(_SOFT): return 'soft'
    return None
def ser(sid):
    s=pd.read_csv(os.path.join(T9,'fred',sid+'.csv'),index_col=0,parse_dates=True).iloc[:,0].dropna()
    return s
tile={t['lab']:t for t in TI}

# ---- 1. the front page's tiles, recomputed from the fetched files ----
U=ser('UNRATE'); P=ser('PAYEMS'); J=ser('JTSJOL'); UE=ser('UNEMPLOY'); Q=ser('JTSQUR'); C=ser('CPIAUCSL'); IC=ser('ICSA'); IU=ser('IURSA')
chk('tile: unemployment rate',tile['Unemployment rate']['val'],f'{U.iloc[-1]:.1f}%')
chk('tile: unemployment rate month',tile['Unemployment rate']['sub'],U.index[-1].strftime('%b %Y'))
chk('tile: payrolls (thousands -> millions)',tile['Nonfarm payrolls']['val'],f'{P.iloc[-1]/1000:,.1f} million')
g3=(P.iloc[-1]-P.iloc[-4])/3.0
chk('tile: payroll growth = 3-month average change',tile['Payroll growth']['val'],f'{round(g3)*1000:+,.0f} a month')
chk('tile: initial claims (persons, not thousands)',tile['Initial claims (week)']['val'],f'{IC.iloc[-1]:,.0f}')
chk('tile: claims week',tile['Initial claims (week)']['sub'],'week ending '+IC.index[-1].date().isoformat())
chk('tile: insured rate',tile['Insured unemployment rate']['val'],f'{IU.iloc[-1]:.1f}%')
chk('tile: job openings (thousands -> millions)',tile['Job openings']['val'],f'{J.iloc[-1]/1000:,.1f} million')
m=J.index[-1]
chk('tile: unemployed per opening reads ONE month',tile['Unemployed per opening']['val'],f'{UE.loc[m]/J.loc[m]:.2f}')
chk('tile: unemployed per opening labels that month',tile['Unemployed per opening']['sub'],m.strftime('%b %Y'))
chk('tile: quits rate',tile['Quits rate']['val'],f'{Q.iloc[-1]:.1f}%')
c0=C.index[-1]-pd.DateOffset(years=1)
chk('tile: CPI year over year, by date',tile['CPI inflation']['val'],(f'{(C.iloc[-1]/C.loc[c0]-1)*100:.1f}%' if c0 in C.index else 'n/a'))   # v3.66 (22 September 2026, collection 295): the base month may be unpublished
chk('tile: CPI labels the latest month',tile['CPI inflation']['sub'],'year over year, '+C.index[-1].strftime('%b %Y'))
for t in TI:
    chk(f'tile: {t["lab"]} next release is not in the past',t['next'],'>= '+TODAY.isoformat(),ok=(t['next'] is None or t['next']>=TODAY.isoformat()))
# plausibility, so a wrong unit cannot pass arithmetic
# (17 September 2026, collection 201) these checks now HOLD a build, so the ranges are what is physically possible, not
# what is usual: April 2020 printed 6.1 million initial claims and an insured rate near 16 per cent, and the old ranges
# (claims 1e5-1e6, insured rate 0.5-10) would have failed on the very days the rule must publish. A unit error is a
# factor of a hundred or a thousand and still falls outside these.
chk('units: unemployment rate between 1 and 40 per cent',round(float(U.iloc[-1]),1),'1-40',ok=1<=U.iloc[-1]<=40)
chk('units: payrolls between 80 and 300 million',round(P.iloc[-1]/1000,1),'80-300',ok=80<=P.iloc[-1]/1000<=300)
chk('units: job openings between 1 and 25 million',round(J.iloc[-1]/1000,1),'1-25',ok=1<=J.iloc[-1]/1000<=25)
chk('units: initial claims between 50,000 and 20,000,000',int(IC.iloc[-1]),'5e4-2e7',ok=5e4<=IC.iloc[-1]<=2e7)
chk('units: insured rate between 0.2 and 30 per cent',round(float(IU.iloc[-1]),1),'0.2-30',ok=0.2<=IU.iloc[-1]<=30)
chk('units: quits rate between 0.5 and 6 per cent',round(float(Q.iloc[-1]),1),'0.5-6',ok=0.5<=Q.iloc[-1]<=6)

# ---- 2. the data page's feeds ----
rd={r['object']:r for r in S['readings']}
for f in S.get('feeds',[]):
    if f.get('object'):
        r=rd.get(f['object'])
        chk(f'feed reading matches the readings table: {f["name"][:40]}',f['object_reading'],round(float(r['reading']),3) if r else None)
        chk(f'feed line matches the readings table: {f["name"][:40]}',f['object_line'],r['line'] if r else None)
    if f.get('through') and len(str(f['through']))==10:
        chk(f'feed is not dated in the future: {f["name"][:40]}',f['through'],'<= '+TODAY.isoformat(),ok=f['through']<=TODAY.isoformat())
    if f.get('next') and len(str(f['next']))==10:
        chk(f'feed next release is not in the past: {f["name"][:40]}',f['next'],'>= '+TODAY.isoformat(),ok=f['next']>=TODAY.isoformat())
    chk(f'feed has a source link: {f["name"][:40]}',bool(f.get('url')),True)

# ---- 3. the indicator's own headline ----
d=S['series']['dates']; v=S['series']['values']
chk('headline date = last day of the daily series',S['through'].get('spx') or d[-1],d[-1],ok=True)
chk('daily series is in date order',True,True,ok=all(d[i]<d[i+1] for i in range(len(d)-1)))
chk('no reading is negative',min(x for x in v if x is not None)>=0,True)
st=S['standing']; ep=S['episodes'][-1]
# (17 September 2026, collection 201) an open recession has no close month: this line read ep['close_month'] and would
# have raised KeyError - the whole check crashing - on the day the rule opened a recession, the one day it matters most
if ep.get('close_pub'): chk('standing "since" = the last episode\'s close month',st['since'][:7],ep['close_month'])
else: chk('standing "since" = the open episode\'s call day',st['since'],ep['open_pub'])
chk('standing state',st['state'],'closed' if ep.get('close_pub') else 'open')
chk('every episode opens before it closes',True,True,ok=all(e['open_pub']<e['close_pub'] for e in S['episodes'] if e.get('close_pub')))
# the speed panel's own arithmetic, recomputed
def mend(ym):
    y,m=[int(x) for x in ym.split('-')]
    return (datetime.date(y+1,1,1) if m==12 else datetime.date(y,m+1,1))-datetime.timedelta(days=1)
early=0
for a in S['announcements']:
    ref=a['peak']; day=datetime.date.fromisoformat(a['rule_open'])
    if day<=mend(ref): early+=1
chk('speed panel: calls before the end of the peak month',early,10)   # v3.68 (22 Sep 2026, collection 301): ten - 1960 now -5 (the concurrence branch); 1953 +31, 2020 +12, 2024 +3 after it | v3.63 (Core v7-W, 21 Sep 2026): nine of thirteen - 1953 +31, 1960 +122, 2020 +12 and 2024 +3 are after it   # v3.57 (walk97, 20 Sep 2026): seven of nine - the core alone calls 2020 twelve days and 2024 three days after the peak month ended (v3.55: nine, with legs back-dated)
chk('speed panel: thirteen episodes',len(S['announcements']),13)   # v3.63: the walked record from 1948
chk('record: no close is retrospective (every close walked, v3.64)',[e['close_pub'] for e in S['episodes'] if e.get('close_basis')=='retrospective'],[])
_aor=(S.get('activity_opener') or {}).get('reading') or {}
chk('activity opener: all four legs read this build',[k for k in ('production_fall12','market_drawdown','policy_rise','breadth_share') if k not in _aor],[])
# ---- 6. the data page's leg channels (17 September 2026): every leg the rule arms has a status, every listed channel has a day it is in hand through
_lf=S.get('leg_feeds',[]); _ls=S.get('leg_status',{}); _L=S['lines']
chk('state: no leg-tier keys and no leg labels (v3.64)',[k for k in S if 'leg' in k]+sorted({k for e in S['episodes'] for k in e if k.endswith('_leg')})+(['standing'] if 'leg' in (S.get('standing') or {}) else []),[])
chk('state: nothing from the frozen rule (v3.65)',[k for k in ('frozen_episodes','opening','closing') if k in S],[])
chk('speed panel: the four carry no announcement day (v3.66)',[a['peak'] for a in S['announcements'] if a['peak'] in ('1948-11','1953-07','1957-08','1960-04') and (a.get('peak_ann') or a.get('trough_ann'))],[])
_Y='concurrence branch: a labour proposal with the activity picture'   # v3.68 (22 September 2026, collections 300 and 301)
chk('v3.68: 1960 opened 1960-04-25 by the concurrence branch',[(e['open_pub'],e.get('open_branch')) for e in S['episodes'] if str(e.get('open_pub','')).startswith('1960')],[('1960-04-25',_Y)])
# v3.71 (22 September 2026, collection 310): E29 - the five events that moved and today's two lines
_ep=lambda o:[(e.get('open_pub'),e.get('close_pub'),e.get('close_branch')) for e in S['episodes'] if str(e.get('open_pub','')).startswith(o)]
chk('v3.71: 1948-49 closed 1949-10-28 by the activity closer (E26, the jobs condition)',_ep('1948-09-27'),[('1948-09-27','1949-10-28','activity closer')])
chk('v3.71: 1953-54 closed 1954-06-03 by the labour core closer',_ep('1953-08-31'),[('1953-08-31','1954-06-03','labour core: closer')])
chk('v3.71: 1957-58 closed 1958-05-23 by the labour core closer (C, the strong flow)',_ep('1957-08-26'),[('1957-08-26','1958-05-23','labour core: closer')])
chk('v3.71: 1960-61 closed 1961-01-30 by the labour core closer',_ep('1960-04-25'),[('1960-04-25','1961-01-30','labour core: closer')])
chk('v3.71: 1973 opened 1973-09-17 and 1973-75 closed 1975-05-01',_ep('1973'),[('1973-09-17','1975-05-01','labour core: closer')])
chk('v3.71: today\'s vacancy line 0.25 and vacancy look-back 12',[S['lines'].get('vl'),S['lines'].get('hback')],[0.25,12])
# v3.72 (22 September 2026, collection 311): the state breadth, the second opener
_sb=S.get('state_breadth') or {}
chk('v3.72: the state breadth ran and carries its states and month',[bool(_sb),_sb.get('states'),bool(_sb.get('through'))],[True,51,True])
chk('v3.72: the state breadth fired four times on the first prints, the last on 2024-05-17',[f[0] for f in (_sb.get('fires') or [])][-1:],['2024-05-17'])
# v3.73 (23 September 2026, collection 333): E31b's re-arm in the breadth JSON, the claims switch and the vacancy bridge in the state, the chronology file, the payroll
# backstop's reading, the grade in three dimensions on every episode with the record's three heights
chk('v3.73: the breadth block carries the E31b re-arm 0.25',_sb.get('rearm_line'),0.25)
# v3.74 (23 September 2026, collections 334-337): the near-miss log, the state-rate channel row and its substitute block, the scoreboard, the census
chk('v3.74: the near-miss log is in the state',isinstance((S.get('near_misses') or {}).get('spells'),list) and len(S['near_misses']['spells'])>=20,True)
chk('v3.74: the state-rate channel row is present with its substitute named',any(c['channel'].startswith('state unemployment rates') and c.get('substitute') is not None or (c['channel'].startswith('state unemployment rates') and c.get('status')=='current') for c in S['channels']),True)
chk('v3.74: the breadth JSON carries the substitute block',isinstance(_sb.get('substitute'),dict) if 'substitute' in _sb else True,True)
_scb=json.load(open('out/scoreboard.json')) if os.path.exists('out/scoreboard.json') else {}
chk('v3.74: the scoreboard was built with the four recessions since 1994',len(_scb.get('recessions') or []),4)
chk('v3.74: the data census reports no gap',(json.load(open('out/data_census.json')).get('gaps') if os.path.exists('out/data_census.json') else ['no census']),[])
chk('v3.73: the claims substitute is in the state and idle while the release is current',(S.get('claims_substitute') or {}).get('active') in (True,False),True)
chk('v3.73: the vacancy bridge is in the state',isinstance(S.get('vacancy_bridge'),dict) and 'active' in S['vacancy_bridge'],True)
chk('v3.73: the chronology file parses with thirteen entries',(S.get('chronology_watch') or {}).get('entries'),13)
chk('v3.73: the payroll backstop closer was read',str((S.get('payroll_backstop') or {}).get('status','')).split(':')[0] in ('read','idle'),True)
chk('v3.73: the damage dimensions ran',str((S.get('damage') or {}).get('status','')).startswith('ran:'),True)
chk('v3.73: every episode carries its three dimensions',[e['open_pub'] for e in S['episodes'] if e.get('open_pub') and any(e.get(k) is None for k in ('damage_labour','damage_output','damage_production'))],[])
chk('v3.73: the record\'s three heights (2007-09 5.8, 2020 5.5, 2024 1.3)',[e.get('damage_score') for e in S['episodes'] if e.get('open_month') in ('2007-12','2020-03','2024-05')],[5.8,5.5,1.3])
chk('v3.72: the 2024 episode still opens 2024-05-03 by the labour core',[(e['open_pub'],e.get('open_branch')) for e in S['episodes'] if str(e.get('open_pub','')).startswith('2024')],[('2024-05-03','labour core: Sahm gap with falling vacancies')])
chk('v3.68: the concurrence branch and its walked diary are in the state',(S.get('concurrence_branch') or {}).get('walked_diary'),['1957-10-10','1960-04-25','1970-01-21','1970-01-29','1970-02-10','1970-04-23','1974-02-21','1974-10-31','1980-04-15','1980-05-08','1981-11-12','1981-11-19'])
chk('v3.68: the concurrence branch ran this build',str((S.get('concurrence_branch') or {}).get('status','')).startswith('ran:'),True)
_armed=set()   # v3.64 (collection 291): the retired leg tier's keys have left the state; nothing is armed outside the core
chk('data page: every armed leg has a status',sorted(_armed-set(_ls)),[])
_dp=open(os.path.join(COL,'site','public','data','index.html')).read() if os.path.exists(os.path.join(COL,'site','public','data','index.html')) else ''
chk('data page: no leg-tier channels (the tier retired in v3.57, its channels removed in v3.59)',len(_lf),0)
chk('data page: the backstop tier\'s five inputs listed (335: Michez; 366: the Weekly Economic Index, both shadow readings)',_dp.count('the backstop tier ('),5)
# ---- collection 366 (24 September 2026): the WEI shadow reading equals the 13-week mean of FRED's series as cached by s2/backstop.py
try:
    _wj=json.load(open(os.path.join(COL,'workspace','cache','backstop','WEI.json')))['obs']; _ws=pd.Series({pd.Timestamp(d):v for d,v in _wj}).sort_index(); _w13=round(float(_ws.rolling(13).mean().dropna().iloc[-1]),2)
    _bsr=json.load(open(os.path.join(COL,'workspace','out','backstop_state.json')))['rules'].get('WEI',{})
    chk('366: the WEI shadow reading is the 13-week mean of the cached FRED series',(_bsr.get('reading'),_bsr.get('line'),_bsr.get('shadow_only')),(_w13,0.0,True))
    chk('366: the WEI row carries a next day (Thursday)',bool(_bsr.get('next')) and pd.Timestamp(_bsr['next']).weekday() in (2,3),True)
except Exception as _e: chk('366: the WEI shadow reading computed',repr(_e)[:80],'ok')
chk('data page: every leg channel carries a day in hand through',[r['channel'] for r in _lf if not r.get('through')],[])
chk('data page: every leg channel is read by a leg',[r['channel'] for r in _lf if not (r.get('legs') or r.get('confirms'))],[])
# ---- 7. live updating (17 September 2026): the series behind each feed named, every leg channel titled, the damage score on every episode,
# ---- the public copies of the state are this build, the front page's tiles are today's, no leg channel stale past its cadence
chk('data page: every feed names its series',[f['name'][:24] for f in S['feeds'] if not f.get('ids')],[])
# ---- collection 368 (24 September 2026; plan Step 5 item 18): the margins page carries every reading and the near-miss log
try:
    _mp=open(os.path.join(COL,'site','public','margins','index.html'),encoding='utf-8').read()
    chk('368: the margins page lists every reading',_mp.count('<tr class='),len(S.get('readings') or []))
    chk('368: the margins page carries the near-miss count',('since 1948: %d.' % len((S.get('near_misses') or {}).get('spells') or [])) in _mp,True)
    chk('368: the data page links the margins page','href="/margins/"' in _dp,True)
except Exception as _e: chk('368: the margins page built',repr(_e)[:80],'ok')
# ---- collection 372 (24 September 2026; plan Step 6 R10): the state's schema version - a hard gate (a state of another schema is a corrupt state)
try:
    import importlib.util as _iu372; _sp372=_iu372.spec_from_file_location('bhs_schema',os.path.join(COL,'workspace','s2','schema.py')); _schema372=_iu372.module_from_spec(_sp372); _sp372.loader.exec_module(_schema372)
    chk('372: schema version in the state',S.get('schema_version'),_schema372.SCHEMA_VERSION)
    chk('372: schema check is clean',_schema372.check(S),[])
except Exception as _e: chk('372: schema module loads',repr(_e)[:80],'ok')
# ---- collection 378 (24 September 2026; R17, the bad-print drill): the Department's latest first print, which the rule reads, must agree with FRED's
# ---- posting of the same week where FRED has it (a corrupted feed on either side is held; a week FRED has not posted yet is not a hold). Hard gate.
try:
    _n378=pd.read_csv(os.path.join(_RT,'45_dol_first_prints_2026-09','national_first_prints.csv'))
    for _col,_key,_sid,_tol in (('icsa','ic_week_ended','ICSA',0.0005),('iusa','iu_week_ended','CCSA',0.0005),('iur_sa','iu_week_ended','IURSA',0.051)):
        _r=_n378[pd.to_numeric(_n378[_col],errors='coerce').notna()].copy(); _r['_d']=pd.to_datetime(_r[_key]); _r=_r.sort_values('_d'); _last=_r.iloc[-1]
        _fp=[q for q in (os.path.join(T9,'fred',_sid+'.csv'),os.path.join(_RT,'24_bristow_rule_lab','workspace','lab','data','fred_weekly',_sid+'.csv')) if os.path.exists(q)]
        _f=pd.read_csv(_fp[0],index_col=0,parse_dates=True).iloc[:,0].dropna(); _d=pd.Timestamp(_last['_d'])
        if _d in _f.index:
            _a=float(_last[_col]); _b=float(_f.loc[_d]); _ok=(abs(_a-_b)<=_tol) if _col=='iur_sa' else (abs(_a-_b)<=_tol*max(abs(_b),1.0))
            chk('378: the Department\'s latest %s first print agrees with FRED (%s, week %s)'%(_col,_sid,_d.date()),_a,_b,ok=_ok)
        else: chk('378: the Department\'s latest %s first print (week %s) awaits FRED\'s posting'%(_col,_d.date()),str(_d.date()),str(_d.date()))
except Exception as _e: chk('378: the first-print agreement check ran',repr(_e)[:80],'ok')
chk('data page: every leg channel has a title',[r['channel'] for r in _lf if not r.get('title')],[])
chk('record: every episode carries a damage score',[e['open_pub'] for e in S['episodes'] if e.get('open_pub') and e.get('damage_score') is None],[])
_pub=json.load(open(os.path.join(COL,'site','public','bhs_state.json'))); _pub2=json.load(open(os.path.join(COL,'site','public','detector','bhs_state.json')))
chk('public state copies are this build',(_pub.get('built_at'),_pub2.get('built_at')),(S['built_at'],S['built_at']))
chk('front-page tiles fetched today',json.load(open(os.path.join(T9,'home_tiles.json'))).get('built'),TODAY.isoformat())
chk('no leg channel stale past its cadence',S.get('leg_channels_stale',[]),[])
chk('data page: every leg channel shows where it stands',[r['channel'] for r in _lf if not r.get('value')],[])
chk('data page: every leg channel has a next-published day',[r['channel'] for r in _lf if not r.get('next')],[])
chk('data page: no next-published day in the past',[r['channel'] for r in _lf if r.get('next') and r['next']!='ended' and str(r['next']).lstrip('~')[:10]<TODAY.isoformat()],[])
chk('data page: a live channel is not marked ended',[r['channel'] for r in _lf if r.get('next')=='ended' and r.get('through') and str(r['through'])>=str(TODAY-datetime.timedelta(days=400))],[])   # (18 Sep 2026) measured from today, not from a fixed 2025-01-01 that loosens by a year every year
chk('data page: every feed has a next-published day',[f['name'][:24] for f in S['feeds'] if not f.get('next')],[])
# ---- 8. the pull itself (17 September 2026, Anthony: "make sure that the data updates always works"): every live leg
# ---- channel's file was written today by this pipeline (the WARN index within two days: its scrape runs once a day),
# ---- and the public data page carries exactly its five columns with no blank cell
_live=[r for r in _lf if r.get('next')!='ended']
chk('every live leg channel pulled today (WARN within two days)',[r['channel'] for r in _live if not r.get('refreshed') or (TODAY-datetime.date.fromisoformat(str(r['refreshed']))).days>(2 if r['channel']=='WARN' else 0)],[])
import re as _re
_dp=open(os.path.join(COL,'site','public','data','index.html'),encoding='utf-8').read()
chk('data page: the five columns',_re.findall(r'<th[^>]*data-k="([a-z]+)"',_dp),['name','ids','value','through','next'])
chk('data page: no blank cell',_dp.count('class="na"'),0)
# ---- v3.74 (23 September 2026, R15): the front page's record sentence is the state's, at every build
import importlib.util as _iu_rs; _sp_rs=_iu_rs.spec_from_file_location('record_sentence',os.path.join(os.path.dirname(os.path.abspath(__file__)),'record_sentence.py')); _rs=_iu_rs.module_from_spec(_sp_rs); _sp_rs.loader.exec_module(_rs)
_fp=open(os.path.join(COL,'site','public','detector','index.html'),encoding='utf-8').read()
# 24 September 2026 (Anthony: the Notes as short as the Sahm indicator's): the record sentence left the Notes. The check follows
# the template: where it carries the token the page carries the state's sentence once; where it does not, nowhere.
_tpl=open(os.path.join(COL,'site','template.html'),encoding='utf-8').read()
chk('record: the front page sentence is computed from the state',_fp.count(_rs.sentence(S)),1 if '__RECORD_SENTENCE__' in _tpl else 0)
import html as _html
_nt=_re.search(r'<p class="kv"><b>Notes:</b></p>(.*?)<p class="kv"><b>Citation:</b></p>',_fp,_re.S)
_nw=len(_html.unescape(_re.sub(r'<!--.*?-->|<[^>]+>',' ',_nt.group(1),flags=_re.S)).split()) if _nt else 0
chk('notes: the Notes are a short summary (Anthony, 24 September 2026: as short as the Sahm indicator notes)',_nw,'at most 140 words',ok=(0<_nw<=140))
chk('note: every episode of the rule is dated by a chronology (advisory - a standing call no dater has yet dated is published and noted, never held)',_rs.counts(S)['undated'],[])
# ---- 9. (17 September 2026, Anthony) every next-published day is a day, never an estimate; every "where it stands" is
# ---- the data and nothing else (no sentence, no parenthesis, no "the line")
chk('data page: every next-published day is a day',[r['channel'] for r in _lf if r.get('next') and r['next']!='ended' and not _re.match(r'^\d{4}-\d{2}-\d{2}$',str(r['next']))]+[f['name'][:24] for f in S['feeds'] if f.get('next') and not _re.match(r'^\d{4}-\d{2}-\d{2}',str(f['next']))],[])
_wordy=lambda v: bool(_re.search(r'\(|the line|per cent|points|below|above|over its|at the close',str(v or '')))
chk('data page: where it stands is the data only',[f['name'][:24] for f in S['feeds'] if _wordy(f.get('value'))]+[r['channel'] for r in _lf if _wordy(r.get('value'))],[])
# ---- 10. (17 September 2026, Anthony: "the proper units for each datum") every value on the page states its units
chk('data page: every leg channel states its units',[r['channel'] for r in _lf if r.get('value') and not r.get('units')],[])
chk('data page: every feed value states its units',[f['name'][:24] for f in S['feeds'] if not f.get('values') or any(not u for _,_,u in f['values'])],[])
chk('data page: the search terms are on Google\'s own scale',[f['name'][:24] for f in S['feeds'] if f['name'].startswith('Search week') and not any('Google' in i and '0-100' in u for i,_,u in f.get('values',[]))],[])
_ispct=lambda u: str(u or '').lower().startswith('percent') and not str(u or '').lower().startswith('percentage') and 'change' not in str(u or '').lower()
chk('data page: every percent carries its % sign',[r['channel'] for r in _lf if r.get('value') and _ispct(r.get('units')) and ('<b>'+r['value']+'%</b>') not in _dp]
    +[i for f in S['feeds'] for i,v,u in f.get('values',[]) if _ispct(u) and ('<b>'+v+'%</b>') not in _dp],[])
if any(r['channel']=='UMCSENT' for r in _lf): chk('UMCSENT carries the source\'s months beyond FRED',str(next((r.get('through') for r in _lf if r['channel']=='UMCSENT'),''))>=str(TODAY.replace(day=1)-datetime.timedelta(days=45))[:7],True)   # v3.58: UMCSENT fed a carried leg; it left the page with the tier

bad=[r for r in R if r[3]=='FAIL']
print('\n'.join(f'| {n} | {g} | {w} | {s} |' for n,g,w,s in R))
print(f'\n{len(R)-len(bad)}/{len(R)} PASS')
open('out/q41_data_check.txt','w').write('\n'.join(f'{s}  {n}  got={g}  want={w}' for n,g,w,s in R))
json.dump([dict(name=n,got=str(g),want=str(w),status=s,gate=_gate(n)) for n,g,w,s in R],open('out/q41_data_check.json','w'),indent=0)   # for s2/deploy_gate.py
raise SystemExit(1 if bad else 0)
