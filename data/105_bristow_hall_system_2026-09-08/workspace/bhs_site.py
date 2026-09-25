"""THE BRISTOW HALL SYSTEM — build the page. Injects site/bhs_state.json into site/template.html and writes
site/index.html (the copy the artifact publisher wraps in its own document; downloads there open on the page) and
site/public/index.html (a complete document for Cloudflare Pages; downloads there save files). Run from the
collection 105 workspace after bhs_build.py:
    python3 bhs_site.py
Then, if a Cloudflare token is configured, deploy.sh publishes the site folder."""
import os, json
HOME=os.path.expanduser('~'); COL=os.path.join(HOME,'mnt','Onset Detector Data','105_bristow_hall_system_2026-09-08')
SITE=os.path.join(COL,'site')
state=json.load(open(os.path.join(SITE,'bhs_state.json')))
# 25 Sep 2026 (ops-0924; audit-0924, Anthony 'FIX THIS'): the state the site serves says what the data page says - each feed's
# publisher page and exact cadence (s2/feed_publishers.py), no Yahoo or FRED address where another publishes, no approximate clock
import importlib.util as _iu_fp0; _sp_fp0=_iu_fp0.spec_from_file_location('feed_publishers',os.path.join(os.path.dirname(os.path.abspath(__file__)),'s2','feed_publishers.py')); _fp0=_iu_fp0.module_from_spec(_sp_fp0); _sp_fp0.loader.exec_module(_fp0)
state['feeds']=[_fp0.normalize(dict(_f)) for _f in state.get('feeds') or []]
# R10 (24 September 2026, collection 372): the renderer refuses a state of any schema but the one it renders (s2/schema.py); in the cloud
# this line is not guarded by `|| true`, so a refusal fails the run and the ops layer holds the site as it was - nothing wrong is published.
import importlib.util as _iu372; _sp372=_iu372.spec_from_file_location('bhs_schema',os.path.join(os.path.dirname(os.path.abspath(__file__)),'s2','schema.py')); _schema372=_iu372.module_from_spec(_sp372); _sp372.loader.exec_module(_schema372)
_pr372=_schema372.check(state)
if _pr372: raise SystemExit('R10: bhs_site refuses to render: the state is not schema %d: %s'%(_schema372.SCHEMA_VERSION,'; '.join(_pr372)))
t=open(os.path.join(COL,'site','template.html'),encoding='utf-8').read()
assert t.count('__STATE__')==1 and t.count('__SITE__')==1, 'template must contain exactly one __STATE__ and one __SITE__ token'
# v3.74 (23 September 2026, R15): the front page's record sentence is computed from the state at every build, never fixed text
# 24 September 2026 (Anthony: the Notes as short as the Sahm indicator's): the record sentence left the Notes, so the token is
# optional; where a template carries it, the sentence is still the state's (R15)
assert t.count('__RECORD_SENTENCE__')<=1, 'template must contain at most one __RECORD_SENTENCE__ token'
import importlib.util as _iu_rs; _sp_rs=_iu_rs.spec_from_file_location('record_sentence',os.path.join(os.path.dirname(os.path.abspath(__file__)),'s2','record_sentence.py')); _rs=_iu_rs.module_from_spec(_sp_rs); _sp_rs.loader.exec_module(_rs)
t=t.replace('__RECORD_SENTENCE__',_rs.sentence(state))
page=t.replace('__STATE__',json.dumps(state,separators=(',',':')))
# the artifact publisher wraps the file in a document skeleton; a web server does not, so the standalone copy gets one
head,body=page.split('</style>',1); head=head+'</style>'
full='<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n'+head+'\n</head>\n<body>\n'+body+'\n</body>\n</html>\n'
os.makedirs(os.path.join(SITE,'public'),exist_ok=True)
open(os.path.join(SITE,'index.html'),'w',encoding='utf-8').write(page.replace('__SITE__','false'))          # for the artifact publisher
os.makedirs(os.path.join(SITE,'public','detector'),exist_ok=True)
open(os.path.join(SITE,'public','detector','index.html'),'w',encoding='utf-8').write(full.replace('__SITE__','true'))  # the indicator, for Cloudflare Pages
json.dump(state,open(os.path.join(SITE,'public','bhs_state.json'),'w'))                                     # the data beside the page
json.dump(state,open(os.path.join(SITE,'public','detector','bhs_state.json'),'w'))

# ---- the home page: the programme's front door, carrying only what the programme publishes today ----
_sp=[(d,v) for d,v in zip(state['series']['dates'],state['series']['values'])] if 'series' in state else []
if not _sp:
    _S=state.get('daily') or {}; _sp=[(d,v) for d,v in zip(_S.get('dates',[]),_S.get('values',[]))]
