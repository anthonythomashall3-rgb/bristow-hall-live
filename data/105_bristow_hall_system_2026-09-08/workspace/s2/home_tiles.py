"""The home page's current readings: the headline series the programme shows beside its own indicator.

Fetched from FRED at every run of the live system and saved to collection 109 (the data rule), with one JSON of the
tiles the page prints. Nothing here enters the rule: these are context for a reader, not objects the rule reads.
The FRED key is read from local.env inside this process and never printed (Rule 12.6).
Run: python3 s2/home_tiles.py
"""
import os,sys,json,subprocess,datetime,shutil
from zoneinfo import ZoneInfo
import pandas as pd, numpy as np

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
MNT=_bhs_root()
ENV=os.path.join(MNT,'onset-detector-new-2026-08-23','live_data','config','local.env')
COL=os.path.join(MNT,'109_home_tiles_2026-09-11'); FR=os.path.join(COL,'fred'); os.makedirs(FR,exist_ok=True)
KEY=None
for line in open(ENV):
    if line.startswith('FRED_API_KEY='): KEY=line.strip().split('=',1)[1].strip().strip('"').strip("'")
assert KEY and len(KEY)==32, 'no FRED key in local.env'
def _curl(url,m=20,tries=2):
    for t in range(tries):   # 17 Sep 2026: shorter timeouts and one retry, so a slow FRED edge cannot hold the run for minutes
        r=subprocess.run(['curl','-sSL','-m',str(m),url],capture_output=True,text=True)
        if r.returncode==0 and r.stdout.strip(): return r.stdout
    raise RuntimeError('curl failed')
def fred(series):
    url=f'https://api.stlouisfed.org/fred/series/observations?series_id={series}&api_key={KEY}&file_type=json&observation_start=1990-01-01'
    try: d=json.loads(_curl(url))
    except RuntimeError: raise RuntimeError(f'curl failed for {series}')
    if 'observations' not in d: raise RuntimeError(f'FRED error for {series}: '+str(d)[:60].replace(KEY,'***'))
    s=pd.Series({o['date']:(np.nan if o['value']=='.' else float(o['value'])) for o in d['observations']})
    s.index=pd.to_datetime(s.index); return s.sort_index().dropna()
SERIES=['UNRATE','PAYEMS','JTSJOL','UNEMPLOY','JTSQUR','CPIAUCSL','ICSA','IURSA']
_RDC=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'cache','tiles_release_cache.json')
try: _RD=json.load(open(_RDC))
except Exception: _RD={}
def release_dates(sid,n=16):
    """the days the source itself publishes this series, from FRED's own release calendar, from today forward.
    Cached for the day (17 Sep 2026): the calendar is fetched once a day, not at every run."""
    t=datetime.date.today().isoformat(); c=_RD.get(sid)
    if c and c.get('day')==t and c.get('dates'): return [d for d in c['dates'] if d>=t]
    try:
        rid=_RD.get(sid,{}).get('rid')
        if not rid:
            u=f'https://api.stlouisfed.org/fred/series/release?series_id={sid}&api_key={KEY}&file_type=json'
            rid=json.loads(_curl(u))['releases'][0]['id']
        u2=(f'https://api.stlouisfed.org/fred/release/dates?release_id={rid}&api_key={KEY}&file_type=json'
            f'&realtime_start={t}&include_release_dates_with_no_data=true&sort_order=asc&limit={n}')
        ds=[d['date'] for d in json.loads(_curl(u2)).get('release_dates',[]) if d['date']>=t]
        _RD[sid]=dict(rid=rid,day=t,dates=ds); json.dump(_RD,open(_RDC,'w')); return ds
    except Exception: return [d for d in (c or {}).get('dates',[]) if d>=t] if c else []
def next_release(ds):
    """the next one. A day that is today counts as spent once the morning's releases are out (all of these are
    8:30 or 10:00 Eastern), so the page does not say 'next release today' all afternoon."""
    if not ds: return None
    now=datetime.datetime.now(ZoneInfo('America/New_York'))
    if ds[0]==now.date().isoformat() and (now.hour,now.minute)>=(10,30) and len(ds)>1: return ds[1]
    return ds[0]
