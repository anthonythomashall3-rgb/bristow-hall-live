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
        r=subprocess.run(['curl','-sS','-m',str(m),url],capture_output=True,text=True)
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
def get(sid):
    p=os.path.join(FR,sid+'.csv')
    try:
        s=fred(sid)
        if os.path.exists(p): shutil.copy(p,p+'.bak')
        s.rename(sid).to_frame().to_csv(p)
        return s
    except Exception as e:
        if os.path.exists(p):
            print(f'home tiles: {sid} not refreshed ({str(e)[:50]}); the file on disk stands')
            return pd.read_csv(p,index_col=0,parse_dates=True).iloc[:,0].dropna()
        raise
from concurrent.futures import ThreadPoolExecutor as _TPE
with _TPE(max_workers=3) as _ex: S=dict(zip(SERIES,_ex.map(get,SERIES)))
def mon(d): return pd.Timestamp(d).strftime('%b %Y')
def day(d): return pd.Timestamp(d).date().isoformat()
U=S['UNRATE']; P=S['PAYEMS']; J=S['JTSJOL']; UE=S['UNEMPLOY']; Q=S['JTSQUR']; C=S['CPIAUCSL']; IC=S['ICSA']; IU=S['IURSA']
# UNITS, checked against FRED's own unit strings (11 September 2026):
#   UNRATE, IURSA, JTSQUR  percent          PAYEMS, JTSJOL, UNEMPLOY  thousands of persons
#   ICSA   persons (not thousands)          CPIAUCSL  index 1982-84=100
# so a level in thousands is divided by 1,000 and printed in millions, which is how a reader holds it.
g3=(P.iloc[-1]-P.iloc[-4])/3.0            # payroll growth, three-month average change, thousands
_c0=C.index[-1]-pd.DateOffset(years=1)    # the SAME month a year earlier, by date, never by position
assert _c0 in C.index, f'CPI has no observation for {_c0.date()}'
cpi=(C.iloc[-1]/C.loc[_c0]-1)*100
_um=J.index[-1]                           # unemployed per opening: BOTH series read at the SAME month
assert _um in UE.index, f'UNEMPLOY has no observation for {_um.date()}'
upo=UE.loc[_um]/J.loc[_um]
T=[
 dict(lab='Unemployment rate',      val=f'{U.iloc[-1]:.1f}%',              sub=mon(U.index[-1]),                    src='https://fred.stlouisfed.org/series/UNRATE'),
 dict(lab='Nonfarm payrolls',       val=f'{P.iloc[-1]/1000:,.1f} million',  sub=mon(P.index[-1]),                    src='https://fred.stlouisfed.org/series/PAYEMS'),
 dict(lab='Payroll growth',         val=f'{round(g3)*1000:+,.0f} a month', sub='3-month average, '+mon(P.index[-1]),src='https://fred.stlouisfed.org/series/PAYEMS'),
 dict(lab='Initial claims (week)',  val=f'{IC.iloc[-1]:,.0f}',             sub='week ending '+day(IC.index[-1]),    src='https://fred.stlouisfed.org/series/ICSA'),
 dict(lab='Insured unemployment rate',val=f'{IU.iloc[-1]:.1f}%',           sub='week ending '+day(IU.index[-1]),    src='https://fred.stlouisfed.org/series/IURSA'),
 dict(lab='Job openings',           val=f'{J.iloc[-1]/1000:,.1f} million',  sub=mon(J.index[-1]),                    src='https://fred.stlouisfed.org/series/JTSJOL'),
 dict(lab='Unemployed per opening', val=f'{upo:.2f}',                      sub=mon(_um),                    src='https://fred.stlouisfed.org/series/JTSJOL'),
 dict(lab='Quits rate',             val=f'{Q.iloc[-1]:.1f}%',              sub=mon(Q.index[-1]),                    src='https://fred.stlouisfed.org/series/JTSQUR'),
 dict(lab='CPI inflation',          val=f'{cpi:.1f}%',                     sub='year over year, '+mon(C.index[-1]), src='https://fred.stlouisfed.org/series/CPIAUCSL'),
]
_ID={"Unemployment rate":"UNRATE","Nonfarm payrolls":"PAYEMS","Payroll growth":"PAYEMS","Initial claims (week)":"ICSA",
     "Insured unemployment rate":"IURSA","Job openings":"JTSJOL","Unemployed per opening":"JTSJOL","Quits rate":"JTSQUR","CPI inflation":"CPIAUCSL"}
_DS={}; _NX={}
for _s in set(_ID.values()):
    _DS[_s]=release_dates(_s); _NX[_s]=next_release(_DS[_s])
# Three tiles are computed rather than read, so the link under them must say so: the number shown is not the
# series the link opens. CPI inflation is the exception that can be linked exactly — FRED's own year-over-year
# transformation of CPIAUCSL is the figure printed.
_LINK={'Payroll growth':'computed from PAYEMS',
       'Unemployed per opening':'UNEMPLOY \u00f7 JTSJOL',
       'CPI inflation':'CPIAUCSL, year over year'}
_SRC={'CPI inflation':'https://fred.stlouisfed.org/graph/?id=CPIAUCSL&transformation=pc1'}
for _t in T:
    _t["sid"]=_ID.get(_t["lab"]); _t["next"]=_NX.get(_t["sid"])
    _t["link"]=_LINK.get(_t["lab"],_t["sid"])
    if _t["lab"] in _SRC: _t["src"]=_SRC[_t["lab"]]
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
json.dump(out,open(_op,'w'),indent=1)
print('home tiles: '+(('CHANGED — '+'; '.join(_moved)) if _moved else 'unchanged')
      +f' | {len(T)} readings through {mon(U.index[-1])} (unemployment rate), {day(IC.index[-1])} (claims)'
      +'; next releases '+', '.join(f'{k} {v}' for k,v in sorted(_NX.items()) if v)+'; saved to collection 109')