_sp=[p for p in _sp if p[0]>='1975-01-01']
_last=_sp[-1] if _sp else (None,None)
_step=max(1,len(_sp)//420); _sp=_sp[::_step]
if _sp and _last[0]!=_sp[-1][0]: _sp.append(_last)   # keep the newest observation whatever the decimation
_bands=[]
for _r in state.get('nber',[]):
    try:
        _y,_m=[int(x) for x in _r['trough'].split('-')]; _e=(f'{_y+1}-01-01' if _m==12 else f'{_y}-{_m+1:02d}-01')
        _bands.append([_r['peak']+'-01',_e])
    except Exception: pass
for _e in state.get('episodes',[]):
    if _e.get('open_month') and _e.get('close_month'): _bands.append([_e['open_month']+'-01',_e['close_month']+'-28'])
_tp=os.path.join(HOME,'mnt','Onset Detector Data','109_home_tiles_2026-09-11','home_tiles.json')
_tiles=(json.load(open(_tp))['tiles'] if os.path.exists(_tp) else [])
_tiles_built=(json.load(open(_tp)).get('built') if os.path.exists(_tp) else '') or ''
home=dict(standing=state['standing'],tiles=_tiles,
          last_date=_last[0],last_value=_last[1],
          spark=dict(dates=[p[0] for p in _sp],values=[p[1] for p in _sp]),bands=_bands)
_h=open(os.path.join(COL,'site','template_home.html'),encoding='utf-8').read()
assert _h.count('__HOME__')==1, 'the home template needs exactly one __HOME__ token'
_hh,_hb=_h.replace('__HOME__',json.dumps(home,separators=(',',':'))).split('</style>',1)
_full_home='<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n'+_hh+'</style>\n</head>\n<body>\n'+_hb+'\n</body>\n</html>\n'
open(os.path.join(SITE,'public','index.html'),'w',encoding='utf-8').write(_full_home)
print('home built: standing',state['standing']['state'],'| public/index.html',len(_full_home),'bytes')
print('site built:',state['built'],'| standing',state['standing']['state'],'since',state['standing']['since'],'| public/detector/index.html',len(full),'bytes')

# ---- the pages the masthead names but the programme has not published yet ----
# Every function in the top bar is clickable: each unbuilt one gets its own page, in the site's own dress,
# saying plainly what it will be and what it waits on. They are generated from the home template, so the
# masthead, the nav and the footer can never drift between the front door and these.
import re as _re2

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
_style=_re2.search(r'<style>.*?</style>',_h,_re2.S).group(0)
_header=_re2.search(r'<header class="bh">.*?</header>',_h,_re2.S).group(0)
_footer=_re2.search(r'<div class="foot">.*?</div></div>',_h,_re2.S).group(0)
_STUBS=[
 ('disturbance','Real-Time National Disturbance Indicator',
  'The national labor disturbance beneath a call: what moved, when it moved, and how far it went.',
  'The detector reads the same public releases as the recession indicator and asks a narrower question — not whether a recession has opened, but whether the labour market has been disturbed at all, and in which of its parts. It waits on the disturbance measure being written down and walked forward on the same terms as the rule: every clause fixed before it is scored, every number read as it stood on its release day.'),
 ('state-onset','Real-Time State Recession Indicator',
  'The same rule read state by state, so an onset is seen where it starts and not only in the aggregate.',
  'The weekly state claims and the state unemployment rates are already gathered and refreshed at every release (collections 37 and 45). What remains is the walk: the rule read on each state separately, from 1976 forward, with no line chosen from a state’s own future. Until that walk is finished and audited nothing is published here.'),
 ('stress-map','National Stress Map',
  'Labor-market stress across the fifty states and the District, on one scale, week by week.',
  'One scale, one week, fifty-one places. The map draws on the same weekly state claims as the state onset detector; it waits on the scale being fixed in advance, so that a state’s colour means the same thing in 1980 as in 2026.'),
 ('damage-index','Damage Index',
  'A Richter scale for recessions: how deep, how broad, and where — not only when.',
  'Dating a recession says when; it does not say how much. The index measures the depth of the fall and the breadth of the states and industries carrying it on one scale fixed in advance, so that two recessions can be compared without hindsight about either, and so that a disturbance a national date hides — one state, one industry — still has a number. It is the subject of Paper 3, <i>The Damage Index: A Richter Scale for Recessions</i>.'),
 ('chronology','Business-Cycle Chronology',
  'The program’s dated chronology of peaks and troughs beside the committee’s and the OECD’s.',
  'The rule’s own peaks and troughs, 1948 to today, set beside the National Bureau’s and the OECD’s, with the days each was called and the days each was announced. The material exists in the record; the page is what remains.'),
]
for _slug,_name,_tag,_body in _STUBS:
    _nav=_header.replace(' aria-current="page"','').replace('href="/%s/"'%_slug,'href="/%s/" aria-current="page"'%_slug)
    _p=('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n<title>Bristow-Hall Business Cycle Program — '+_name+'</title>\n'
        +_style+'\n<style>.stub{max-width:none;margin:38px 0 0}.stub h1{font-size:30px;color:#990000;margin:0 0 10px;line-height:1.2}'
        '.stub .tag{font-size:17px;color:#333;margin:0 0 18px;max-width:none}.stub p{color:#333;margin:0 0 14px}'
        '.stub .back{margin-top:26px;font-size:14px}</style>\n</head>\n<body>\n'
        +_nav+'\n<div class="inner"><div class="stub">'
        '<span class="badge dev">IN DEVELOPMENT</span>'
        '<h1>'+_name+'</h1><p class="tag">'+_tag+'</p>'                  # audit-0924: the name and one line, nothing else
        '<p class="back"><a href="/">&larr; Back to the program</a></p></div></div>\n'
        +_footer+'\n</body>\n</html>\n')
    os.makedirs(os.path.join(SITE,'public',_slug),exist_ok=True)
    open(os.path.join(SITE,'public',_slug,'index.html'),'w',encoding='utf-8').write(_p)
print('stub pages built:',', '.join('/'+s+'/' for s,_,_,_ in _STUBS))

# ---- /data/ : every series the site stands on, one table, sortable (17 September 2026) ----
# Rows: the series the rule reads (the state's `feeds`), the front page's readings (collection 109's tiles) and every
# channel the legs read (the state's `leg_feeds`, from the files the leg loaders read). Nothing is typed: the page and
# the inventory read the same objects. Default order: the day each is in hand through, most recent first; a click on a
# heading sorts by it, a second click reverses. Names carry no parentheticals; the ID column names the series.
import re as _re3, datetime as _dt3
def _esc(x):
    return ('' if x is None else str(x)).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')
_MON=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
def _fmtd(d):
    try:
        y,m,dd=str(d).split('-'); return _MON[int(m)-1]+' '+str(int(dd))+', '+y
    except Exception:
        try:
            y,m=str(d).split('-'); return _MON[int(m)-1]+' '+y
        except Exception: return _esc(d)
def _fmtp(d,cad):
    # audit-0924: a monthly value is its month, a quarterly one its quarter - not the first day of either
    try:
        y,m=[int(x) for x in str(d)[:7].split('-')]
        if cad=='monthly': return _MON[m-1]+' '+str(y)
        if cad=='quarterly': return '%d:Q%d'%(y,(m-1)//3+1)
    except Exception: pass
    return _fmtd(d)
def _us(h):
    # audit-0924 (Anthony, 17 Sep 2026: US spelling for everything) - the page text only; the state's own keys are unchanged
    for a_,b_ in (('labour','labor'),('Labour','Labor'),('programme','program'),('Programme','Program'),('colour','color'),('per cent','percent'),('centre','center')):
        h=h.replace(a_,b_)
    return h
def _strip_paren(x): return _re3.sub(r'\s*\([^)]*\)','',x or '').replace('  ',' ').strip().rstrip(':,')
# exact words only on the data page (Anthony, 17 and 20 September 2026): the Next published column carries the day, so a
# cadence says only what is fixed - 'Monthly - usually the first Friday, 8:30 AM ET' becomes 'Monthly, 8:30 AM ET'
def _exact_every(s): return _re3.sub(r'\s*-\s*(?:usually|about)\b[^,]*,\s*',', ',s or '')
# audit-0924 (24 Sep 2026; Anthony: every link to the publisher's own page, exact words only, no explanatory sentences);
# one list since 25 Sep 2026 (ops-0924): s2/feed_publishers.py, which also rewrites the feed records this page publishes
import importlib.util as _iu_fp; _sp_fp=_iu_fp.spec_from_file_location('feed_publishers',os.path.join(os.path.dirname(os.path.abspath(__file__)),'s2','feed_publishers.py')); _fp=_iu_fp.module_from_spec(_sp_fp); _sp_fp.loader.exec_module(_fp)
_PUB=_fp.PUB
_pub=_fp.pub
def _cad_kind(every):
    e_=str(every or '').lower()
    return 'quarterly' if e_.startswith('quarterly') else 'monthly' if e_.startswith('monthly') else 'weekly' if e_.startswith('weekly') else 'daily'
def _iso(d):
    d=str(d or '')
    if _re3.match(r'^\d{4}-\d{2}-\d{2}$',d): return d
    if _re3.match(r'^\d{4}-\d{2}$',d): return d+'-01'
    m=_re3.search(r'(\d{4}-\d{2}-\d{2})',d)
    if m: return m.group(1)
    m=_re3.search(r'([A-Z][a-z]{2}) (\d{1,2}), (\d{4})',d)                    # audit-0924: 'week ending Sep 19, 2026'
    if m and m.group(1) in _MON: return '%s-%02d-%02d'%(m.group(3),_MON.index(m.group(1))+1,int(m.group(2)))
    m=_re3.search(r'([A-Z][a-z]{2}) (\d{4})',d)
    if m and m.group(1) in _MON: return '%s-%02d-01'%(m.group(2),_MON.index(m.group(1))+1)
    return ''
def _nxt_iso(n):
    n=str(n or ''); m=_re3.match(r'^~?(\d{4}-\d{2}-\d{2})',n)
    if m: return m.group(1)
    if 'next weekday' in n or n=='daily': return (_dt3.date.today()+_dt3.timedelta(days=1)).isoformat()
    return ''
_rows=[]
for f in state.get('feeds',[]):
    _pb=_pub(_strip_paren(f.get('name')))
    _rows.append(dict(kind='rule',cad=('quarterly' if str(f.get('name','')).startswith('GDPNow') else _cad_kind(f.get('every'))),name=_strip_paren(f.get('name')),ids=f.get('ids') or '',url=((_pb[1] or f.get('url')) if _pb else f.get('url')),
                      source=((_pb[0]+' &middot; '+_pb[2]) if _pb else _strip_paren(f.get('source'))+((' &middot; '+_exact_every(_strip_paren(f.get('every')))) if f.get('every') else '')),
                      value=f.get('value') or '',values=f.get('values') or [],units=None,through=str(f.get('through') or ''),nxt=str(f.get('next') or ''),refreshed=state.get('built') or '',legs='the rule',note=None))
_seen=set()
for t in _tiles:
    sid=t.get('sid') or ''
    if not sid or sid in _seen: continue
    _seen.add(sid)
    _TILE_UNITS={'UNRATE':'percent, seasonally adjusted','PAYEMS':'persons, seasonally adjusted','ICSA':'claims, seasonally adjusted','IURSA':'percent, seasonally adjusted','JTSJOL':'openings, seasonally adjusted','UNEMPLOY':'unemployed per opening','JTSQUR':'percent, seasonally adjusted','CPIAUCSL':'percent, year over year'}
    _tu=_TILE_UNITS.get(sid,'')
    if 'a month' in (t.get('val') or ''): _tu='persons a month, the three-month average change'
    if 'per opening' in (t.get('lab') or '').lower(): _tu='unemployed persons per job opening'
    _TPUB={'UNRATE':'Bureau of Labor Statistics, Employment Situation','PAYEMS':'Bureau of Labor Statistics, Employment Situation','ICSA':'Department of Labor, weekly claims release',
           'IURSA':'Department of Labor, weekly claims release','JTSJOL':'Bureau of Labor Statistics, JOLTS','JTSQUR':'Bureau of Labor Statistics, JOLTS','CPIAUCSL':'Bureau of Labor Statistics, Consumer Price Index'}
    _rows.append(dict(kind='front',cad=('weekly' if sid in ('ICSA','IURSA') else 'monthly'),name=_strip_paren(t.get('lab')),ids=sid,url=t.get('src') or ('https://fred.stlouisfed.org/series/'+sid),source=_TPUB.get(sid,'FRED series '+sid),
                      value=(t.get('val') or ''),values=[],units=_tu,through=_iso(t.get('sub')),nxt=str(t.get('next') or ''),refreshed=_tiles_built,legs='front page',note=None))
import json
_lf=state.get('leg_feeds',[]); _ls=state.get('leg_status',{})
# v3.59 (20 September 2026): the backstop tier's three inputs, read from out/backstop_state.json (written by s2/backstop.py before the build)
try:
    _bs=json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'out','backstop_state.json')))
    _BSROW={'SOS_NSA':('Insured unemployment rate, not seasonally adjusted (52-week change of the 26-week average)','CCNSA / COVEMP','https://www.dol.gov/ui/data.pdf','Department of Labor, weekly claims release'),
            'LMSI30':('States with the insured rate accelerating (13-week average at least 0.20 point above a year earlier)','ETA 539 by state','https://oui.doleta.gov/unemploy/DataDownloads.asp','Department of Labor, ETA 539 state weekly claims'),
            'CFNAI':('Chicago Fed National Activity Index, three-month average','CFNAIMA3','https://www.chicagofed.org/research/data/cfnai/current-data','Federal Reserve Bank of Chicago'),
            # v3.74 (23 September 2026, collection 335; the row's link, its series and its next day added after the deploy's ops check
            # reported the row with no link and no release calendar): the shadow reading. Its ids name both inputs, so the ops calendar
            # reads both FRED releases (50, the Employment Situation; 192, JOLTS) and keeps the one whose day the reading gives.
            'Michez':('Michaillat and Saez\'s rule: the smaller of the unemployment indicator and the vacancy indicator','UNRATE, JTSJOL','https://doi.org/10.1111/obes.12685','Michaillat and Saez (2025); Bureau of Labor Statistics'),
            # v3.74 + collection 366 (24 September 2026; Anthony: 'yes'): the Weekly Economic Index as a fifth shadow reading - the only weekly read on the
            # labour-hoarding type; current vintage, real-time history from April 2020; not in the opener, not on the scoreboard
            'WEI':('Weekly Economic Index (Lewis, Mertens and Stock), 13-week mean','WEI','https://www.dallasfed.org/research/wei','Federal Reserve Bank of Dallas &middot; Weekly, Thursday')}
    for _k,_r in (_bs.get('rules') or {}).items():
        _nm,_id,_url,_src=_BSROW.get(_k,(_k,_k,'','backstop tier'))
        _rows.append(dict(kind='backstop',cad=('monthly' if _k in ('CFNAI','Michez') else 'weekly'),name=_nm,ids=_id,url=_url,source=_src+' &middot; line '+str(_r.get('line')),value=str(_r.get('reading')) if _r.get('reading') is not None else '',values=[],units=_r.get('unit'),through=str(_r.get('data_through') or ''),nxt=(next((str(x.get('date')) for x in state.get('next_releases',[]) if str(x.get('what','')).lower().startswith('weekly claims')),'') if _k not in ('CFNAI','Michez','WEI') else str(_r.get('next') or '')),refreshed=str(_bs.get('built_at') or '')[:10],legs='the backstop tier',note=('ON since '+_fmtd(_r.get('since')) if _r.get('on') else 'off since '+_fmtd(_r.get('since')))))