# A SECOND SOURCE BEHIND EVERY SERIES (11 November 2026, collection 1042; Anthony: "make sure that all of our sources have backups
# wherever possible"). Order: (1) the FRED API; (2) FRED's keyless file (another route, no key to expire); (3) the file on disk.
# The Bureau of Labor Statistics' own API (the publisher itself) is read on every run for the six monthly series: its figures are
# compared with FRED's (source_check in the JSON; s2/q41_data_check.py), and a month the BLS has that FRED has not yet loaded, or
# that the disk file lacks when FRED is down, is taken from the BLS.
import io as _io
BLS_ID={'UNRATE':'LNS14000000','PAYEMS':'CES0000000001','UNEMPLOY':'LNS13000000','JTSJOL':'JTS000000000000000JOL','JTSQUR':'JTS000000000000000QUR','CPIAUCSL':'CUSR0000SA0'}
_BKEY=None
for _l in open(ENV):
    if _l.startswith('BLS_API_KEY='): _BKEY=_l.strip().split('=',1)[1].strip().strip('"').strip("'") or None
def _fredgraph(sid):
    df=pd.read_csv(_io.StringIO(_curl('https://fred.stlouisfed.org/graph/fredgraph.csv?id='+sid,m=30)))
    assert df.shape[1]==2 and df.columns[1]==sid, 'fredgraph: unexpected columns'
    s=pd.Series(pd.to_numeric(df.iloc[:,1],errors='coerce').values,index=pd.to_datetime(df.iloc[:,0])).dropna()
    s=s[s.index>='1990-01-01'].sort_index()
    assert len(s)>100, 'fredgraph: too short'
    return s
_BLS={}
def _bls_all():
    y=datetime.date.today().year
    body={'seriesid':list(BLS_ID.values()),'startyear':str(y-2),'endyear':str(y)}
    if _BKEY: body['registrationkey']=_BKEY
    r=subprocess.run(['curl','-sSL','-m','30','-X','POST','-H','Content-Type: application/json','-d',json.dumps(body),'https://api.bls.gov/publicAPI/v2/timeseries/data/'],capture_output=True,text=True)
    d=json.loads(r.stdout)
    assert d.get('status')=='REQUEST_SUCCEEDED', 'BLS API: '+str(d.get('status'))
    inv={v:k for k,v in BLS_ID.items()}
    for srs in d['Results']['series']:
        obs={}
        for o in srs['data']:
            if o['period'][:1]=='M' and o['period']!='M13':
                try: obs[pd.Timestamp(int(o['year']),int(o['period'][1:]),1)]=float(str(o['value']).replace(',',''))
                except ValueError: pass       # a month the Bureau never published (October 2025) prints as '-'
        if obs and srs['seriesID'] in inv: _BLS[inv[srs['seriesID']]]=pd.Series(obs).sort_index()
try: _bls_all()
except Exception as _e: print('home tiles: BLS API not read ('+str(_e)[:50]+'); FRED stands alone this run')
_ROUTE={}
def get(sid):
    p=os.path.join(FR,sid+'.csv')
    s=None
    for route,fn in (('FRED API',fred),('FRED keyless file',_fredgraph)):
        try:
            s=fn(sid)
            _ROUTE[sid]=route
            break
        except Exception as e: print(f'home tiles: {sid} not read by the {route} ({str(e)[:50]})')
    if s is None and os.path.exists(p):
        s=pd.read_csv(p,index_col=0,parse_dates=True).iloc[:,0].dropna()
        _ROUTE[sid]='file on disk'
        print(f'home tiles: {sid}: the file on disk stands')
    if s is None: raise RuntimeError(f'{sid}: no source answered and no file on disk')
    b=_BLS.get(sid)
    if b is not None and len(b):
        _new=b[b.index>s.index[-1]]
        if len(_new):
            s=pd.concat([s,_new]).sort_index()
            _ROUTE[sid]+=' + BLS API (newer month)'
            print(f'home tiles: {sid} {_new.index[-1].strftime("%b %Y")} taken from the BLS API ahead of FRED')
    if _ROUTE[sid]!='file on disk':
        if os.path.exists(p): shutil.copy(p,p+'.bak')
        s.rename(sid).to_frame().to_csv(p)
    return s
