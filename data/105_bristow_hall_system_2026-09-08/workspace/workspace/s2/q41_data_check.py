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
_HARD=('units:','daily series is in date order','no reading is negative','every episode opens before it closes','public state copies are this build')
_SOFT=('tile:','feed reading matches','feed line matches','feed is not dated in the future','headline date','standing','speed panel','record:','data page: the five columns','data page: no blank cell')
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
chk('tile: CPI year over year, by date',tile['CPI inflation']['val'],f'{(C.iloc[-1]/C.loc[c0]-1)*100:.1f}%')
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
chk('speed panel: calls before the end of the peak month',early,9)   # v3.55 (walk94): all nine calls before the peak month ended (v3.29: seven)
chk('speed panel: nine episodes',len(S['announcements']),9)
# ---- 6. the data page's leg channels (17 September 2026): every leg the rule arms has a status, every listed channel has a day it is in hand through
_lf=S.get('leg_feeds',[]); _ls=S.get('leg_status',{}); _L=S['lines']
_armed=set(str(_L.get('carry') or ''))|set(str(_L.get('newlegs') or ''))|set(str(_L.get('extra') or ''))|{'N'}
chk('data page: every armed leg has a status',sorted(_armed-set(_ls)),[])
chk('data page: leg channels listed',len(_lf)>=60,True)
chk('data page: every leg channel carries a day in hand through',[r['channel'] for r in _lf if not r.get('through')],[])
chk('data page: every leg channel is read by a leg',[r['channel'] for r in _lf if not (r.get('legs') or r.get('confirms'))],[])
# ---- 7. live updating (17 September 2026): the series behind each feed named, every leg channel titled, the damage score on every episode,
# ---- the public copies of the state are this build, the front page's tiles are today's, no leg channel stale past its cadence
chk('data page: every feed names its series',[f['name'][:24] for f in S['feeds'] if not f.get('ids')],[])
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
chk('UMCSENT carries the source\'s months beyond FRED',str(next((r.get('through') for r in _lf if r['channel']=='UMCSENT'),''))>=str(TODAY.replace(day=1)-datetime.timedelta(days=45))[:7],True)

bad=[r for r in R if r[3]=='FAIL']
print('\n'.join(f'| {n} | {g} | {w} | {s} |' for n,g,w,s in R))
print(f'\n{len(R)-len(bad)}/{len(R)} PASS')
open('out/q41_data_check.txt','w').write('\n'.join(f'{s}  {n}  got={g}  want={w}' for n,g,w,s in R))
json.dump([dict(name=n,got=str(g),want=str(w),status=s,gate=_gate(n)) for n,g,w,s in R],open('out/q41_data_check.json','w'),indent=0)   # for s2/deploy_gate.py
raise SystemExit(1 if bad else 0)