except Exception as _e: print('backstop rows not listed:', _e)
for f in _lf:
    who=('legs '+f['legs'] if f.get('legs') else '')+((' &middot; ' if f.get('legs') else '')+'confirms '+f['confirms'] if f.get('confirms') else '')
    src=_strip_paren(f.get('source'))+((' &middot; '+f['cadence']) if f.get('cadence') else '')+((' &middot; first prints through '+_fmtd(f['first_prints_through'])) if f.get('first_prints_through') else '')
    _note=f.get('note')
    if str(state.get('leg_tier') or '').startswith('retired'):   # v3.58 (20 Sep 2026): the rule has no leg tier; say what these rows are
        _note=((_note+' \u00b7 ') if _note else '')+'read for the retired leg tier (v3.46\u2013v3.56); not used by the rule since v3.57'
    _rows.append(dict(kind='leg',name=_strip_paren(f.get('title') or f['channel']),ids=f['channel'],url=f.get('url'),source=src,value=str(f.get('value') or ''),values=[],units=f.get('units'),through=str(f.get('through') or ''),nxt=str(f.get('next') or ''),refreshed=f.get('refreshed') or '',legs=who,note=_note))
def _pct(v,u):
    # a percent carries its sign on the number (Anthony, 17 September 2026): "1.1%", and the units line keeps only what
    # else the publisher says ("seasonally adjusted"); percentage points and percent changes are not percents of a level
    u=u or ''; ul=u.lower()
    if ul.startswith('percent') and not ul.startswith('percentage') and 'change' not in ul and v:
        rest=_re3.sub(r'^percent\s*,?\s*','',u,flags=_re3.I).strip(' ,')
        return (str(v) if str(v).endswith('%') else str(v)+'%'),rest
    return v,u