from concurrent.futures import ThreadPoolExecutor as _TPE
with _TPE(max_workers=3) as _ex: S=dict(zip(SERIES,_ex.map(get,SERIES)))
# every BLS figure for the last six months it shares with FRED must equal FRED's (the same number from the publisher itself)
_XC=dict(routes=dict(_ROUTE),compared=[],mismatch=[])
for _sid,_b in _BLS.items():
    _cm_=[d for d in _b.index if d in S[_sid].index][-6:]
    if _cm_: _XC['compared'].append(_sid)
    for _d in _cm_:
        if abs(float(_b.loc[_d])-float(S[_sid].loc[_d]))>1e-6*max(1.0,abs(float(_b.loc[_d]))): _XC['mismatch'].append('%s %s: FRED %s, BLS %s'%(_sid,_d.strftime('%Y-%m'),S[_sid].loc[_d],_b.loc[_d]))
# 1047 (11 November 2026): the two weekly-claims tiles against the Department of Labor's own release (the chain's first-print file,
# cache/national_first_prints_1985_live.csv, kept by bhs_update.py and bhs_dol_press.py). The newest week FRED carries is the advance
# figure, which is the first print: the two must be equal; a week the Department has released that FRED lacks is taken from the release.
try:
    _np=pd.read_csv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'cache','national_first_prints_1985_live.csv'),dtype=str)
    for _sid,_wk,_col in (('ICSA','ic_week_ended','icsa'),('IURSA','iu_week_ended','iur_sa')):
        _x=pd.DataFrame({'w':pd.to_datetime(_np[_wk],errors='coerce'),'v':pd.to_numeric(_np[_col],errors='coerce')}).dropna().sort_values('w').drop_duplicates('w',keep='last')
        _d=_x['w'].iloc[-1]
        _v=float(_x['v'].iloc[-1])
        if _d==S[_sid].index[-1]:
            _XC['compared'].append(_sid)
            if abs(_v-float(S[_sid].iloc[-1]))>1e-6*max(1.0,abs(_v)): _XC['mismatch'].append('%s %s: FRED %s, Department of Labor release %s'%(_sid,_d.date(),S[_sid].iloc[-1],_v))
        elif _d>S[_sid].index[-1] and (_d-S[_sid].index[-1]).days<=21:
            S[_sid].loc[_d]=_v
            S[_sid].rename(_sid).to_frame().to_csv(os.path.join(FR,_sid+'.csv'))
            _XC['routes'][_sid]=str(_XC['routes'].get(_sid,''))+' + Department of Labor release (newer week)'
            print('home tiles: %s week ending %s taken from the Department of Labor release ahead of FRED'%(_sid,_d.date()))
except Exception as _e: print('home tiles: Department of Labor first-print file not read ('+str(_e)[:60]+')')
print('home tiles: second source: %d series compared with the BLS and the Department of Labor, %d mismatch%s'%(len(_XC['compared']),len(_XC['mismatch']),(' - '+' / '.join(_XC['mismatch'])) if _XC['mismatch'] else ''))
def mon(d): return pd.Timestamp(d).strftime('%b %Y')
def day(d): d=pd.Timestamp(d); return d.strftime('%b')+' '+str(d.day)+', '+str(d.year)   # audit-0924: 'Sep 19, 2026'
U=S['UNRATE']; P=S['PAYEMS']; J=S['JTSJOL']; UE=S['UNEMPLOY']; Q=S['JTSQUR']; C=S['CPIAUCSL']; IC=S['ICSA']; IU=S['IURSA']
# UNITS, checked against FRED's own unit strings (11 September 2026):
#   UNRATE, IURSA, JTSQUR  percent          PAYEMS, JTSJOL, UNEMPLOY  thousands of persons
#   ICSA   persons (not thousands)          CPIAUCSL  index 1982-84=100
# so a level in thousands is divided by 1,000 and printed in millions, which is how a reader holds it.
g3=(P.iloc[-1]-P.iloc[-4])/3.0            # payroll growth, three-month average change, thousands
# 11 November 2026 (Anthony: n/a must never be printed; "there are other sources where we can find the cpi inflation"): October 2025
# was never published (the 2025 lapse in appropriations) and the BLS publishes no 12-month change for October 2026. Where the base
# month does not exist it is filled the way the BLS itself filled it for seasonal adjustment (its FAQ on the lapse, question 12): the
# geometric mean of the published months either side. The tile then says "estimated". No other month is ever filled.
_cm=C.index[-1]
_c0=_cm-pd.DateOffset(years=1)      # by date, never by position
_cpi_est=_c0 not in C.index
if _cpi_est:
    _lo=_c0-pd.DateOffset(months=1)
    _hi=_c0+pd.DateOffset(months=1)
    assert _lo in C.index and _hi in C.index, f'CPI: no base for {_cm.date()} and no published month either side of {_c0.date()}'
    _cbase=float(np.sqrt(C.loc[_lo]*C.loc[_hi]))