def _vcell(r):
    # the value and, beneath it, the units the publisher states; a feed of several series lists each with its ID
    if r.get('values'):
        out=[]
        for i_,v_,u_ in r['values']:
            v_,u_=_pct(v_,u_); out.append('<div class="v"><b>'+_esc(v_)+'</b><span class="u">'+_esc(i_)+(' &middot; '+_esc(u_) if u_ else '')+'</span></div>')
        return ''.join(out)
    if not r['value']: return '<span class="na">&mdash;</span>'
    v_,u_=_pct(r['value'],r.get('units'))
    return '<b>'+_esc(v_)+'</b>'+('<div class="u">'+_esc(u_)+'</div>' if u_ else '')
def _drow(r):
    ext=not str(r.get('url') or '').startswith('/')
    t1=('<a href="'+_esc(r['url'])+'"'+(' target="_blank" rel="noopener"' if ext else '')+'>'+_esc(r['name'])+' &#8599;</a>') if r.get('url') else _esc(r['name'])
    th=_iso(r['through']); nx=_nxt_iso(r['nxt']); rf=_iso(r['refreshed'])
    return ('<tr data-name="'+_esc(r['name'].lower())+'" data-ids="'+_esc(r['ids'].lower())+'" data-value="'+_esc(r['value'].lower())+'" data-through="'+th+'" data-next="'+nx+'" data-refreshed="'+rf+'" data-legs="'+_esc(r['legs'].lower())+'">'
            +'<td><b>'+t1+'</b><div class="src">'+r['source']+'</div>'+('<div class="note">'+_esc(r['note'])+'</div>' if r.get('note') else '')+'</td>'
            +'<td class="id">'+_esc(r['ids'])+'</td>'
            +'<td class="val">'+_vcell(r)+'</td>'
            +'<td class="num">'+(_fmtp(r['through'],r.get('cad')) if r['through'] else '<span class="na">&mdash;</span>')+'</td>'
            +'<td class="num">'+(('<span class="na">&mdash;</span>' if r['nxt'].startswith('~') else (_fmtd(r['nxt'][:10]) if _re3.match(r'^\d{4}-\d{2}-\d{2}',r['nxt']) else _esc(r['nxt']))) if r['nxt'] else '<span class="na">&mdash;</span>')+'</td></tr>')
_rows.sort(key=lambda r:_iso(r['through']),reverse=True)
_trs=''.join(_drow(r) for r in _rows)
_stale=state.get('leg_channels_stale',[])
_legend=''
_stale_line=('<p class="dlede">Stale past its own cadence: '+_esc(', '.join(_stale))+'.</p>') if _stale else ''
# v3.60 (21 September 2026, collection 278; E5, the channel-dark rules): every channel the rule reads declares how long it may go
# without a new reading and what stands in for it; a channel past its limit is named here with its substitute, never frozen silently
_chs=state.get('channels') or []; _chd=[c for c in _chs if c.get('status')!='current']
_ch_line=(('<p class="dlede">Not current: '+_esc('; '.join('%s - %s, %s days since its last reading (limit %s); substitute: %s'%(c.get('channel'),c.get('status'),c.get('age_days'),c.get('limit_days'),c.get('substitute')) for c in _chd))+'.</p>') if _chd
          else '')   # audit-0924: no sentence when every channel is current
_nav_data=_header.replace(' aria-current="page"','').replace('href="/data/"','href="/data/" aria-current="page"')
_datapage=('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
 '<meta name="viewport" content="width=device-width, initial-scale=1">\n<title>Bristow-Hall Business Cycle Program — Data</title>\n'
 +_style+'\n<style>.dtab{width:100%;border-collapse:collapse;font-size:14px;margin-top:10px}'
 '.dtab th{text-align:left;font-weight:700;color:#222;border-bottom:2px solid #990000;padding:9px 10px 7px;background:#faf7f7;white-space:nowrap;cursor:pointer;user-select:none}'
 '.dtab th:hover{background:#fdf2f2}.dtab th.on::after{content:" \\25BC";font-size:9px;color:#990000}.dtab th.on.asc::after{content:" \\25B2"}'
 '.dtab th.num,.dtab td.num{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}'
 '.dtab td{padding:11px 10px;border-bottom:1px solid #dfe4ea;vertical-align:top}'
 '.dtab td.val{color:#111}.dtab td.val b{font-weight:700}.dtab .u{color:#666;font-size:12px;font-weight:400;margin-left:7px}.dtab div.u{margin-left:0;margin-top:2px}.dtab .v{margin-bottom:3px;white-space:nowrap}'
 '.dtab td.id{font-family:Menlo,Consolas,monospace;font-size:12.5px;color:#222;white-space:nowrap}'
 '.dtab .src{color:#666;font-size:12.5px;font-weight:400;margin-top:3px}'
 '.dtab .note{color:#7f0000;font-size:12.5px;margin-top:4px}'
 '.dtab .na{color:#999}.dwrap{overflow-x:auto}.dlede{max-width:none;color:#7f0000;margin:12px 0 0}'
 '.dleg{margin-top:8px;font-size:12.5px;color:#555}.dleg summary{cursor:pointer;color:#990000}'
 '@media (max-width:1100px){.dtab th[data-k="ids"],.dtab td.id{display:none}.dtab td{padding:9px 6px}.dtab .v{white-space:normal}}</style>\n</head>\n<body>\n'
 +_nav_data+'\n<div class="inner">'
 '<h2 style="margin-top:30px">Data</h2><div class="rule"></div>'+_stale_line+_ch_line+
 '<div class="dwrap"><table class="dtab" id="dtab"><thead><tr>'
 '<th data-k="name">Series</th><th data-k="ids">ID</th><th data-k="value">Where it stands</th><th class="num on" data-k="through">In hand through</th>'
 '<th class="num" data-k="next">Next published</th></tr></thead><tbody>'
 +_trs+'</tbody></table></div><p class="dleg"><a href="/margins/">Margins</a></p>'+_legend+
 '<script>(function(){var tb=document.getElementById("dtab"),ths=tb.querySelectorAll("th[data-k]"),cur="through",dir=-1;'
 'function srt(k,d){var body=tb.tBodies[0],rows=Array.prototype.slice.call(body.rows);rows.sort(function(a,b){var x=a.dataset[k]||"",y=b.dataset[k]||"";if(x===y)return 0;if(x==="")return 1;if(y==="")return -1;return (x<y?-1:1)*d;});'
 'rows.forEach(function(r){body.appendChild(r);});ths.forEach(function(t){t.classList.remove("on","asc");if(t.dataset.k===k){t.classList.add("on");if(d>0)t.classList.add("asc");}});}'
 'ths.forEach(function(t){t.addEventListener("click",function(){var k=t.dataset.k;dir=(k===cur)?-dir:((k==="name"||k==="ids"||k==="value")?1:-1);cur=k;srt(k,dir);});});'
 'srt("through",-1);})();</script>'
 '</div>\n'+_footer+'\n</body>\n</html>\n')