else: _cbase=float(C.loc[_c0])
cpi=(C.loc[_cm]/_cbase-1)*100
_um=J.index[-1]                           # unemployed per opening: BOTH series read at the SAME month
assert _um in UE.index, f'UNEMPLOY has no observation for {_um.date()}'
upo=UE.loc[_um]/J.loc[_um]
T=[
 dict(lab='Unemployment rate',      val=f'{U.iloc[-1]:.1f}%',              sub=mon(U.index[-1]),                    src='https://www.bls.gov/news.release/empsit.toc.htm'),
 dict(lab='Nonfarm payrolls',       val=f'{P.iloc[-1]/1000:,.1f} million',  sub=mon(P.index[-1]),                    src='https://www.bls.gov/news.release/empsit.toc.htm'),
 dict(lab='Payroll growth',         val=f'{round(g3)*1000:+,.0f} a month', sub='3-month average, '+mon(P.index[-1]),src='https://www.bls.gov/news.release/empsit.toc.htm'),
 dict(lab='Initial claims (week)',  val=f'{IC.iloc[-1]:,.0f}',             sub='week ending '+day(IC.index[-1]),    src='https://www.dol.gov/ui/data.pdf'),
 dict(lab='Insured unemployment rate',val=f'{IU.iloc[-1]:.1f}%',           sub='week ending '+day(IU.index[-1]),    src='https://www.dol.gov/ui/data.pdf'),
 dict(lab='Job openings',           val=f'{J.iloc[-1]/1000:,.1f} million',  sub=mon(J.index[-1]),                    src='https://www.bls.gov/jlt/'),
 dict(lab='Unemployed per opening', val=f'{upo:.2f}',                      sub=mon(_um),                    src='https://www.bls.gov/jlt/'),
 dict(lab='Quits rate',             val=f'{Q.iloc[-1]:.1f}%',              sub=mon(Q.index[-1]),                    src='https://www.bls.gov/jlt/'),
 dict(lab='CPI inflation',          val=f'{cpi:.1f}%',                     sub=('estimated year over year, ' if _cpi_est else 'year over year, ')+mon(_cm), src='https://www.bls.gov/cpi/'),
]
# NO PLACEHOLDER, EVER (11 November 2026): a tile that is not a number stops this run here; the tiles already on disk stand.
import re as _re_np
_bad_np=[t_['lab'] for t_ in T if not _re_np.fullmatch(r'[+-]?\d[\d,]*(\.\d+)?(%| million| a month)?',str(t_['val'])) or not _re_np.search(r'\b(19|20)\d\d$',str(t_['sub']))]
assert not _bad_np, 'home tiles: not a number / no period: '+', '.join(_bad_np)
_ID={"Unemployment rate":"UNRATE","Nonfarm payrolls":"PAYEMS","Payroll growth":"PAYEMS","Initial claims (week)":"ICSA",
     "Insured unemployment rate":"IURSA","Job openings":"JTSJOL","Unemployed per opening":"JTSJOL","Quits rate":"JTSQUR","CPI inflation":"CPIAUCSL"}
_DS={}; _NX={}
for _s in set(_ID.values()):
    _DS[_s]=release_dates(_s); _NX[_s]=next_release(_DS[_s])