os.makedirs(os.path.join(SITE,'public','data'),exist_ok=True)
open(os.path.join(SITE,'public','data','index.html'),'w',encoding='utf-8').write(_us(_datapage))

# ---- THE MARGINS PAGE (24 September 2026, collection 368; plan Step 5 item 18): every object's distance to its line today, flagged within
# ---- 20 per cent on the side that is live (open when the rule stands closed, close when it stands open), and the near-miss log the build
# ---- keeps (state['near_misses']: spells with a reading at or above 0.8 of a line since 1948) - the false-alarm audit of the future.
try:
    _rd=list(state.get('readings') or []); _nm=state.get('near_misses') or {}; _live='close' if (state.get('standing') or {}).get('state')=='open' else 'open'
    def _rat(r):
        try: return float(r.get('ratio'))
        except Exception: return -9
    _rd.sort(key=lambda r:(-1 if r.get('side')==_live else 0, -_rat(r)))
    _mrows=''
    for r in _rd:
        _q=_rat(r); _flag=(r.get('side')==_live and 0.8<=_q<1); _past=(r.get('side')==_live and _q>=1)   # audit-0924: 250% of a line is not 'within 20%'
        _nx=str(r.get('next') or '').split(' (')[0]
        if _nx=='daily': _nx=(_dt3.date.today()+_dt3.timedelta(days=(3 if _dt3.date.today().weekday()==4 else 2 if _dt3.date.today().weekday()==5 else 1))).isoformat()
        _mrows+=('<tr class="%s"><td>%s</td><td>%s</td><td class="num">%s</td><td class="num">%s</td><td class="num"><b>%s</b>%s</td><td class="num">%s</td><td class="num">%s</td></tr>'
                 % ('near' if (_flag or _past) else '', r.get('side',''), _esc(str(r.get('object',''))), r.get('reading',''), r.get('line',''),
                    ('%.0f%%' % (100*_q)) if _q>-9 else '', ' <span class="fl">within 20%</span>' if _flag else (' <span class="fl">past its line</span>' if _past else ''), _fmtd(r.get('through')) if r.get('through') else '', _fmtd(_nx) if _nx else ''))
    _sp=list(_nm.get('spells') or []); _sp.sort(key=lambda x:str(x.get('start')))
    _nrows=''.join('<tr><td>%s</td><td>%s</td><td>%s</td><td class="num">%s</td><td class="num">%s</td></tr>' % (_fmtd(x.get('start')), _fmtd(x.get('end')), _esc(str(x.get('branch',''))), ('%.0f%%' % (100*float(x.get('max')))) if x.get('max') is not None else '', x.get('days','')) for x in _sp[-12:][::-1])
    _nav_m=_header.replace(' aria-current="page"','')
    _mpage=('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n'
      '<title>Bristow-Hall Business Cycle Program — Margins</title>\n'+_style+
      '\n<style>.dtab{width:100%;border-collapse:collapse;font-size:14px;margin-top:10px}.dtab th{text-align:left;font-weight:700;color:#222;border-bottom:2px solid #990000;padding:9px 10px 7px;background:#faf7f7;white-space:nowrap}'
      '.dtab th.num,.dtab td.num{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}.dtab td{padding:9px 10px;border-bottom:1px solid #dfe4ea;vertical-align:top}'
      'tr.near td{background:#fff4f4}.fl{color:#990000;font-size:12px;font-weight:700;margin-left:6px}.dwrap{overflow-x:auto}h3{margin:28px 0 0;font-size:18px;color:#222}.sub{color:#555;font-size:13px;margin:4px 0 0}</style>\n</head>\n<body>\n'
      +_nav_m+'\n<div class="inner"><h2 style="margin-top:30px">Margins</h2><div class="rule"></div>'
      '<div class="dwrap"><table class="dtab"><thead><tr><th>Side</th><th>Object</th><th class="num">Reading</th><th class="num">Line</th><th class="num">Of the line</th><th class="num">Through</th><th class="num">Next</th></tr></thead><tbody>'+_mrows+'</tbody></table></div>'
      '<h3>Near misses since 1948: %d</h3>' % len(_sp)+
      '<div class="dwrap"><table class="dtab"><thead><tr><th>From</th><th>To</th><th>Branch</th><th class="num">Peak, of the line</th><th class="num">Days</th></tr></thead><tbody>'+_nrows+'</tbody></table></div>'
      '</div>\n'+_footer+'\n</body>\n</html>\n')
    os.makedirs(os.path.join(SITE,'public','margins'),exist_ok=True)
    open(os.path.join(SITE,'public','margins','index.html'),'w',encoding='utf-8').write(_us(_mpage))
    print('margins page built: %d objects, %d flagged within 20%% on the %s side, %d near-miss spells' % (len(_rd), sum(1 for r in _rd if r.get('side')==_live and _rat(r)>=0.8), _live, len(_sp)))
except Exception as _e: print('margins page not built:', _e)

# /data/warn/: the 25 states' own WARN notice pages, the sources leg N reads (17 September 2026, Anthony: a link takes
# the reader to the actual source, never to a scraper's repository). Each state's page as the state publishes it.
_WARN_STATES=[('AK','Alaska','https://jobs.alaska.gov/RR/WARN_notices.htm'),('AL','Alabama','https://www.madeinalabama.com/warn-list/'),('AZ','Arizona','https://www.azjobconnection.gov/search/warn_lookups?utf8=%E2%9C%93&q%5Bnotice_on_gteq%5D=1990-01-01&q%5Bnotice_on_lteq%5D=2035-12-31&commit=Search&q%5Bs%5D=notice_on+desc'),
 ('CA','California','https://edd.ca.gov/en/Jobs_and_Training/Layoff_Services_WARN'),('CT','Connecticut','https://dolpublicdocumentlibrary.ct.gov/CsblrCategory?prefix=%2Frapid_response%2Fwarn_documents'),
 ('DC','District of Columbia','https://does.dc.gov/page/industry-closings-and-layoffs-warn-notifications'),('DE','Delaware','https://joblink.delaware.gov/search/warn_lookups?utf8=%E2%9C%93&q%5Bnotice_on_gteq%5D=1990-01-01&q%5Bnotice_on_lteq%5D=2035-12-31&commit=Search&q%5Bs%5D=notice_on+desc'),('IA','Iowa','https://workforce.iowa.gov/employers/business-resources/warn'),
 ('IL','Illinois','https://dceo.illinois.gov/workforcedevelopment/warn.html'),('IN','Indiana','https://www.in.gov/dwd/warn-notices/current-warn-notices/'),('KY','Kentucky','https://kcc.ky.gov/Pages/News.aspx'),
 ('MT','Montana','https://wsd.dli.mt.gov/wioa/related-links/warn-notice-page'),('NE','Nebraska','https://dol.nebraska.gov/ReemploymentServices/LayoffServices/LayoffsAndDownsizingWARN'),('NY','New York','https://dol.ny.gov/warn-dashboard'),
 ('OK','Oklahoma','https://www.employoklahoma.gov/Participants/s/warnnotices'),('OR','Oregon','https://ccwd.hecc.oregon.gov/Layoff/WARN'),('RI','Rhode Island','https://dlt.ri.gov/employers/worker-adjustment-and-retraining-notification-warn'),
 ('SC','South Carolina','https://scworks.org/employer/employer-programs/risk-closing/layoff-notification-reports'),('SD','South Dakota','https://dlr.sd.gov/workforce_services/businesses/warn_notices.aspx'),
 ('TN','Tennessee','https://www.tn.gov/workforce/general-resources/major-publications0/major-publications-redirect/reports.html'),('TX','Texas','https://www.twc.texas.gov/data-reports/warn-notice'),('UT','Utah','https://jobs.utah.gov/employer/business/warnnotices.html'),
 ('VT','Vermont','https://www.vermontjoblink.com/search/warn_lookups?utf8=%E2%9C%93&q%5Bnotice_on_gteq%5D=1990-01-01&q%5Bnotice_on_lteq%5D=2035-12-31&commit=Search&q%5Bs%5D=notice_on+desc'),('WA','Washington','https://esd.wa.gov/about-employees/WARN'),('WI','Wisconsin','https://dwd.wisconsin.gov/dislocatedworker/warn/')]