# Three tiles are computed rather than read, so the link under them must say so: the number shown is not the
# series the link opens. CPI inflation is the exception that can be linked exactly — FRED's own year-over-year
# transformation of CPIAUCSL is the figure printed.
# audit-0924 (24 Sep 2026; Anthony: every link to the publisher's own page): each tile names the release it links to
_LINK={'Unemployment rate':'BLS Employment Situation','Nonfarm payrolls':'BLS Employment Situation',
       'Payroll growth':'computed from the BLS Employment Situation','Initial claims (week)':'Department of Labor, weekly claims',
       'Insured unemployment rate':'Department of Labor, weekly claims','Job openings':'BLS JOLTS',
       'Unemployed per opening':'computed from the BLS Employment Situation and JOLTS','Quits rate':'BLS JOLTS',
       'CPI inflation':'computed from the BLS Consumer Price Index'}
# THE EXACT SOURCE, AND NOTHING ELSE (collection 411, 25 September 2026; Anthony: "on the widgets on the home page, dont include
# anything but the name of and link to the proper source, the exact page we get the data from"). Every number here is read from
# FRED (above), so each tile links the FRED series page of each series it is computed from - two for unemployed per opening -
# named by the series and nothing more; s2/source_links.py checks each address once a day and never lets a dead one through.
# _LINK above (the publisher's release, "computed from ...") is no longer shown.
try:
    import importlib.util as _iu_sl
    _sp_sl=_iu_sl.spec_from_file_location('source_links',os.path.join(os.path.dirname(os.path.abspath(__file__)),'source_links.py'))
    _sl=_iu_sl.module_from_spec(_sp_sl); _sp_sl.loader.exec_module(_sl)
    # the tile's value and period as its data token: the run that reads a release checks that tile's addresses again (411)
    _TS=_sl.guarded({'tile|'+_t['lab']:_sl.tile_sources(_t['lab']) for _t in T},tokens={'tile|'+_t['lab']:str(_t.get('val'))+'|'+str(_t.get('sub')) for _t in T})
    _TS={k[5:]:v for k,v in _TS.items()}
except Exception as _e:
    print(f'home tiles: source links not checked ({type(_e).__name__}); FRED series pages as written')
    _TS={_t['lab']:[('FRED '+s,'https://fred.stlouisfed.org/series/'+s) for s in ([_ID.get(_t['lab'])] if _ID.get(_t['lab']) else [])] for _t in T}
for _t in T:
    _t["sid"]=_ID.get(_t["lab"]); _t["next"]=_NX.get(_t["sid"])
    _srcs=[list(p) for p in (_TS.get(_t["lab"]) or [])]
    if _srcs:
        _t["srcs"]=_srcs; _t["src"]=_srcs[0][1]; _t["link"]=_srcs[0][0]
    else:
        _t.pop("src",None); _t["link"]=None      # no address that answers: the tile shows no link rather than a dead one
# the scheduler reads this: a run is due on every day a series the front page shows is published, so the page is
# current within minutes of the release instead of waiting for the day's close.
_cal=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'cache','tiles_release_dates.csv')
with open(_cal,'w') as _f:
    _f.write('series,date\n')
    for _s in sorted(_DS):
        for _d in _DS[_s]: _f.write(f'{_s},{_d}\n')
shutil.copy(_cal,os.path.join(COL,'tiles_release_dates.csv'))
_prev=None
_op=os.path.join(COL,'home_tiles.json')
if os.path.exists(_op):
    try: _prev={x['lab']:x for x in json.load(open(_op))['tiles']}
    except Exception: _prev=None
_moved=[]
if _prev is not None:
    for _t in T:
        _o=_prev.get(_t['lab'])
        if _o is None: _moved.append(f"{_t['lab']} (new)")
        elif (_o.get('val'),_o.get('sub'))!=(_t['val'],_t['sub']): _moved.append(f"{_t['lab']} {_o.get('val')} -> {_t['val']}")
out=dict(built=datetime.date.today().isoformat(),tiles=T)
out['source_check']=_XC
json.dump(out,open(_op,'w'),indent=1)
print('home tiles: '+(('CHANGED — '+'; '.join(_moved)) if _moved else 'unchanged')
      +f' | {len(T)} readings through {mon(U.index[-1])} (unemployment rate), {day(IC.index[-1])} (claims)'
      +'; next releases '+', '.join(f'{k} {v}' for k,v in sorted(_NX.items()) if v)+'; saved to collection 109')