try:
    _wix={x['state']:x for x in json.load(open(os.path.join(_bhs_root(),'117_warn_notices_2026-09-14','data','warn_notices','_INDEX.json')))}
except Exception: _wix={}
_wrows=''.join('<tr><td><b><a href="'+_esc(u)+'" target="_blank" rel="noopener">'+_esc(n)+' &#8599;</a></b></td><td class="id">'+s+'</td>'
               +'<td class="num">'+('{:,}'.format(int(_wix[s].get('n') or 0)) if s in _wix else '')+'</td><td class="num">'+(_fmtd(str(_wix[s].get('to') or '')[:10]) if s in _wix and _wix[s].get('to') else '')+'</td></tr>' for s,n,u in _WARN_STATES)
_warnpage=('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n'
 '<title>Bristow-Hall Business Cycle Program — WARN notices, the 25 states</title>\n'+_style+'\n<style>.dtab{width:100%;border-collapse:collapse;font-size:14px;margin-top:10px}'
 '.dtab th{text-align:left;font-weight:700;color:#222;border-bottom:2px solid #990000;padding:9px 10px 7px;background:#faf7f7;white-space:nowrap}'
 '.dtab th.num,.dtab td.num{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}.dtab td{padding:9px 10px;border-bottom:1px solid #dfe4ea;vertical-align:top}'
 '.dtab td.id{font-family:Menlo,Consolas,monospace;font-size:12.5px;color:#222}</style>\n</head>\n<body>\n'+_nav_data+'\n<div class="inner">'
 '<h2 style="margin-top:30px">WARN notices, the 25 states</h2><div class="rule"></div>'
 '<table class="dtab"><thead><tr><th>State page</th><th>State</th><th class="num">Notices on file</th><th class="num">In hand through</th></tr></thead><tbody>'+_wrows+'</tbody></table></div>\n'+_footer+'\n</body>\n</html>\n')
os.makedirs(os.path.join(SITE,'public','data','warn'),exist_ok=True)
open(os.path.join(SITE,'public','data','warn','index.html'),'w',encoding='utf-8').write(_warnpage)
print('data inventory built:',len(state.get('feeds',[])),'rule series,',len(_seen),'front-page series,',len(_lf),'leg channels |',len(_rows),'rows')
