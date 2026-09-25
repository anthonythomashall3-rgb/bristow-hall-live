"""THE BRISTOW HALL SYSTEM (build v346 variant: walk-file split fixed for walks 69+) — the rule as a published series, and the forward log (collection 105, 8 September 2026).
Builds, from the lab's data as fetched, (1) the rule's reading: one number a month, the strongest branch of the peak
side of the version named in cache/bhs_version.json, at its walk-end lines, a branch reading being min(the proposer's largest ratio to its line over the last
four months, its best confirmer's largest ratio over the last six) - the rule's window read backward, so causal -
so that 1.00 is the line; read with the branches' arming for the distance to the next call and without it for the
reading inside a recession (the analogue of FRED's SAHMREALTIME); (2) the closing indicator: one number a week,
closer C's score at its walked lines, min(drop / 6, run / 3, hump / 20, max(S&P / 15, continued claims / 3, insured
rate / 3)), read only while an episode is open, kept in the state for the record; (3) the chronology the causal walk
named in cache/bhs_version.json produced; (4) every object's latest reading against its line, appended to the forward log LIVE_LOG_v321.tsv
(append-only); (5) bhs_state.json for the site: the one line (series), at most 0.99 outside a recession the rule
called and at least 1.00 inside, unsmoothed and uncapped.
Run from the collection 103/104 workspace: python3 bhs_build.py"""
import sys, io, contextlib, os, json, datetime, pickle
import time as _tm0; _TB0=_tm0.time(); _TBF=open(os.path.join('out','bhs_build_timing.txt'),'w') if os.path.isdir('out') else None
def _tick(lbl):
    try: _TBF.write('%7.1fs  %s\n'%(_tm0.time()-_TB0,lbl)); _TBF.flush()
    except Exception: pass
# THE WALK THE SITE STANDS ON is named in cache/bhs_version.json: {"walk": "walk39.py", "var": "w39", "version": "v3.22"}.
# Walks from walk39 on carry the walk loop behind the marker "# ---- the walk itself"; walk38 and before split at the
# "Y0,Y1,VAR=" line. The preamble defines the objects, the release-day functions and build_v.
_VF=os.environ.get('BHS_VERSION_FILE','cache/bhs_version.json')   # v3.55 staged builds name their version file (16 September 2026)
VERS=json.load(open(_VF)) if os.path.exists(_VF) else dict(walk='walk38.py',var='w38',version='v3.21')
WALK,VAR,VERSION=VERS['walk'],VERS['var'],VERS['version']
sys.argv=['x','2011','2012','wbhs']
_wsrc=open(WALK).read()
# THE SPLIT, MADE TO RECOGNISE EVERY WALK THAT EXISTS. Walks up to 55 carry the literal marker
# "# ---- the walk itself". Walks from 69 on build that string at run time (_MARK = "# ---- the walk "
# + "itself") precisely so their own text does not contain it, and end their preamble with
# exec(open('walk39.py').read().split(_MARK)[1] ...). The original split found neither and fell
# through to the whole file, which then RAN the walk under the throwaway name 'wbhs' and left this
# build reading an empty log. Found on 16 September 2026 staging v3.46; no walk after 55 had been built.
_TAILMARK = "exec(open('walk39.py').read().split(_MARK)[1]"
if "# ---- the walk itself" in _wsrc: src=_wsrc.split("# ---- the walk itself")[0]
elif _TAILMARK in _wsrc: src=_wsrc.split(_TAILMARK)[0]
else: src=_wsrc.split("Y0,Y1,VAR=int(sys.argv[1])")[0]
# v3.55: a `carry` axis on the leg loop (every vetted mechanism channel as a live leg) and the pending-proposal
# instrumentation (a leg proposal that has passed the record bar but whose core confirmation has not yet arrived).
_c_old = "    for _L in ((p.get('newlegs') or '') + (p.get('extra') or '')):"
if _c_old in src: src = src.replace(_c_old, "    for _L in ((p.get('newlegs') or '') + (p.get('extra') or '') + (p.get('carry') or '')):")
_p_old = "            _keep = [(a, b) for a, b in _prop\n                     if not any(s <= a <= e for s, e in _bars) and _accelerates(a)]\n            if _keep:\n                legs[_L] = _keep; _added = True"
assert src.count(_p_old) == 1, 'pending anchor (legs) not found'
src = src.replace(_p_old, _p_old + "\n            PENDING.extend([(a, b, _L) for a, b in _prop if not any(s <= a <= e for s, e in _bars) and not _accelerates(a)])")
_n_old = "            _keep = [(a, b) for a, b in _prop\n                     if not any(s <= a <= e for s, e in _bars) and _accelerates(a)]\n            if _keep:\n                legs['N'] = _keep; _added = True"
assert src.count(_n_old) == 1, 'pending anchor (N) not found'
src = src.replace(_n_old, _n_old + "\n            PENDING.extend([(a, b, 'N') for a, b in _prop if not any(s <= a <= e for s, e in _bars) and not _accelerates(a)])")
PENDING = []
# ---- THE BACKSTOP OPENER (20 September 2026, collection 256). The walk's text gains the block below inside build_v: with
# ---- _BS_ON set, the frozen rule's record is rebuilt with leg b = the gated backstop calls (s2/backstop.py writes them to
# ---- out/backstop_opener_calls.csv). The walk itself never sets _BS_ON, so the chooser and the walked diary are untouched.
_bs_old = '    if _added:\n        with contextlib.redirect_stdout(io.StringIO()): turns = B.american_chronology(legs, TL)"""'
_bs_new = '    if _BS_ON:\n        # THE BACKSTOP OPENER (20 September 2026, collection 256; Anthony\'s Q1 ruling): leg b may open what the core does not,\n        # once its union has been ON for a quarter; refused inside an open episode and for 183 days after a close.\n        if _added:\n            with contextlib.redirect_stdout(io.StringIO()):\n                turns = B.american_chronology(legs, TL)     # the core+legs record, for the spans below\n        _sp = []; _o = None\n        for x in turns:\n            if x[\'kind\'] == \'peak\' and _o is None: _o = x[\'published\']\n            elif x[\'kind\'] == \'trough\' and _o is not None: _sp.append((_o, x[\'published\'] + pd.Timedelta(days=183))); _o = None\n        if _o is not None: _sp.append((_o, pd.Timestamp(\'2100-01-01\')))\n        _keep = [(a, b) for a, b in _BS_CALLS if not any(s <= a <= e for s, e in _sp)]\n        if _keep: legs[\'b\'] = _keep; _added = True\n        # THE ACTIVITY OPENER (v3.60, 21 September 2026, collection 278; Core v6): leg P may open what the core does not, on\n        # the backstop opener\'s own bars (refused inside an open episode and for 183 days after a close).\n        _keepP = [(a, b) for a, b in _AO_CALLS if not any(s <= a <= e for s, e in _sp)]\n        if _keepP: legs[\'P\'] = _keepP; _added = True\n        # THE CONCURRENCE BRANCH (v3.68, 22 September 2026, collections 300 and 301): leg Y, on the same bars.\n        _keepY = [(a, b) for a, b in _CB_CALLS if not any(s <= a <= e for s, e in _sp)]\n        if _keepY: legs[\'Y\'] = _keepY; _added = True\n    if _added:\n        with contextlib.redirect_stdout(io.StringIO()): turns = B.american_chronology(legs, TL)"""'
assert src.count(_bs_old) == 1, 'backstop opener anchor not found once in the walk text'
src = src.replace(_bs_old, _bs_new)
_BS_ON = False; _BS_CALLS = []; _AO_CALLS = []; _CB_CALLS = []   # v3.60: the activity opener's calls (Core v6, collection 278); v3.68: the concurrence branch's
# ---- 17 September 2026 (Anthony: "make the overall refresh faster, as safe as possible"): the settling closers memoised
# ---- on disk. The walk heads (walk38, walk39, s2/asof_trough.py) rebuild the closer menus RC, TC, QC and the hours
# ---- object at every build - forty seconds of Python loops over monthly and weekly series that change only on claims
# ---- days and monthly release days. Each such function's result is now kept in cache/closers/, keyed on the function's
# ---- own code, its arguments and a fingerprint of every file those objects are built from (the claims files, the
# ---- vintage tables, the first prints, the release calendars, cache/objects.pkl); a changed input or a changed function
# ---- is a different key, so a hit is exactly what the function would have computed. The walk files on disk are not
# ---- touched: the decorator is added to their text as it is read.
import hashlib as _hl0, pickle as _pk0, glob as _gl0, builtins as _bi0
_bhs_real_open=_bi0.open
def _bhs_fingerprint():
    _R=os.path.expanduser('~/mnt/Onset Detector Data'); _L=os.path.join(_R,'24_bristow_rule_lab','workspace','lab')
    pats=[os.path.join(_L,'data','fred_weekly','*.csv'),os.path.join(_L,'vac','*.csv'),
          os.path.join(_R,'onset-detector-new-2026-08-23','27_realtime_vintages','alfred_all_vintages','*_all_vintages.csv'),
          os.path.join(_R,'186_realtime_channels_2026-09-15','vintages','*.csv'),os.path.join(_R,'45_dol_first_prints_2026-09','*.csv'),
          os.path.join(_R,'37_*','*.csv'),'cache/objects.pkl','cache/alfred_first_*.csv','cache/relcal_*.csv','cache/surveys/*.csv','cache/SAHMREALTIME.csv','s2/first_prints_early_1984_2002.csv']   # E66: the early first prints are an input
    h=_hl0.md5()
    for pat in pats:
        for f in sorted(_gl0.glob(pat)):
            h.update(f.encode())
            try: h.update(_hl0.md5(open(f,'rb').read()).digest())
            except Exception as e_:   # a file that cannot be read goes into the print as its size, time and error, never
                try: st_=os.stat(f); h.update(('UNREAD %d %f %s'%(st_.st_size,st_.st_mtime,type(e_).__name__)).encode())
                except Exception: h.update(('UNREAD ? %s'%type(e_).__name__).encode())   # silently, so two different files can never share a key
    return h.hexdigest()
_BHS_FP=_bhs_fingerprint(); _BHS_MEMO_DIR=os.path.join('cache','closers'); os.makedirs(_BHS_MEMO_DIR,exist_ok=True)
_BHS_MEMO_STATS={'hit':0,'miss':0,'passed':0}
for _f in _gl0.glob(os.path.join(_BHS_MEMO_DIR,'*.pkl')):   # results not used for three days (a hit touches its file) go
    try:
        if _tm0.time()-os.path.getmtime(_f)>3*86400: os.remove(_f)
    except Exception: pass
def _bhs_obj_hash(v,h,seen,depth=0):
    # the content of a data object a memoised function reads, into the running hash: a pandas object by its values and
    # index, a container by its members, a function by its code and, recursively, by everything it reads
    if hasattr(v,'index') and hasattr(v,'values') and hasattr(v,'dtype') or (hasattr(v,'index') and hasattr(v,'values') and hasattr(v,'columns')):
        try:   # a numeric or datetime block by its bytes (C speed); anything else through pandas' own row hash
            import pandas as _pdx, numpy as _npx; _vals=v.values
            if getattr(_vals,'dtype',None) is not None and _vals.dtype.kind in 'biufcMm': h.update(_npx.ascontiguousarray(_vals).tobytes()); h.update(repr(_vals.shape).encode())
            else: h.update(_pdx.util.hash_pandas_object(v,index=False).values.tobytes())
            _ix=v.index.values
            if _ix.dtype.kind in 'biufcMm': h.update(_npx.ascontiguousarray(_ix).tobytes())
            else: h.update(repr(list(_ix)).encode())
            if hasattr(v,'columns'): h.update(repr(list(v.columns)).encode())
            return
        except Exception as e_: raise TypeError('pandas object not hashed for the memo key (%s): %s'%(type(v).__name__,str(e_)[:60]))   # the call then runs unmemoised
    if isinstance(v,(int,float,str,bool,bytes,type(None))): h.update(repr(v).encode()); return
    if type(v).__name__=='ndarray':
        if v.dtype.kind=='O': h.update(repr(v.tolist()).encode()); return   # object arrays by their members, never by their pointers
        h.update(v.tobytes()); h.update(repr(v.shape).encode()); return
    if type(v).__name__ in ('Index','DatetimeIndex','Int64Index','RangeIndex','PeriodIndex'): h.update(repr(list(v)).encode()); return
    if isinstance(v,dict):
        h.update(b'{')
        for k_ in sorted(v,key=repr): h.update(repr(k_).encode()); _bhs_obj_hash(v[k_],h,seen,depth+1)
        h.update(b'}'); return
    if isinstance(v,(list,tuple)):
        h.update(b'[')
        for x_ in v: _bhs_obj_hash(x_,h,seen,depth+1)
        h.update(b']'); return
    if isinstance(v,(set,frozenset)): h.update(repr(sorted(v,key=repr)).encode()); return
    _f=getattr(v,'_bhs_fn',None)
    if _f is not None: _bhs_fn_hash(_f,h,seen,depth+1); return
    if callable(v) and hasattr(v,'__code__'): _bhs_fn_hash(v,h,seen,depth+1); return
    if type(v).__name__ in ('Timestamp','Timedelta','datetime','date','DateOffset','timedelta','Pattern'): h.update(repr(v).encode()); return
    import types as _ty0, io as _io0
    if isinstance(v,_ty0.MethodType): _bhs_fn_hash(v.__func__,h,seen,depth+1); _bhs_obj_hash(v.__self__,h,seen,depth+1); return   # a bound method: its code and the object it is bound to
    if isinstance(v,(_ty0.ModuleType,type,_ty0.BuiltinFunctionType,_ty0.BuiltinMethodType,_io0.IOBase)): h.update(type(v).__name__.encode()); return   # a module, a class, a builtin, a file: its kind only
    raise TypeError('object not hashed for the memo key: '+type(v).__name__)   # the call then runs unmemoised, and the summary line names it
def _bhs_code_hash(c,h):
    # a code object by its bytecode and constants; a nested code object (a lambda, a comprehension) the same way, never
    # by its repr, which carries a memory address
    h.update(c.co_code); h.update(repr(c.co_names).encode())
    for k_ in c.co_consts:
        if hasattr(k_,'co_code'): _bhs_code_hash(k_,h)
        else: h.update(repr(k_).encode())
def _bhs_names(c,acc):
    # every global name a code object reads, including those read only inside its lambdas and nested functions
    acc.update(c.co_names)
    for k_ in c.co_consts:
        if hasattr(k_,'co_code'): _bhs_names(k_,acc)
    return acc
def _bhs_fn_hash(fn,h,seen,depth):
    if id(fn) in seen or depth>12: return
    seen.add(id(fn)); c=fn.__code__
    _bhs_code_hash(c,h)
    g=fn.__globals__
    for n in sorted(_bhs_names(c,set())):
        if n in g: h.update(n.encode()); _bhs_obj_hash(g[n],h,seen,depth+1)
def _BHS_MEMO(fn):
    def w(*a,**k):
        if any(hasattr(x,'index') and hasattr(x,'values') for x in list(a)+list(k.values())): _BHS_MEMO_STATS['passed']+=1; return fn(*a,**k)
        try:
            h=_hl0.md5(); _bhs_fn_hash(fn,h,set(),0); h.update(repr((a,sorted(k.items()),_BHS_FP)).encode()); key=h.hexdigest()
        except Exception as e_:   # no key could be made (an object of a kind the hash does not cover): computed as before, never cached
            _BHS_MEMO_STATS['unkeyed']=_BHS_MEMO_STATS.get('unkeyed',0)+1; _BHS_MEMO_STATS.setdefault('unkeyed_names',set()).add(fn.__name__+' ('+str(e_)[:70]+')'); return fn(*a,**k)
        p=os.path.join(_BHS_MEMO_DIR,fn.__name__+'_'+key+'.pkl')
        if os.path.exists(p):
            try:
                r=_pk0.load(_bhs_real_open(p,'rb')); _BHS_MEMO_STATS['hit']+=1; os.utime(p,None); return r
            except Exception: pass
        r=fn(*a,**k); _BHS_MEMO_STATS['miss']+=1; _BHS_MEMO_STATS.setdefault('missed',[]).append(fn.__name__+repr(a)[:30]+repr(sorted(k.items()))[:40])
        try: _pk0.dump(r,_bhs_real_open(p+'.tmp','wb')); os.replace(p+'.tmp',p)
        except Exception: pass
        return r
    w.__name__=fn.__name__; w.__doc__=fn.__doc__; w._bhs_fn=fn; return w
_BHS_MEMO_NAMES=('_settle_calls','_settle_starts','_qleg','_confirm_close','_guard_ur','hours_asof','_settle_starts_asof','_settle_calls_asof','_qleg_asof','_confirm_close_asof','_guard_ur_asof')
def open(f,*a,**k):   # every walk file read from here on (the heads exec each other by name) gets the decorator in memory
    mode=a[0] if a else k.get('mode','r')
    if isinstance(f,str) and f.endswith('.py') and 'r' in mode and 'b' not in mode and 'w' not in mode and 'a' not in mode:
        txt=_bhs_real_open(f,*a,**k).read()
        for n in _BHS_MEMO_NAMES: txt=txt.replace('\ndef %s('%n,'\n@_BHS_MEMO\ndef %s('%n)
        return io.StringIO(txt)
    return _bhs_real_open(f,*a,**k)
# ---- E66 (24 September 2026; collections 396, 399, 382; the perfection plan's Gap 1): THE WEEKLY CLAIMS FIRST PRINTS FROM JANUARY 1985. Collection 45,
# ---- the Department's own release archive, begins on 17 October 2002; the bound news releases (1985-2001), the bound volumes (1994-2009) and the
# ---- Internet Archive's captures (1996-2011) carry the release as printed back to the last week of 1984, checked against 45 week for week where
# ---- they overlap (340/340, 240/240 and 414/414 weeks identical). s2/first_prints_early_1984_2002.csv is that early table, static; it is put in
# ---- front of 45's live file at every build (cache/national_first_prints_1985_live.csv, rewritten only when either changes) and every reader of
# ---- 45's national file reads the merged file through the substitute door. The rule does not change; on the record one label moves (the 2001
# ---- opening of 15 March 2001 is made by U as well as I, the same day) and the revision drill's exposure ends in 1984. BHS_FIRSTPRINTS_OFF=1
# ---- reads 45 alone, for a cmpstate.
FIRSTPRINTS={'active':False}
try:
    import pandas as _pd66
    _e66_early=os.path.join('s2','first_prints_early_1984_2002.csv')
    if os.path.exists(_e66_early) and not os.environ.get('BHS_FIRSTPRINTS_OFF'):
        _root66=next(r for r in (os.path.expanduser('~/Projects/Onset Detector Data'),os.path.expanduser('~/mnt/Onset Detector Data')) if os.path.isdir(r))
        _p45live=os.path.join(_root66,'45_dol_first_prints_2026-09','national_first_prints.csv')
        _early66=_pd66.read_csv(_e66_early,dtype=str).fillna(''); _live66=_pd66.read_csv(_p45live,dtype=str).fillna('')
        _first45=_pd66.to_datetime(_live66['release_date']).min()
        _early66=_early66[_pd66.to_datetime(_early66['release_date'])<_first45]          # the early table ends where 45 begins
        _cols66=list(_live66.columns)
        for _c in _cols66:
            if _c not in _early66.columns: _early66[_c]=''
        _live66['source']='45'; _live66['fills']=''
        _merged66=_pd66.concat([_early66[_cols66+['source','fills']],_live66[_cols66+['source','fills']]],ignore_index=True)
        os.makedirs('cache',exist_ok=True); _pm66=os.path.join('cache','national_first_prints_1985_live.csv'); _txt66=_merged66.to_csv(index=False)
        if not os.path.exists(_pm66) or _bhs_real_open(_pm66).read()!=_txt66:
            with _bhs_real_open(_pm66,'w') as _fh66: _fh66.write(_txt66)
        FIRSTPRINTS=dict(active=True,file=_pm66,early_table=_e66_early,early_weeks=int(len(_early66)),early_from=str(_early66['ic_week_ended'].min()),early_to=str(_early66['ic_week_ended'].max()),
                         live_rows=int(len(_live66)),sources={k:int(v) for k,v in _early66['source'].value_counts().items()},
                         note='the weekly claims first prints from the last week of 1984: the bound news releases (399), the bound volumes (396), the Archive (382); current series where marked')
        print('E66: weekly claims first prints from %s: %d early weeks in front of 45\'s %d rows (%s)'%(FIRSTPRINTS['early_from'],FIRSTPRINTS['early_weeks'],FIRSTPRINTS['live_rows'],FIRSTPRINTS['sources']))
except Exception as _e66:
    FIRSTPRINTS={'active':False,'note':'did not run (%r)'%(_e66,)}; print('E66 first prints not applied:',_e66)
# ---- collection 329 (23 September 2026; the plan's Step 3b, the risks register R1): THE CLAIMS SUBSTITUTE. When the Department's weekly
# ---- release is stale (no advance week for more than 13 days) the national claims the proposers and the closer read are rebuilt for the
# ---- missing weeks from the states' own ETA 539 file (s2/claims_substitute.py: the state sum, the Bureau's published factor), flagged
# ---- kind='substitute' and dropped again when the release resumes. A drill (BHS_CLAIMS_DARK_FROM=YYYY-MM-DD [BHS_CLAIMS_DARK_WEEKS=n])
# ---- cuts the real prints from that week and substitutes them, to show what the rule would have done through a shutdown. Inert otherwise:
# ---- a build with the release current reads exactly the file it read before (cmpstate).
CLAIMS_SUB={'active':False}
try:
    import pandas as pd
    import importlib.util as _iu329
    _sp329=_iu329.spec_from_file_location('claims_substitute',os.path.join('s2','claims_substitute.py')); _cs329=_iu329.module_from_spec(_sp329); _sp329.loader.exec_module(_cs329)
    if FIRSTPRINTS.get('active'): _cs329.N45=FIRSTPRINTS['file']   # E66: a substituted build keeps the early weeks
    _n329=pd.read_csv(_cs329.N45,parse_dates=['ic_week_ended'])
    _last329=pd.Timestamp(_n329['ic_week_ended'].max()); _age329=(pd.Timestamp(datetime.date.today())-_last329).days
    _dark329=os.environ.get('BHS_CLAIMS_DARK_FROM'); _dw329=os.environ.get('BHS_CLAIMS_DARK_WEEKS')
    if _dark329 or _age329>13:
        _mp329,_info329=_cs329.merged_file(os.path.join('cache','claims_merged.csv'),dark_from=_dark329,dark_weeks=(int(_dw329) if _dw329 else None))
        if _mp329:
            CLAIMS_SUB=dict(active=True,drill=bool(_dark329),**_info329)
            _real_read_csv329=pd.read_csv
            def _rc329(f,*a,**k):
                if isinstance(f,str) and f.endswith('45_dol_first_prints_2026-09/national_first_prints.csv'): f=_mp329
                return _real_read_csv329(f,*a,**k)
            pd.read_csv=_rc329
            _BHS_MEMO_DIR=os.path.join('cache','closers_sub'); os.makedirs(_BHS_MEMO_DIR,exist_ok=True)   # the memo of a substituted build never mixes with the record's
            print('329 claims substitute ACTIVE (%s): release through %s; substitute weeks %s; factors %s'%('drill' if _dark329 else 'the release is %d days old'%_age329,_info329['last_release_week'],_info329['substitute_weeks'],_info329['factors']))
except Exception as _e329:
    print('329 claims substitute not applied:',_e329)
# ---- v3.73 (23 September 2026, collection 333; collection 330): THE JOLTS -> INDEED BRIDGE. When a scheduled JOLTS month has not printed (at most two), the
# ---- vacancy object's first-print file, its release calendar and the labour force are read from bridged copies that carry the missing
# ---- months on the Indeed postings index (s2/vacancy_bridge.py); flagged in the state; inert when every month has printed. Drill:
# ---- BHS_JOLTS_DARK_MONTHS=n cuts the last n printed months.
VAC_BRIDGE={'active':False}
try:
    import importlib.util as _iu333
    _spv=_iu333.spec_from_file_location('vacancy_bridge',os.path.join('s2','vacancy_bridge.py')); _vb333=_iu333.module_from_spec(_spv); _spv.loader.exec_module(_vb333)
    _dm333=os.environ.get('BHS_JOLTS_DARK_MONTHS')
    VAC_BRIDGE=_vb333.bridge(datetime.date.today(),dark_months=(int(_dm333) if _dm333 else None))
    _BR_MAP={}   # every file the exec reads through a substitute door: {suffix of the path as read: the file to read instead}
    if VAC_BRIDGE.get('active'):
        _BR_MAP.update({'cache/alfred_first_JTSJOL.csv':VAC_BRIDGE['paths']['jolts'],'cache/relcal_JTSJOL.csv':VAC_BRIDGE['paths']['relcal'],'cache/alfred_first_CLF16OV.csv':VAC_BRIDGE['paths']['clf'],'JTSJOL_all_vintages.csv':VAC_BRIDGE['paths']['vintages']})
        _BHS_MEMO_DIR=os.path.join('cache','closers_bridge'); os.makedirs(_BHS_MEMO_DIR,exist_ok=True)   # a bridged build's memo never mixes with the record's
        print('v3.73 vacancy bridge ACTIVE:',VAC_BRIDGE.get('note'))
    else: print('v3.73 vacancy bridge:',VAC_BRIDGE.get('note'))
except Exception as _e333:
    VAC_BRIDGE={'active':False,'note':'did not run (%r)'%(_e333,)}; _BR_MAP={}; print('v3.73 vacancy bridge not applied:',_e333)
# ---- THE REVISION DRILL (collection 334, 23 September 2026; plan item 13, R10): BHS_REVISION_SEED=<n>[:all] rebuilds the pre-first-print claims
# ---- histories with revisions drawn from the Department's real ones (s2/revision_drill.py) and reads them through the same doors. Never set on a runner.
REV_DRILL={'active':False}
try:
    _rs334=os.environ.get('BHS_REVISION_SEED')
    if _rs334:
        import importlib.util as _iu334
        _spr=_iu334.spec_from_file_location('revision_drill',os.path.join('s2','revision_drill.py')); _rd334=_iu334.module_from_spec(_spr); _spr.loader.exec_module(_rd334)
        _seed,_mode=(_rs334.split(':')+['typical'])[:2]
        REV_DRILL=dict(active=True,**_rd334.draw(_seed,_mode)); _BR_MAP.update(REV_DRILL['paths'])
        _BHS_MEMO_DIR=os.path.join('cache','closers_revision_%s_%s'%(_seed,_mode)); os.makedirs(_BHS_MEMO_DIR,exist_ok=True)
        print('REVISION DRILL ACTIVE:',{k:(v['weeks_perturbed'],round(v['draw_mean'],4),round(v['draw_sd'],4)) for k,v in REV_DRILL['series'].items()})
except Exception as _e334:
    REV_DRILL={'active':False,'note':'did not run (%r)'%(_e334,)}; print('revision drill not applied:',_e334)
# ---- R17 (24 September 2026, collection 378): THE BAD-PRINT DRILL. BHS_BADPRINT=<col>:<factor>[:<weeks_back>] multiplies one week's print
# ---- (icsa | iusa | iur_sa; the latest week by default, or weeks_back weeks earlier) in a COPY of the Department's first-print file and reads
# ---- it through the same door as the substitute and the revision drill (_BR_MAP). Never set on a runner; inert otherwise (cmpstate identical).
BADPRINT={'active':False}
try:
    _bp378=os.environ.get('BHS_BADPRINT')
    if _bp378:
        _parts378=(_bp378.split(':')+['1','0'])[:3]; _col378=_parts378[0]; _fac378=float(_parts378[1]); _wb378=int(_parts378[2])
        assert _col378 in ('icsa','iusa','iur_sa'), 'BHS_BADPRINT column must be icsa, iusa or iur_sa'
        import pandas as _pd378
        _root378=next(r for r in (os.path.expanduser('~/Projects/Onset Detector Data'),os.path.expanduser('~/mnt/Onset Detector Data')) if os.path.isdir(r))
        _p45=os.path.join(_root378,'45_dol_first_prints_2026-09','national_first_prints.csv'); _n378=_pd378.read_csv(_p45,dtype=str)
        _key378='ic_week_ended' if _col378=='icsa' else 'iu_week_ended'
        _val378=_pd378.to_numeric(_n378[_col378],errors='coerce'); _ok378=_n378[_val378.notna()].copy(); _ok378['_d']=_pd378.to_datetime(_ok378[_key378])
        _idx378=_ok378.sort_values('_d').index[-1-_wb378]
        _before378=float(_val378.loc[_idx378]); _after378=round(_before378*_fac378,1) if _col378=='iur_sa' else float(round(_before378*_fac378))
        _n378.loc[_idx378,_col378]=('%.1f'%_after378) if _col378=='iur_sa' else ('%.1f'%_after378 if _n378.loc[_idx378,_col378].endswith('.0') else str(int(_after378)))
        os.makedirs(os.path.join('cache','badprint'),exist_ok=True); _pbp378=os.path.join('cache','badprint','national_first_prints_%s_x%g_w%d.csv'%(_col378,_fac378,_wb378)); _n378.to_csv(_pbp378,index=False)
        BADPRINT=dict(active=True,column=_col378,factor=_fac378,weeks_back=_wb378,week=str(_ok378.loc[_idx378,'_d'].date()),before=_before378,after=_after378,file=_pbp378)
        _BR_MAP['45_dol_first_prints_2026-09/national_first_prints.csv']=_pbp378
        _BHS_MEMO_DIR=os.path.join('cache','closers_badprint'); os.makedirs(_BHS_MEMO_DIR,exist_ok=True)   # a drilled build's memo never mixes with the record's
        print('R17 BAD-PRINT DRILL ACTIVE:',{k:v for k,v in BADPRINT.items() if k!='file'})
except Exception as _e378:
    BADPRINT={'active':False,'note':'did not run (%r)'%(_e378,)}; print('bad-print drill not applied:',_e378)
if FIRSTPRINTS.get('active') and not CLAIMS_SUB.get('active') and '45_dol_first_prints_2026-09/national_first_prints.csv' not in _BR_MAP:
    _BR_MAP['45_dol_first_prints_2026-09/national_first_prints.csv']=FIRSTPRINTS['file']   # E66: every reader of 45's national file reads the merged table (the substitute, when active, already carries it; a drill's own copy wins)
if _BR_MAP:
    def _br333(f):
        if isinstance(f,str):
            for _key,_val in _BR_MAP.items():
                if f.endswith(_key): return _val
        return f
    _real_read_csv333=pd.read_csv
    def _rc333(f,*a,**k): return _real_read_csv333(_br333(f),*a,**k)
    pd.read_csv=_rc333
    _open_before333=open   # the memo-injecting open above; the as-of vacancy object reads its vintage table through it, mini.py its pickle
    def open(f,*a,**k): return _open_before333(_br333(f),*a,**k)
with contextlib.redirect_stdout(io.StringIO()): exec(src)
if _BR_MAP: pd.read_csv=_real_read_csv333
open=_bhs_real_open
if CLAIMS_SUB.get('active'): pd.read_csv=_real_read_csv329
print('closers memo: %d hit, %d recomputed, %d passed, %d unkeyed (fingerprint %s)'%(_BHS_MEMO_STATS['hit'],_BHS_MEMO_STATS['miss'],_BHS_MEMO_STATS['passed'],_BHS_MEMO_STATS.get('unkeyed',0),_BHS_FP[:8])+('; recomputed: '+'; '.join(_BHS_MEMO_STATS.get('missed',[])[:8]) if _BHS_MEMO_STATS['miss'] else '')+('; UNKEYED: '+'; '.join(sorted(_BHS_MEMO_STATS['unkeyed_names'])) if _BHS_MEMO_STATS.get('unkeyed') else ''))
_tick('exec walk94 head')
out.close()
# ---- v3.70 (22 September 2026, collection 303; PREREG-the-four-round4 A4; Rule Zero): THE CONTINUED-CLAIMS CLOSER DATED BY ITS RELEASE. The lab's
# ---- K published each call five days after the continued-claims week that fired, but a week's continued claims are released a
# ---- week later, with the next week's initial claims (rel_iu: the Thursday twelve days after the week ends). Every K call is
# ---- re-dated to rel_iu of its week, so a close by K is never stamped before its data were public.
_K370=[_p-pd.Timedelta(days=5) for _p,_d in TLH['K']]
assert all(_w.weekday()==5 for _w in _K370), 'v3.70: a K call is not dated five days after a Saturday'
_K370_OLD=list(TLH['K']); TLH=dict(TLH); TLH['K']=sorted((rel_iu(_w),_d) for _w,(_p,_d) in zip(_K370,_K370_OLD))
print('v3.70: K dated by its release: %d calls; first %s (was %s)'%(len(TLH['K']),(str(TLH['K'][0][0].date()) if TLH['K'] else None),(str(_K370_OLD[0][0].date()) if _K370_OLD else None)))
# ---- v3.71 (22 September 2026, collection 310; PREREG-v371-port; E29): CLOSER C'S FOURTH CONFIRMATION, THE STRONG FLOW. C closes when initial claims
# ---- have fallen from their 26-week maximum (the 3-week mean's drop at its line, a hump of 20, a run of n weeks) and a confirmation holds:
# ---- the S&P 500 above its 130-day low by its line, continued claims down 3, or the insured rate down 0.3. E29 adds a fourth: the drop
# ---- at least 15 log points with a run of at least 6 weeks and the S&P 500 at least 10 per cent above its low. The menu is rebuilt
# ---- here, after the walk preamble; with the strong flow off it must equal the preamble's menu.
_CMENU370={_k:list(_v) for _k,_v in CMENU.items()}
def closer_C(D,n,s,A=20.0,c=3.0,u=3,need=1,k=1,pub_cc=12,cool=26,Ds=15.0,Ns=6,Ms=10.0,strong=True):
    prop=(_FI['drop'].values>=D)&(_FI['amp'].values>=A)&(_FI['run'].values>=n)
    sp_=np.nan_to_num(_Csp,nan=-99); fc_=np.nan_to_num(_Cfc,nan=-99); du_=np.nan_to_num(_Cdu,nan=-99)
    hs=(sp_>=s).astype(int)+(fc_>=c).astype(int)+(du_>=u).astype(int)
    if strong: hs=hs+((_FI['drop'].values>=Ds)&(_FI['run'].values>=Ns)&(sp_>=Ms)).astype(int)
    ok=np.where(prop&(hs>=need))[0]; calls=[]; last_=None
    for i in ok:
        t=_CW[i]
        if last_ is not None and t<last_+pd.Timedelta(weeks=cool): continue
        pub=_CpI[i]
        pm=_c_peak(t); dated=pd.Timestamp(pm.year,pm.month,1)+pd.DateOffset(months=k)
        if fc_[i]>=c:
            seg=_LCC[(_LCC.index<=_Ctc[i])&(_LCC.index>_Ctc[i]-pd.Timedelta(weeks=26))]
            if len(seg):
                cm=seg.idxmax(); cmm=pd.Timestamp(cm.year,cm.month,1)
                if cmm>dated: dated=cmm
        calls.append((pub,dated)); last_=t
    return calls
assert {_k:closer_C(*_k,strong=False) for _k in _CMENU370}=={_k:list(_v) for _k,_v in _CMENU370.items()}, 'v3.71: the rebuilt C with the strong flow off is not the live C'
CMENU={_k:closer_C(*_k) for _k in _CMENU370}
print('v3.71: C with the strong-flow confirmation (E29) on %d lines; at (6,3,15) %d closes (was %d), the last three %s'%(len(CMENU),len(CMENU[(6,3,15)]),len(_CMENU370[(6,3,15)]),[str(a.date()) for a,b in CMENU[(6,3,15)][-3:]]))
# ---- v3.55: the carried legs, built exactly as legs E/S/T/Z/c/m are, from the declared table ----
import csv as _csv
_CONF86.update({'mfg_emp_falling': ('MANEMP', _PCTDN), 'unrate_rising': ('UNRATE', _RISE), 'overtime_falling': ('AWOTMAN', _FALL), 'freight_cars_falling': ('M03002USM544NNBR', _PCTDN)})
_DFN = {'rise': _RISE, 'fall': _FALL, 'pct_up': _PCTUP, 'pct_down': _PCTDN}
CARRY_TABLE = list(_csv.DictReader(open(os.path.join(_ROOT, '189_walk_from_1948_2026-09-16', 'out', 'v355', 'v355_carried_legs.csv'))))   # the declared table, on the Mac (16 Sep 2026)
CARRY_EXCLUDED = {'HOUST1F': 'a false alarm in June 2023 and a call 235 days early in 1979 under the arming bar', 'TOTBORR': 'proposals of May 1995 and May 1998 that lapsed (real-time false alarms)'}
CARRY = {}
for _r in CARRY_TABLE:
    if _r['channel'] in CARRY_EXCLUDED: continue
    _L = _r['letter']
    NEW_LEGS[_L] = _load_leg86(_r['channel'], _DFN[_r['direction']], int(_r['p_horizon']), int(_r['p_q']), int(_r['p_win']), int(_r['p_hold']), _r['confirmer'], int(_r['c_horizon']), int(_r['c_q']), int(_r['c_hold']))
    CARRY[_L] = _r
CARRY_LETTERS = ''.join(CARRY.keys())
print('v3.55 carried legs:', len(CARRY), 'excluded:', sorted(CARRY_EXCLUDED))
# ---- v3.56 (16 September 2026): the high-frequency transmission legs of collection 190 -- payments (withheld taxes,
# ---- UI benefits paid, customs duties, corporate taxes), physical activity (petroleum supplied, gasoline stocks),
# ---- plumbing (OFR stress), credit cost (30-year mortgage rate), equity tail (VVIX, SKEW), attention (EPU, GPR) --
# ---- daily or weekly and never revised, screened and null-tested in collection 190 (hf_screen, hf_null), walked in
# ---- walk 96 (PREREG-v356), carried under the v3.55 protocol: leg - (VVIX x hours) leaves the walked record unchanged
# ---- and is carried; the eleven others would have moved a past call and are armed from 2026-09-16, backtest shown.
import pandas as _pd
sys.path.insert(0, os.path.join(_ROOT, '190_month_standard_and_hf_legs_2026-09-16', 'code'))
import hf_legs as _HF
_HFT = list(_csv.DictReader(open(os.path.join(_ROOT, '190_month_standard_and_hf_legs_2026-09-16', 'out', 'v356_hf_carried_legs.csv'))))
_HFP = _HF.build(_pd.DataFrame(_HFT))
_HF_ROUTE = {'withheld': 'payments: withheld taxes (daily)', 'customs': 'trade: customs duties (daily)', 'gpr': 'attention: geopolitical risk (daily)',
             'corptax': 'payments: corporate taxes (daily)', 'ofr': 'plumbing: OFR financial stress (daily)', 'petroleum': 'physical: petroleum supplied (weekly)',
             'gasolinestocks': 'physical: gasoline stocks (weekly)', 'vvix': 'equity tail: VVIX (daily)', 'uibenefits': 'payments: UI benefits paid (daily)',
             'epu': 'attention: policy uncertainty (daily)', 'skew': 'equity tail: SKEW (daily)', 'mortgage': 'credit cost: 30-year mortgage rate (weekly)'}
for _r in _HFT:
    _L = _r['letter']; NEW_LEGS[_L] = _HFP[_L]
    CARRY[_L] = dict(letter=_L, channel=_r['proposer'], mechanism=_HF_ROUTE.get(_r['family'], _r['family']), direction=_r['direction'], p_horizon=_r['p_horizon'],
                     p_q=_r['p_q'], p_win=_r['p_win'], p_hold=_r['p_hold'], confirmer=_r['confirmer'], c_horizon=_r['c_horizon'], c_q=_r['c_q'], c_hold=_r['c_hold'],
                     screen_peaks=_r['wide'], n_proposals=str(len(_HFP[_L])), proposals=_r['proposals'], carried=_r['carried'], lapsed_proposals=_r['lapsed_proposals'])
    CARRY_TABLE.append(CARRY[_L])
CARRY_LETTERS = ''.join(CARRY.keys())
print('v3.56 high-frequency legs:', len(_HFT), 'carried unchanged:', [r['letter'] for r in _HFT if r['carried'] == 'True'])
# ---- v3.57 (20 September 2026, collection 260; Anthony: 'get rid of legs completely if it makes our tool more reliable'):
# ---- THE LEG TIER IS RETIRED. The carried legs stay loaded for the data page but none is armed; the walk (walk97.py, memo w357)
# ---- carries no leg axis; the rule calls with its core alone. Walk 97: zero false alarms, 2007 -7, 2020 +12, 2024 +3, the rest as before.
CARRY = {}; CARRY_TABLE = []; CARRY_LETTERS = ''
print('v3.57: no leg tier; the rule calls with its core alone')

import numpy as np, pandas as pd
CFG=pickle.load(open(f'cache/{VAR}_carry.pkl','rb'))          # the configuration the walk ended on
LIVE=VERS.get('live') or os.path.join(os.environ['HOME'],'mnt','Onset Detector Data','105_bristow_hall_system_2026-09-08')
os.makedirs(os.path.join(LIVE,'live'),exist_ok=True)
today=datetime.date.today()
# ---- the opening indicator: branch scores over their lines ----
p=CFG
# THE HUB'S HOLD AS THE WALK READS IT. From walk40 the hub X fires when the Sahm gap (as published) is at its line and the
# vacancy gap stood at its line in two of the prior nine months AND in the latest JOLTS print known that day. From walk54
# (v3.28, 10 September 2026) 'still falling' is the latest print at the line OR the vacancy at the line in a majority - five
# or more - of the window's prints as published by the day (the hold's own window; no new line). The reading follows the
# walk the site stands on: HUB_MAJ is the majority count when the walk carries the clause, None otherwise.
# (v3.29, 11 September 2026) the clause is looked for in the whole chain of walk files the walk execs, not in its own text
# alone: walk55.py carries walk54's preamble by exec, and reading walk55's text alone had left HUB_MAJ None in the first
# v3.29 build - the 3 May 2024 open day then read 0.933 under a held 1.00 (caught by the site audit; Rule Zero).
import re as _re
def _walk_chain(path,seen=None):
    seen=seen if seen is not None else set()
    if path in seen or not os.path.exists(path): return ''
    seen.add(path); t=open(path).read()
    # v3.57 (20 Sep 2026): walk94/97 carry walk54's preamble by `_hdr = open('walk54.py').read()` (no exec( prefix), which the
    # old pattern missed - HUB_MAJ then read None and the majority-hold reading was not carried. Any open() of a walk file counts.
    return t+''.join(_walk_chain(m,seen) for m in _re.findall(r"open\('(walk\w+\.py)'\)",t))
_wchain=_walk_chain(WALK)
HUB_MAJ=5 if ('len(hitk)>=5' in _wchain or 'len(hit)>=5' in _wchain) else None
_RELU=globals().get('relU',globals().get('rel')); _RELJ=globals().get('relJ'); _RELH=globals().get('relH')
_SCHED={}
try:
    for _r in pd.read_csv('cache/release_schedule.csv').itertuples():
        _SCHED[(_r.series,pd.Timestamp(_r.reference_month))]=pd.Timestamp(_r.release_date)
except Exception: pass
_CALNAME={id(globals().get('relU')):'UNRATE',id(globals().get('relJ')):'JTSJOL',id(globals().get('relH')):'HOUST'}
def _rel(cal,m,default_days):
    """the release day of month m's print: the lab's calendar, else the published schedule, else the usual timing"""
    if cal is not None and m in cal.index and not pd.isna(cal[m]): return pd.Timestamp(cal[m])
    k=(_CALNAME.get(id(cal)),m)
    if k in _SCHED: return _SCHED[k]
    return pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=default_days)
# RULE ZERO, 8 September 2026 - the hours pair's publication day. The lab's mkhours dates each month's reading the
# fifth of the following month (pub_day=5); the Employment Situation comes out on the first Friday, the 1st to the
# 7th. One call in the causal diary was confirmed by the hours pair, 2020, and carried 5 May 2020; the April 2020
# report was released on 8 May 2020. From here the pair is dated by the release calendar (relU), so the frozen run,
# the site's chronology and the daily reading all carry the true day; the month, May 2020, is unchanged.
if '_mkhours0' not in globals():                 # walk38's preamble already dates the pair by the calendar; walk37's did not
    _mkhours0=mkhours
    def mkhours(h1,h2):
        d=dict(_mkhours0(h1,h2)); d['pubs']=pd.Series({m:_rel(_RELU,m,4) for m in d['gap'].index}); d.pop('pub_day',None); return d
G=vgap2_asof(p['vk'],p['vb']); Hc=(mkpair_either_asof(p['hline']) if 'mkpair_either_asof' in globals() else mkpair_asof(p['hline'])); MX=(Hc['mx'] if 'mx' in Hc else mkpair_asof(p['hline'])['mx']); Hh=HOURS_ASOF   # v3.27 (walk51): the pair on starts or permits
_pubsV=pd.Series({m:_rel(_RELJ,m,29) for m in G.index}); SVc=mkpair_sv_asof(G,_pubsV,p['vl'])   # the starts x vacancy pair, the weak proposers' third confirmer
# ---- v3.72 (22 September 2026, collection 311; E31): THE STATE SAHM BREADTH, THE SECOND OPENER. The share of states whose own Sahm gap - the three-month
# ---- average of the state's unemployment rate above its twelve-month low, on first prints - stands at or above 0.70 fires when
# ---- at least 40 per cent of the states are there; it opens an episode only if the vacancy gap stood at its line in two of the
# ---- prior months, the condition the national hub already carries, and only when the rule has stood closed for a quarter, the
# ---- backstop's own rule. s2/state_breadth.py writes out/state_breadth.json before the build.
SB_ST={}; SB_OPENER=[]
try:
    SB_ST=json.load(open('out/state_breadth.json')) if os.path.exists('out/state_breadth.json') else {}
    # The walked loop (311/code/make_walk_fast_e31.py): every month in turn, not only the months the share first crosses.
    # A month at or above the line opens while the opener is armed AND the vacancy gap stood at its line in two of the prior
    # hback months; a month that fails the vacancy condition leaves the opener armed, so a later month can still open. The
    # opener re-arms when the share falls back below the line. A month reporting fewer than SB_ST['cover'] states is passed
    # over entirely - it can neither open nor re-arm.
    _sbB=float(((SB_ST.get('cell') or {}).get('share')) or 0.40); _sbcov=int(SB_ST.get('cover') or 0)
    _sbR=float(((SB_ST.get('cell') or {}).get('rearm')) or 0.25)   # v3.73 (23 September 2026, collection 333; E31b, collection 326): the opener re-arms only once the share has fallen below 0.25, not merely below the 0.40 line - re-armed at the line it fired a second time inside one stretch of high breadth (1992, on the Employment and Earnings first prints of collection 324); the four fires on the record are unchanged
    _sbCOV=SB_ST.get('coverage') or {}; _sbPUB=SB_ST.get('publications') or {}
    _sbarmed=True
    for _ms,_sh in sorted((SB_ST.get('series') or {}).items()):
        if _ms not in _sbPUB: continue
        if _sbcov and int(_sbCOV.get(_ms,0))<_sbcov: continue
        _sh=float(_sh)
        if _sbarmed and _sh>=_sbB-1e-9:
            _mm=pd.Timestamp(_ms); _w=G[(G.index>=_mm-pd.DateOffset(months=p['hback']))&(G.index<=_mm)]; _hit=_w[_w>=p['vl']]
            if len(_hit)>=2:
                SB_OPENER.append((max(pd.Timestamp(_sbPUB[_ms]),pd.Timestamp(_pubsV[_hit.index[1]])),_mm,_sh)); _sbarmed=False
        elif not _sbarmed and _sh<_sbR-1e-9: _sbarmed=True   # v3.73: E31b
    print('v3.73 state breadth (E31b, re-arm %.2f): %d fires, %d with the vacancy condition: %s'%(_sbR,len(SB_ST.get('fires') or []),len(SB_OPENER),[str(d.date()) for d,m,s in SB_OPENER]))
except Exception as _e:
    print('v3.72: the state opener was not read:',_e)
gU=_tenths(spl-spl.rolling(p['look'],min_periods=p['look']).min().shift(1)).dropna()/p['u45']
gL=_tenths(spl-spl.rolling(52,min_periods=52).min().shift(1)).dropna()/p['low']
m4=ICfp.dropna().rolling(4).mean(); _icl=m4.rolling(52,min_periods=52).min().shift(1)
# THE CLAIMS OBJECT'S MOVING BASE (walk43, v3.24; 9 September 2026, evening). The four-week mean's rise is measured from
# the higher of its 52-week low and ALPHA (0.85) times its trailing five-year median, both as published, so a return
# from a freak low is not read as a turn (August 2022: 43.9 per cent above the low, 31.4 above the base). The walk's
# preamble defines ALPHA and MED_W; under an older walk the base is the low alone.
_icb=np.maximum(_icl,ALPHA*m4.rolling(MED_W,min_periods=156).median().shift(1)) if 'ALPHA' in globals() else _icl
gI=((m4/_icb-1)*100).dropna()/p['ic']
gX=(g_asof/p['sahm']).dropna()
# THE HOUSEHOLD CO-SIGNER (walk42, v3.23; 9 September 2026). A proposal by the insured rate's 0.45 branch (U) or by
# initial claims (I) that stands within a band above its line - 0.2 point for the insured rate, 15 points for claims -
# fires only if the three-month average of the unemployment rate, as last published on the proposal day, stands at
# least 0.2 point above its low of the prior twelve months; a proposal at or beyond the band fires on its own; an
# unsigned proposal stays armed. The walk's preamble defines cosign(day), gpub (the gap by release day), COS_THR,
# U_BAND and IC_BAND; under an older walk none exists and the reading is as before. In the reading a co-signed branch
# is min(proposer, confirmer, max(proposer over its strong line, co-signer)): below 1.00 until a strong print or the
# co-signer arrives, at or above 1.00 exactly when the branch can fire.
COS=('cosign' in globals() and 'gpub' in globals())
if COS:
    STRONG={'U':(p['u45']+U_BAND)/p['u45'],'I':(p['ic']+IC_BAND)/p['ic']}
    gCS=(gpub_asof/COS_THR).sort_index()                                  # the co-signer's ratio to its line, by release day
    gCSm=(g_asof/COS_THR).dropna()                                        # and by reference month, for the monthly reading
    def _cs_asof(day):
        s_=gCS[gCS.index<=day]; return float(s_.iloc[-1]) if len(s_) else np.nan
else:
    STRONG={}; gCS=None; gCSm=None
    def _cs_asof(day): return np.nan
KC=p.get('kc') or (35,20)
_k1=((ICfp.dropna()/_icb-1)*100).dropna()/KC[0]                                   # the single week over the base
_kc=pd.Series({t:crash_on(rel_ic(t))/KC[1] for t in _k1.index})                  # the S&P under its 20-day high at the last close before the release
gKr=_k1.copy(); gK=pd.concat([_k1.rename('a'),_kc.rename('b')],axis=1).min(axis=1)  # the branch reading: both sides the same week
def _armK(gk,gkr):
    out=pd.Series(0.0,index=gk.index); armed=True
    for t,v in gk.items():
        if np.isnan(v): out[t]=np.nan; continue
        if armed:
            if v>=1.0-1e-9: out[t]=0.0; armed=False
            else: out[t]=v
        else:
            if gkr[t]<=1e-9: armed=True
            out[t]=v if armed else 0.0
    return out
RAW=dict(U=gU.copy(),L=gL.copy(),I=gI.copy(),X=gX.copy(),K=gK.copy())
gW=_tenths(SI-SI.rolling(52,min_periods=52).min().shift(1)).dropna()/p['wline'] if p.get('wline') else None
gV=_tenths(SI-SI.rolling(52,min_periods=52).min().shift(1)).dropna()/p['wline2'] if p.get('wline2') else None
gB=(BR/p['bshare']).dropna() if p.get('bshare') else None
RAW.update(W=None if gW is None else gW.copy(),V=None if gV is None else gV.copy(),B=None if gB is None else gB.copy())
cV=(G/p['vl']).dropna(); cH=(Hh['gap']/Hh['line']).dropna(); cP=(MX/p['hline']).dropna(); cS=(GSP/p['spr']).dropna(); cSV=(SVc['mx']/1.0).dropna()
# the spread's last week is complete only when its Friday's rates are in (the H.15 posts them the next business day):
# a week whose Friday is later than the last daily paper rate is not yet a reading (audit of 8 September 2026)
if '_cp1' in globals(): cS=cS[cS.index<=_cp1.index.max()]
# ARMING. A branch that has fired stays silent until it re-arms - the insured-rate branch U, initial claims I and the
# survey-week branch W when their gap is back at zero; the low branch L and the survey-week branch V when the gap is
# back below the line and four months have passed; breadth B when the share is below half its line; the hub X when
# the Sahm gap is below its line. While a branch is disarmed its distance is shown as zero: it cannot call. The month
# it fires reads zero too: the call is the episode on the chart, and after the call the branch is spent.
def armed_ratio(ratio,rearm,months=4):
    """ratio = reading / line, in time order; returns the ratio where the branch is armed (or firing), 0 where it is not"""
    out=pd.Series(0.0,index=ratio.index); armed=True; last=None
    for t,v in ratio.items():
        if np.isnan(v): out[t]=np.nan; continue
        if armed:
            if v>=1.0-1e-9: out[t]=0.0; armed=False; last=t     # the branch fires and is disarmed; the call itself is the episode, not this reading
            else: out[t]=v
        else:
            if rearm=='zero' and v<=0: armed=True
            elif rearm=='window' and v<1.0-1e-9 and last is not None and t>=last+pd.DateOffset(months=months): armed=True
            elif rearm=='half' and v<0.5: armed=True
            elif rearm=='line' and v<1.0-1e-9: armed=True
            out[t]=v if armed else 0.0
    return out
def armed_ratio_c(ratio,strong,pubfn):
    """armed_ratio for a co-signed branch (re-arms at zero): a reading at or above its line fires, and disarms, only if it stands at
    the strong line or the co-signer stood on its release day; an unsigned proposal stays armed and keeps its reading"""
    out=pd.Series(0.0,index=ratio.index); armed=True
    for t,v in ratio.items():
        if np.isnan(v): out[t]=np.nan; continue
        if armed:
            if v>=1.0-1e-9 and (v>=strong-1e-9 or cosign(pubfn(t))): out[t]=0.0; armed=False
            else: out[t]=v
        else:
            if v<=0: armed=True
            out[t]=v if armed else 0.0
    return out
if COS: gU=armed_ratio_c(gU,STRONG['U'],rel_iu); gI=armed_ratio_c(gI,STRONG['I'],rel_ic)
else: gU=armed_ratio(gU,'zero'); gI=armed_ratio(gI,'zero')
gL=armed_ratio(gL,'window')
if gW is not None: gW=armed_ratio(gW,'zero')
if gV is not None: gV=armed_ratio(gV,'window')
if gB is not None: gB=armed_ratio(gB,'half')
gX=armed_ratio(gX,'line'); gK=_armK(gK,gKr)
# THE INSURED RATE BEFORE 1971 (Rule Zero, 10 September 2026, evening). The weekly insured rate (spl) begins in 1971; before
# it the walk's U and L proposers read the monthly insured-rate gap gm (leg_gap_mx2: a month's reading published on the
# 10th of the next month; re-armed four months after a proposal once the gap is under the line; no co-signer). The page had
# no U or L branch before 1971, so the 1969 call (L confirmed by the pair on 6 October 1969) stood on a held 1.00 with a
# reading of 0.97 by W under it. Both branches now enter for the months before 1971, labelled U and L as the walk labels them.
if 'gm' in globals():
    _gm=gm.round(9); _gm=_gm[_gm.index<pd.Timestamp('1971-01-01')]
    RAW['Um']=(_gm/p['u45']).dropna(); RAW['Lm']=(_gm/p['low']).dropna()
    gUm=armed_ratio(RAW['Um'].copy(),'window'); gLm=armed_ratio(RAW['Lm'].copy(),'window')
    _pm10=lambda m:pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=9)
else: gUm=None; gLm=None; RAW['Um']=None; RAW['Lm']=None
# THE SEARCH WEEK IN THE LINE (v3.27, walk51; Rule Zero, 10 September 2026, evening). The sudden stop's second labour
# datum (s2/search_week.py, leg_K_search): the 7-day mean of Google searches for unemployment over its base, each day's
# value known the next morning and read against the S&P 500 at THAT day's close, 20 under its 20-day high. The branch
# reads min(search over 35, crash over 20) on every day the datum is known and the market closed, dated by the day it is
# known; it arms and re-arms as the claims week does (fires at 1.00; re-arms when the search datum is back at its base).
# The line had carried the sudden stop on the claims week alone, so 16 March 2020 stood on the held line (reading 0.39,
# the L branch) rather than on the rule's reading; from here the reading is the rule's own on every day from 2004.
if 'GT_REL' in globals() and '_crash2' in globals():
    _TERMS=(GT_TERMS if 'GT_TERMS' in globals() else {'unemp':(GT_DAY,GT7,GT_REL)})                   # v3.29 (walk55): every labour term; the branch reads the strongest each day
    def _armKS(rel,crash):
        out=pd.Series(np.nan,index=rel.index); armed=True
        for t,v in rel.items():
            c=crash.get(t,np.nan); r=(min(v,c) if not np.isnan(c) else np.nan)
            if armed:
                if not np.isnan(r) and r>=1.0-1e-9: out[t]=0.0; armed=False
                else: out[t]=r
            else:
                if v<=1e-9: armed=True
                out[t]=r if armed else 0.0
        return out
    _ksd=lambda s:s.dropna().set_axis(s.dropna().index+pd.Timedelta(days=1))                           # dated by the morning the datum is known
    _ksR=[]; _ksA=[]
    for _tag,(_tdd,_tgg,_trel) in _TERMS.items():   # _trel, not _rel: _rel is the release-calendar function used below
        _ks1=(_trel/KC[0]).dropna()                                                                      # the term's search week over its base, by the datum's day
        _ksc=pd.Series({t:float(_crash2.get(t+pd.Timedelta(days=1),np.nan))/KC[1] for t in _ks1.index})   # the S&P at the close of the day the datum is known (none on a day without a close)
        _ksR.append(_ksd(pd.concat([_ks1.rename('a'),_ksc.rename('b')],axis=1).min(axis=1,skipna=False)).rename(_tag)); _ksA.append(_ksd(_armKS(_ks1,_ksc)).rename(_tag))
    RAW['KS']=pd.concat(_ksR,axis=1).max(axis=1).dropna()                                            # the strongest term's reading each day (the sudden stop fires on the earliest)
    gKS=pd.concat(_ksA,axis=1).max(axis=1).dropna()
else: gKS=None; RAW['KS']=None
idx=pd.date_range('1948-01-01',pd.Timestamp(today).replace(day=1),freq='MS')
def mm(x): return None if x is None else x.resample('MS').max().reindex(idx)
def _kmm(a,b): return a if b is None else pd.concat([a,mm(b)],axis=1).max(axis=1)                       # the sudden stop's monthly reading on either datum
U,L,I,X,Wm,Vm,Bm,Km=mm(gU),mm(gL),mm(gI),mm(gX),mm(gW),mm(gV),mm(gB),_kmm(mm(gK),gKS)
Umm,Lmm=mm(gUm),mm(gLm)                                                                                 # the insured rate's monthly branches before 1971
Vc,Hpm,Ppm,Spm,SVm=mm(cV),mm(cH),mm(cP),mm(cS),mm(cSV)
C1=[Vc,Hpm,Spm]; C2=[Ppm,Spm,SVm]
# THE READING. Each month, for each branch, the proposer's largest ratio over the last four months and its best
# confirmer's largest ratio over the last six (the rule's own window, read backward so the reading is causal), the
# smaller of the two; the hub X reads the Sahm gap this month against the vacancy ratio held in two months of its
# window. The line is the strongest branch's reading. Read twice: with the branches' arming (a branch that has fired
# counts zero until it re-arms), for the distance to the next call; and without it, for the reading inside a recession.
def best_conf(confs,t,back=6):
    lo=t-pd.DateOffset(months=back); vals=[]
    for c in confs:
        if c is None: continue
        w=c[(c.index>=lo)&(c.index<=t)].dropna()
        if len(w): vals.append(float(w.max()))
    return max(vals) if vals else np.nan
def score_rows(P,tag=None):
    branches=[('U',P['U'],C1),('L',P['L'],C2),('I',P['I'],C1),('W',P['W'],C2),('V',P['V'],C2),('B',P['B'],C2),('Um',P.get('Um'),C1),('Lm',P.get('Lm'),C2)]
    rows={}
    # 17 September 2026 (Anthony: "as fast as possible, as safe as possible"): a month's score reads the series at and
    # before that month only, so the scores of every month up to two months ago are kept in cache/opening_scores_<tag>.pkl
    # under a hash of exactly those values (every series to that month, the lines, this code); a match reuses them and
    # scores the months since, a mismatch scores every month again
    def _sc_hash(M):
        h=_hl0.md5()
        for nm,s in sorted(P.items())+[('C%d'%i,c) for i,c in enumerate(C1+C2)]+[('gCSm',gCSm)]:
            h.update(str(nm).encode())
            if s is None: h.update(b'None'); continue
            s_=s[s.index<=M]; h.update(np.ascontiguousarray(s_.index.values).tobytes()); h.update(np.ascontiguousarray(s_.values,dtype=float).tobytes())
        h.update(repr((sorted(STRONG.items()),HUB_MAJ,p['hback'])).encode()); _bhs_code_hash(score_rows.__code__,h); _bhs_code_hash(best_conf.__code__,h)
        return h.hexdigest()
    _SCP=os.path.join('cache','opening_scores_%s.pkl'%tag) if tag else None; _sc_keep=None; _sc_rows={}
    _M_new=(idx[-1]-pd.DateOffset(months=2)) if (len(idx) and _SCP) else None
    if _M_new is not None:
        try:
            _c=_pk0.load(open(_SCP,'rb'))
            if _c.get('hash')==_sc_hash(_c['M']): _sc_keep=_c['M']; _sc_rows=_c['rows']
        except Exception: _sc_keep=None
    _n_reused=0
    for t in idx:
        if _sc_keep is not None and t<=_sc_keep and t in _sc_rows: rows[t]=_sc_rows[t]; _n_reused+=1; continue
        best=np.nan; who=''
        for nm,leg,confs in branches:
            if leg is None: continue
            w=leg[(leg.index>=t-pd.DateOffset(months=4))&(leg.index<=t)].dropna()
            if not len(w): continue
            sc=min(float(w.max()),best_conf(confs,t))
            if np.isnan(sc): continue
            if nm in STRONG:                       # the co-signer, by reference month: the gap of the month against 0.2
                csv_=gCSm.get(t,np.nan); sc=min(sc,max(float(w.max())/STRONG[nm],0.0 if np.isnan(csv_) else float(csv_)))
            if np.isnan(best) or sc>best: best,who=sc,nm[0]           # the monthly branches before 1971 are labelled U and L
        kv=P.get('K',pd.Series(dtype=float)).get(t,np.nan)             # the sudden stop: both sides read the same week, no window
        if not np.isnan(kv) and (np.isnan(best) or kv>best): best,who=kv,'K'
        pv=P['X'].get(t,np.nan)
        if not np.isnan(pv):
            w=Vc[(Vc.index>=t-pd.DateOffset(months=p['hback']))&(Vc.index<=t)].dropna().sort_values()
            wl=Vc[Vc.index<=t].dropna()
            _lat=float(wl.iloc[-1]) if len(wl) else np.nan
            _hold=(max(_lat,float(w.iloc[-HUB_MAJ])) if (HUB_MAJ and len(w)>=HUB_MAJ) else _lat)                # walk54: the latest print, or the majority's fifth-highest of the window
            sc=min(pv,float(w.iloc[-2]) if len(w)>=2 else np.nan,_hold)      # the hub's hold: the vacancy at its line in TWO months of the window, and STILL at it in its latest reading (walk40) or in a majority of the window (walk54)
            if not np.isnan(sc) and (np.isnan(best) or sc>best): best,who=sc,'X'
        rows[t]=(best,who)
    if _M_new is not None:
        try: _pk0.dump({'M':_M_new,'hash':_sc_hash(_M_new),'rows':{t_:v_ for t_,v_ in rows.items() if t_<=_M_new}},open(_SCP+'.tmp','wb')); os.replace(_SCP+'.tmp',_SCP)
        except Exception: pass
    print('opening scores (%s): %d months, %d reused%s'%(tag,len(idx),_n_reused,(' (kept through %s)'%_sc_keep.strftime('%Y-%m')) if _sc_keep is not None else ' (no kept scores matched: every month scored)'))
    return pd.DataFrame({'indicator':{k:v[0] for k,v in rows.items()},'branch':{k:v[1] for k,v in rows.items()}}).dropna(subset=['indicator'])
OPEN=score_rows(dict(U=U,L=L,I=I,W=Wm,V=Vm,B=Bm,X=X,K=Km,Um=Umm,Lm=Lmm),'armed')                                   # armed: the distance to the next call
OPENU=score_rows(dict(U=mm(RAW['U']),L=mm(RAW['L']),I=mm(RAW['I']),W=mm(RAW['W']),V=mm(RAW['V']),B=mm(RAW['B']),X=mm(RAW['X']),K=_kmm(mm(RAW['K']),RAW['KS']),Um=mm(RAW['Um']),Lm=mm(RAW['Lm'])),'raw')   # unarmed: the reading inside a recession
# the line ends at the last month with a proposer's reading (the windows would otherwise carry it into months without data)
_lastm=max(x.dropna().index.max() for x in [RAW['U'],RAW['L'],RAW['I'],RAW['X'],RAW['W'],RAW['V'],RAW['B'],RAW['K'],RAW['KS']] if x is not None).replace(day=1)
OPEN=OPEN[OPEN.index<=_lastm]; OPENU=OPENU[OPENU.index<=_lastm]
_tick('opening scores')
# THE SERIES IS MADE CONSISTENT WITH THE RULE'S OWN CALLS. The branch scores above ignore the re-arming of each leg, the
# hub's two-month hold as the walk applies it and the six-month minimum expansion, so a score can sit at or above 1.00
# in a month the rule does not speak. The rule frozen at its walk-end lines is run in full (build_v) and its episodes taken:
# inside an episode the series reads at least 1.00, outside it reads at most 0.99. At or above 1.00 means the rule is in
# a recession it has called; the distance below 1.00 says how far the nearest branch stands from speaking.
p = dict(p); p['carry'] = CARRY_LETTERS          # v3.55: the walk-end rule with every carried leg armed
PENDING.clear()
with contextlib.redirect_stdout(io.StringIO()): _r,_t=build_v(p)
_tick('build_v (pending)')
# THE BACKSTOP OPENER'S RECORD (collection 256): the frozen rule once more with leg b. Idle when there is no calls file.
_BS_CALLS=[]
try:
    import csv as _csv_bs
    _BS_CALLS=[(pd.Timestamp(r['pub']),pd.Timestamp(r['dated'])) for r in _csv_bs.DictReader(open('out/backstop_opener_calls.csv'))]
except Exception as _e_bs: print('backstop opener: no calls file (%r); the opener is idle this build'%(_e_bs,))
# THE ACTIVITY OPENER'S CALLS AND READING (v3.60, Core v6, 21 September 2026, collection 278): s2/activity_opener.py writes
# them before the build; the frozen rule is rebuilt once more with leg P beside leg b. Idle when there is no calls file.
_AO_CALLS=[]; _AO_ST={}
try:
    import csv as _csv_ao, json as _json_ao
    _AO_CALLS=[(pd.Timestamp(r['pub']),pd.Timestamp(r['dated'])) for r in _csv_ao.DictReader(open('out/activity_opener_calls.csv'))]
    _AO_ST=_json_ao.load(open('out/activity_opener_state.json'))
except Exception as _e_ao: print('activity opener: no calls file (%r); the opener is idle this build'%(_e_ao,))
# THE CONCURRENCE BRANCH (v3.68 (22 September 2026, collections 300 and 301; PREREG-v368-port-2026-09-22): a labour proposal at today's lines
# (U, L, W, V, I, B), still standing, confirmed on the first day the activity picture ACT(0.010) holds (the activity opener's
# four conditions with production at 0.010; s2/activity_opener.py writes the days). Walked from 1956 in collection 300 (A2:
# 0.010 at every cut; leave-one-out unchanged on all 13 recessions); its only effect on the walked record is 1960 (25 April
# 1960, -5 days). Leg Y, on the activity opener's bars. Idle (and said so in the state) when the days file is missing.
_CB_ALL=[]; _CB_NOTE='not run'
try:
    _CB_ACT=np.array(sorted(np.datetime64(pd.Timestamp(x)) for x in pd.read_csv('out/activity_picture_days.csv')['day']))
    exec(open('s2/concurrence.py').read())
    _CB_ALL=cb_calls(p,_CB_ACT)
    _CB_CALLS=sorted({(d,pd.Timestamp(d.year,d.month,1)) for d,m,w in _CB_ALL})
    _CB_NOTE='ran: %d activity-picture days since 1947 (last %s); %d calls over the history at today\'s lines'%(len(_CB_ACT),str(pd.Timestamp(_CB_ACT[-1]).date()) if len(_CB_ACT) else None,len(_CB_CALLS))
except Exception as _e_cb:
    _CB_CALLS=[]; _CB_NOTE='did not run (%r); the branch is idle this build'%(_e_cb,)
print('concurrence branch:',_CB_NOTE)
_tick('concurrence branch')
def _ao_next():
    # G.17's next release day from FRED's calendar (s2/activity_opener.py); if FRED could not be read, the first weekday
    # on or after the 16th (the Federal Reserve's usual day) - only ever a fallback
    _n=_AO_ST.get('next_production_release')
    if _n and _n>=str(today): return _n
    _t=pd.Timestamp(today); _c=pd.Timestamp(_t.year,_t.month,16)
    if _c<_t: _c=_c+pd.DateOffset(months=1)
    while _c.weekday()>=5: _c=_c+pd.Timedelta(days=1)
    return _c.date().isoformat()
_tb=_t
if _BS_CALLS or _AO_CALLS or _CB_CALLS:   # v3.68: the concurrence branch's leg Y beside b and P
    _BS_ON=True
    try:
        with contextlib.redirect_stdout(io.StringIO()): _rb,_tb=build_v(p)
    finally: _BS_ON=False
    _tick('build_v (backstop opener)')
# ---- v3.73 (23 September 2026, collection 333; E38, collection 323; Anthony: 'for E38 backstop decision, yes!'): THE PAYROLL BACKSTOP CLOSER, branch E. On an
# ---- episode that has stood open ninety days and that no other closer has closed, the employment situation's own vintage closes it when
# ---- payrolls have risen three months running and the three-month unemployment rate stands 0.3 under its high since the open. On the
# ---- record it never acts first (99 to 770 days after the rule's closes on the ALFRED vintages; never in 2024), so no close moves.
PB_ST={'status':'idle'}
try:
    import importlib.util as _iu333b
    _spp=_iu333b.spec_from_file_location('payroll_backstop',os.path.join('s2','payroll_backstop.py')); _pb333=_iu333b.module_from_spec(_spp); _spp.loader.exec_module(_pb333)
    _AL333=os.path.join(_ROOT,'onset-detector-new-2026-08-23','27_realtime_vintages','alfred_all_vintages')
    _ev333=[x for x in _tb if x['kind'] in ('peak','trough')]
    if _ev333 and _ev333[-1]['kind']=='peak':
        _od333=pd.Timestamp(_ev333[-1]['published']); _fd333,_rd333=_pb333.today_reading(_AL333,_od333,pd.Timestamp(today))
        PB_ST=dict(status='read: the rule stands open',open_since=str(_od333.date()),**_rd333)
        if _fd333 is not None:
            _tb.append({'published':pd.Timestamp(_fd333),'kind':'trough','leg':'E','date':pd.Timestamp(_fd333.year,_fd333.month,1)}); _tb.sort(key=lambda x:x['published'])
            PB_ST['closed_on']=str(pd.Timestamp(_fd333).date()); print('v3.73 E38: the payroll backstop closes the open episode on',pd.Timestamp(_fd333).date())
    else:
        _,_rd333=_pb333.today_reading(_AL333,(_ev333[-2]['published'] if len(_ev333)>=2 else pd.Timestamp('1900-01-01')),pd.Timestamp(today))
        PB_ST=dict(status='idle: the rule stands closed',**{k:_rd333.get(k) for k in ('gains','payroll_month','vintage_day','min_open_days','gains_needed','turn_needed')})
except Exception as _e333b: PB_ST=dict(status='did not run (%r)'%(_e333b,))
print('v3.73 payroll backstop closer:',PB_ST.get('status'))
PENDING_NOW = sorted({(a.date().isoformat(), b.strftime('%Y-%m'), L) for a, b, L in PENDING if (pd.Timestamp(today) - a).days <= 400})
print('pending leg proposals (passed the record bar, core not yet confirmed, inside 400 days):', PENDING_NOW)
# THE LIVE-CODE REPLAY (22 September 2026, Step 3a of the plan): the frozen rule's own record on the live data, written out so
# it can be held against the lab's frozen run at the same lines (315/out/false_stop_audit.json, base) - the live tool and the
# walked tool must be the same object on the same lines; a difference is a data or a port defect, never a rule change.
json.dump([dict(published=x['published'].date().isoformat(),kind=x['kind'],leg=str(x['leg']),date=(pd.Timestamp(x['date']).strftime('%Y-%m') if x.get('date') is not None else None)) for x in _tb if x['kind'] in ('peak','trough')],
          open('out/frozen_record.json','w'),indent=1)
FROZEN=[]; _cur=None
for x in _tb:   # the frozen rule's episodes, with any the backstop opener adds (collection 256)
    if x['kind']=='peak': _cur=[x['published'],None]
    elif _cur is not None: _cur[1]=x['published']; FROZEN.append(tuple(_cur)); _cur=None
if _cur is not None: FROZEN.append((_cur[0],pd.Timestamp('2100-01-01')))
def _inside(t):
    return any(a<=t+pd.offsets.MonthEnd(0) and t<=b for a,b in FROZEN)
OPEN['raw']=OPEN['indicator'].copy()
OPEN['indicator']=[max(v,1.0) if _inside(t) else min(v,0.99) for t,v in OPEN['indicator'].items()]
OPEN['called']=[_inside(t) for t in OPEN.index]
# ---- the closing indicator: closer C's score at its walked lines ----
D_,S_=p['cD'] if p.get('cD') else 6,p['cs']
sp_=np.nan_to_num(_Csp,nan=-99); fc_=np.nan_to_num(_Cfc,nan=-99); du_=np.nan_to_num(_Cdu,nan=-99)
conf=np.maximum.reduce([sp_/S_,fc_/3.0,du_/3.0,np.minimum.reduce([_FI['drop'].values/15.0,_FI['run'].values/6.0,sp_/10.0])])   # v3.71 (E29): the fourth confirmation, the strong flow
cs=np.minimum.reduce([_FI['drop'].values/D_,_FI['run'].values/3.0,_FI['amp'].values/20.0,conf])
CLOSE=pd.Series(cs,index=_CW).clip(lower=0); CLOSE_RAW=CLOSE.copy()
# read only while the frozen rule has an episode open (a close cannot be proposed when nothing is open)
CLOSE=pd.Series([v if any(a<=t<=b for a,b in FROZEN) else np.nan for t,v in CLOSE.items()],index=CLOSE.index)
# ---- the chronology from the causal walk ----
pg=pickle.load(open(f'cache/{VAR}_prog.pkl','rb')); LOG=sorted(pg['log'],key=lambda z:z[0])
# ---- THE BACKSTOP OPENER IN THE DIARY (collection 256): when the walked rule stands closed, a gated backstop call after
# ---- the diary's last entry opens an episode tagged b, followed to its close by the frozen rule's closers. Nothing before
# ---- the diary's last entry is touched, and a frozen-rule open by any other leg after it takes precedence over b.
# ---- THE STANDING MOVES (v3.57, 20 September 2026, collection 260). The diary is the walk's record up to the day the walk
# ---- was run; from there the rule is the frozen rule at its walk-end lines, and ITS record on today's data continues the
# ---- diary: every event published after the diary's last entry is appended in order, open/close alternation kept. Until
# ---- today nothing extended the diary, so the headline could not change when the core opened. BHS_DRILL_EVENT injects one
# ---- synthetic event ("YYYY-MM-DD OPEN U") for a fire drill; it is never set on the runner.
BS_EVENTS=[]; NEW_EVENTS=[]; AO_EVENTS=[]; CB_EVENTS=[]; SB_EVENTS=[]
_lp=LOG[-1][0] if LOG else pd.Timestamp('1900-01-01')
_after=[x for x in _tb if x['kind'] in ('peak','trough') and x['published']>_lp]
_sbclose=LOG[-1][0] if LOG and LOG[-1][1]=='CLOSE' else None   # v3.72 (22 September 2026, collection 311): the state opener, under the quarter rule
SB_BLOCKED=[]
for _sd,_sm,_ssh in SB_OPENER:
    if _sd<=_lp: continue
    if _sbclose is not None and (_sd-_sbclose).days<91: SB_BLOCKED.append(str(_sd.date())); continue
    _after.append({'published':_sd,'kind':'peak','leg':'N','date':_sm})
_after.sort(key=lambda x:x['published'])
if SB_BLOCKED: print('v3.72: the state opener stood down (the rule closed less than a quarter ago):',SB_BLOCKED)
_drill=os.environ.get('BHS_DRILL_EVENT')
if _drill:
    _d,_k,_L=_drill.split(); _after.append({'published':pd.Timestamp(_d),'kind':'peak' if _k.upper()=='OPEN' else 'trough','leg':_L,'date':pd.Timestamp(_d)}); _after.sort(key=lambda x:x['published'])
    print('FIRE DRILL: synthetic event injected', _drill)
_open=bool(LOG) and LOG[-1][1]=='OPEN'
for x in _after:
    if (x['kind']=='peak') == _open: continue          # a second open while open, or a close while closed, is not an event
    _ev=(x['published'],'OPEN' if x['kind']=='peak' else 'CLOSE',pd.Timestamp(x['published'].year,x['published'].month,1),x['leg'])
    LOG.append(_ev); NEW_EVENTS.append(_ev); _open=(x['kind']=='peak')
    if x['leg']=='b': BS_EVENTS.append(_ev)
    if x['leg']=='P': AO_EVENTS.append(_ev)   # v3.60: the activity opener (collection 278)
    if x['leg']=='Y': CB_EVENTS.append(_ev)   # v3.68: the concurrence branch (collections 300 and 301)
    if x['leg']=='N': SB_EVENTS.append(_ev)   # v3.72 (22 September 2026, collection 311): the state breadth
LOG=sorted(LOG,key=lambda z:z[0])
if NEW_EVENTS: print('THE DIARY CONTINUED by the frozen rule:',[(e[0].date().isoformat(),e[1],e[3]) for e in NEW_EVENTS])
else: print('the diary stands as walked; no event after', _lp.date().isoformat())
epis=[]; cur=None
for pub,kind,dt,leg in LOG:
    if kind=='OPEN': cur={'open_pub':pub.date().isoformat(),'open_month':dt.strftime('%Y-%m'),'open_leg':leg,'close_pub':None,'close_month':None,'close_leg':None}   # v3.57: an OPEN episode carries its close keys as None (the build crashed on an open standing before)
    elif cur is not None: cur.update(close_pub=pub.date().isoformat(),close_month=dt.strftime('%Y-%m'),close_leg=leg); epis.append(cur); cur=None
if cur is not None: epis.append(cur)
# v3.63 (collection 289): the two closes the labour core's first walked configuration (the 1956 cut) gives to the recessions
# the activity opener opened before the core could be walked - retrospective, not real-time - are marked on every episode
_RETRO=set(pg.get('retro_closes') or [])
for _e in epis: _e['close_basis']=('retrospective' if _e.get('close_pub') in _RETRO else ('real time' if _e.get('close_pub') else None))
# the reading must carry the clauses the diary was walked with: an X open on 3 May 2024 exists only under the majority hold
if any(e['open_pub']=='2024-05-03' and e['open_leg']=='X' for e in epis) and not HUB_MAJ: raise SystemExit('bhs_build: the diary opens 3 May 2024 by X (the majority hold) but HUB_MAJ is None - the walk chain was not read')
last=LOG[-1]; standing={'state':'open' if last[1]=='OPEN' else 'closed','since':last[0].date().isoformat(),'dated':last[2].strftime('%Y-%m'),'leg':last[3]}
# ---- THE ONE LINE (the site's series). Recessions dated by the rule: the causal diary from 1962, and before 1962 the
# rule at its final lines (the walk begins in 1962). Outside a recession the line is the rule's reading with the
# branches' arming - the distance to the next opening call - held below 1.00 (at most 0.99) where the frozen rule did
# not speak; from the month the rule opened through the month it closed it is the reading without arming, held at
# least at 1.00 (the rule has the recession open); it drops below 1.00 the month after the close. Nothing is smoothed
# and nothing is capped: the crossings are the rule's own calls and the heights are its readings.
# THE PAGE BEGINS IN JANUARY 1948 (v3.63, 21 September 2026, collection 289; Anthony: "Yes port core v7-W to the site now").
# Every episode shown is the walked record of Core v7-W: the activity opener walked from 1948 (it learned from the pre-war
# recessions a 1948 reader knew) and the labour core walked from 1956 under E13t (the first cut that knew a postwar
# recession); from 1962 the diary is walk 97's, line for line. The two closes before 1956 (1950-03-09, 1954-06-03) are
# retrospective - the core's first walked configuration's - and carry close_basis='retrospective'. No frozen episode is
# shown. (Until v3.62 the page began in January 1962 - Anthony's ruling of 8 September 2026, the first January at which
# the rule's lines were chosen from the past alone; the opener's walk from 1948 is what now lets the record begin there.)
SITE_START=pd.Timestamp(os.environ.get('BHS_SITE_START','1948-01-01'))
EP=[]
_tick('closing series')
for a_,b_ in FROZEN:
    if False and a_<pd.Timestamp('1962-01-01'):
        EP.append(dict(open_pub=a_.date().isoformat(),open_month=a_.strftime('%Y-%m'),open_leg='',close_pub=(None if b_.year==2100 else b_.date().isoformat()),close_month=(None if b_.year==2100 else b_.strftime('%Y-%m')),close_leg='',walk=False))
for e in epis: EP.append(dict(e,walk=True))
def _ep_inside(m):
    ms=m.strftime('%Y-%m')
    for e in EP:
        if e['open_month']<=ms and (e['close_month'] is None or ms<=e['close_month']): return e
    return None
ONE=[]; PH=[]; RD=[]; BR_=[]
for t in OPEN.index:
    e=_ep_inside(t)
    if e is None:
        v=float(max(0.0,OPEN['raw'][t])); ONE.append(float(min(0.99,v))); RD.append(v); PH.append(''); BR_.append(OPEN['branch'][t])
    else:
        v=OPENU['indicator'].get(t,np.nan); v=float(max(0.0,v)) if not np.isnan(v) else 0.0
        ONE.append(float(max(1.0,v))); RD.append(v); PH.append('open'); BR_.append(OPENU['branch'].get(t,''))
SERIES=pd.DataFrame({'value':ONE,'phase':PH,'branch':BR_,'reading':RD},index=OPEN.index)
# ---- THE LINE AT THE FREQUENCY OF THE DATA. One observation on every day a release the rule reads arrives: weekly
# claims (initial claims five days after their week, the insured rate and the survey-week rate twelve days after,
# the state rates nineteen days after), the employment report (the Sahm gap, the hours pair, the unemployment half
# of the housing pair), JOLTS (the vacancy rate), housing starts, building permits, the H.15 week (the paper spread, on its Friday) and, from
# 2004, the search week (v3.27: every day the market closes, the datum known that morning). Each object is carried at the day it was published; the reading on a day uses only what was
# published by that day: the proposer's largest ratio over its last four months of data, the confirmer's over its
# last six, the smaller of the two, the strongest branch. Inside a recession the rule called (from the day it opened
# to the day it closed) the reading is taken without arming and held at least at 1.00; outside, with arming and
# held at most at 0.99. The dates are the rule's own days: the line crosses 1.00 the day the rule spoke. (The walk
# from walk39 dates every object on its actual release day; the page carries the same days.)
def _pubdf(ratio,pubfn):
    rows=[(pubfn(t),t,float(v)) for t,v in ratio.dropna().items() if pubfn(t) is not None]
    df=pd.DataFrame(rows,columns=['pub','t','v']).sort_values(['pub','t']).reset_index(drop=True)
    return dict(pub=df['pub'].values.astype('datetime64[ns]'),t=df['t'].values.astype('datetime64[ns]'),v=df['v'].values,tmax=np.maximum.accumulate(df['t'].values.astype('datetime64[ns]')) if len(df) else np.array([],dtype='datetime64[ns]'))
def _asof(obj,d,months,second=False):
    """the largest value of the object over its last `months` months of data published by day d (or the second largest)"""
    k=int(np.searchsorted(obj['pub'],np.datetime64(d),side='right'))
    if k==0: return np.nan
    tstar=obj['tmax'][k-1]; lo=(pd.Timestamp(tstar)-pd.DateOffset(months=months)).to_datetime64()
    m=obj['t'][:k]>=lo; vals=obj['v'][:k][m]
    if not len(vals): return np.nan
    if second: return float(np.sort(vals)[-2]) if len(vals)>=2 else np.nan
    return float(vals.max())
def _vals_win(obj,d,lo,hi):
    """the object's values for the months lo..hi that were published by day d (one value per month: the latest print by d)"""
    k=int(np.searchsorted(obj['pub'],np.datetime64(d),side='right'))
    if k==0: return np.array([])
    t=obj['t'][:k]; v=obj['v'][:k]; m=(t>=np.datetime64(pd.Timestamp(lo)))&(t<=np.datetime64(pd.Timestamp(hi)))
    if not m.any(): return np.array([])
    s=pd.Series(v[m],index=pd.DatetimeIndex(t[m])); return s.groupby(level=0).last().values
# THE RELEASE DAYS (audit of 8 September 2026). Walks from walk39 define them: rel_ic (the initial-claims week's
# release), rel_iu (the insured week's, a release later), rel_state (two releases later), rel_h15 (the first business
# day after the H.15 week's Friday, when the Federal Reserve posts Friday's rates). Under an older walk the lab's
# conventions stand in (five, twelve and nineteen days; the Friday).
if 'rel_ic' in globals():
    _wk5=rel_ic; _wk12=rel_iu; _wk19=rel_state; _sp=rel_h15
    _sv=lambda t:(rel_iu(SW[t]) if t in SW.index else None)
else:
    _wk12=lambda t:t+pd.Timedelta(days=12); _wk5=lambda t:t+pd.Timedelta(days=5); _wk19=lambda t:t+pd.Timedelta(days=19)
    _sv=lambda t:(SW[t]+pd.Timedelta(days=12)) if t in SW.index else None
    _sp=lambda t:t
_pu=lambda m:_rel(_RELU,m,4); _pj=lambda m:_rel(_RELJ,m,29)
PROP_A={'U':_pubdf(gU,_wk12),'L':_pubdf(gL,_wk12),'I':_pubdf(gI,_wk5),'X':_pubdf(gX,_pu),'K':_pubdf(gK,_wk5)}
PROP_R={'U':_pubdf(RAW['U'],_wk12),'L':_pubdf(RAW['L'],_wk12),'I':_pubdf(RAW['I'],_wk5),'X':_pubdf(RAW['X'],_pu),'K':_pubdf(RAW['K'],_wk5)}
for _k,_a,_r,_f in (('W',gW,RAW['W'],_sv),('V',gV,RAW['V'],_sv),('B',gB,RAW['B'],_wk19)):
    if _a is not None: PROP_A[_k]=_pubdf(_a,_f); PROP_R[_k]=_pubdf(_r,_f)
if gKS is not None: PROP_A['KS']=_pubdf(gKS,lambda d:d); PROP_R['KS']=_pubdf(RAW['KS'],lambda d:d)   # v3.27: the search week, dated by the morning it is known, read at that day's close
if gUm is not None: PROP_A['Um']=_pubdf(gUm,_pm10); PROP_R['Um']=_pubdf(RAW['Um'],_pm10); PROP_A['Lm']=_pubdf(gLm,_pm10); PROP_R['Lm']=_pubdf(RAW['Lm'],_pm10)   # the monthly insured rate before 1971, on the 10th of the next month
# the housing x rate pair as the rule reads it: each month's reading is set the day both halves are in (mkpair3's events)
def _pair_pub():
    """the housing x rate pair as the rule reads it: each half as it stood on its release day; a month's reading is set the day both halves are in"""
    ev=[(pd.Timestamp(hh_pub[m]),'D',m) for m in hh_asof.index]+[(pd.Timestamp(rate_pub[m]),'U',m) for m in rate_asof.index if m>=pd.Timestamp('1960-01-01')]
    _perm='PERM_ASOF' in globals() and 'mkpair_either_asof' in globals()   # v3.27 (walk51): permits beside starts, each half as it stood on its day
    if _perm: ev+=[(pd.Timestamp(PERM_PUB[m]),'P',m) for m in PERM_ASOF.index if m in PERM_PUB.index]
    ev.sort(key=lambda x:(x[0],x[1])); lastD=None; lastU=None; lastP=None; rows=[]
    for d,kind,m in ev:
        if kind=='D': lastD=m if (lastD is None or m>lastD) else lastD
        elif kind=='P': lastP=m if (lastP is None or m>lastP) else lastP
        else: lastU=m if (lastU is None or m>lastU) else lastU
        if lastU is None or (lastD is None and lastP is None): continue
        vs=min(hh_asof.get(lastD,np.nan),rate_asof.get(lastU,np.nan)) if lastD is not None else np.nan
        vp=min(PERM_ASOF.get(lastP,np.nan),rate_asof.get(lastU,np.nan)) if (_perm and lastP is not None) else np.nan
        v=np.nanmax([vs,vp]) if not (np.isnan(vs) and np.isnan(vp)) else np.nan
        if np.isnan(v): continue
        rows.append((d,max([x for x in (lastD,lastP,lastU) if x is not None]),float(v)/p['hline']))
    df=pd.DataFrame(rows,columns=['pub','t','v']).sort_values(['pub','t']).reset_index(drop=True)
    return dict(pub=df['pub'].values.astype('datetime64[ns]'),t=df['t'].values.astype('datetime64[ns]'),v=df['v'].values,tmax=np.maximum.accumulate(df['t'].values.astype('datetime64[ns]')))
def _pairsv_pub():
    """the starts x vacancy pair: starts as they stood on their release day, the vacancy rate as it stood on the JOLTS day"""
    vr_=(G/p['vl'])
    ev=[(pd.Timestamp(hh_pub[m]),'D',m) for m in hh_asof.index]+[(_pubsV[m],'V',m) for m in vr_.index if m in _pubsV.index]
    ev.sort(key=lambda x:(x[0],x[1])); lastD=None; lastV=None; rows=[]
    for d,kind,m in ev:
        if kind=='D': lastD=m if (lastD is None or m>lastD) else lastD
        else: lastV=m if (lastV is None or m>lastV) else lastV
        if lastD is None or lastV is None: continue
        v=min(hh_asof.get(lastD,np.nan),vr_.get(lastV,np.nan))
        if np.isnan(v): continue
        rows.append((d,max(lastD,lastV),float(v)))
    df=pd.DataFrame(rows,columns=['pub','t','v']).sort_values(['pub','t']).reset_index(drop=True)
    return dict(pub=df['pub'].values.astype('datetime64[ns]'),t=df['t'].values.astype('datetime64[ns]'),v=df['v'].values,tmax=np.maximum.accumulate(df['t'].values.astype('datetime64[ns]')))
_hp=lambda m:(pd.Timestamp(hp_pub[m]) if m in hp_pub.index else _pu(m))
CONF={'vac':_pubdf(cV,_pj),'hours':_pubdf(cH,_hp),'pair':_pair_pub(),'spread':_pubdf(cS,_sp),'pairSV':_pairsv_pub()}
CONF1=['vac','hours','spread']; CONF2=['pair','spread','pairSV']
_alld=set()
for _o in list(PROP_R.values())+list(CONF.values()): _alld.update(pd.DatetimeIndex(_o['pub']).tolist())
DAYS=sorted(d for d in _alld if pd.Timestamp('1948-01-01')<=d<=pd.Timestamp(today))
# v3.73 (23 September 2026, collection 333): every episode's open day and close day is a day of the grid, so the line's ceiling on the close day is the record's grade
# (before 1962 the closes fell between the objects' publication days and the 1948-49 line stopped at 4.79 where the record said 5.2)
DAYS=sorted(set(DAYS)|{pd.Timestamp(e[k]) for e in epis for k in ('open_pub','close_pub') if e.get(k) and pd.Timestamp('1948-01-01')<=pd.Timestamp(e[k])<=pd.Timestamp(today)})
def _reading(P,d):
    best=np.nan; who=''
    cvals={c:_asof(CONF[c],d,6) for c in CONF}
    for nm,confs in (('U',CONF1),('L',CONF2),('I',CONF1),('W',CONF2),('V',CONF2),('B',CONF2),('Um',CONF1),('Lm',CONF2)):
        if nm not in P: continue
        if nm in ('Um','Lm') and d>=pd.Timestamp('1971-05-10'): continue   # the monthly series ends with December 1970 (published 10 January 1971); its four-month window is empty from 10 May 1971
        pv=_asof(P[nm],d,4)
        if np.isnan(pv): continue
        cc=[cvals[c] for c in confs if not np.isnan(cvals[c])]
        if not cc: continue
        cv=max(cc)
        sc=min(pv,cv)
        if nm in STRONG:                           # the co-signer as last published by day d (walk42's clause)
            csd=_cs_asof(d); sc=min(sc,max(pv/STRONG[nm],0.0 if np.isnan(csd) else csd))
        if np.isnan(best) or sc>best: best,who=sc,nm[0]      # the monthly branches before 1971 are labelled U and L
    if 'K' in P:                             # the sudden stop: the latest claims week over its base, the market's fall at the last close before this day
        pk=_asof(P['K'],d,0)
        if not np.isnan(pk) and (np.isnan(best) or pk>best): best,who=pk,'K'
    if 'KS' in P:                            # v3.27: the sudden stop on the search week, the datum known this morning with the market at this day's close - read on its own day only (leg_K_search reads no stale datum)
        _kk=int(np.searchsorted(P['KS']['pub'],np.datetime64(d),side='right'))
        pk=_asof(P['KS'],d,0) if (_kk>0 and pd.Timestamp(P['KS']['tmax'][_kk-1])==d) else np.nan
        if not np.isnan(pk) and (np.isnan(best) or pk>best): best,who=pk,'K'
    pv=_asof(P['X'],d,0)                     # the Sahm gap as last published
    if not np.isnan(pv):
        # the hub's window is the Sahm month's own, m-9..m, over the JOLTS prints published by day d (the walk's hubv); until
        # the evening of 10 September 2026 the window had been anchored on the latest JOLTS month instead (one month earlier)
        _kx=int(np.searchsorted(P['X']['pub'],np.datetime64(d),side='right')); _m=pd.Timestamp(P['X']['tmax'][_kx-1])
        _vals=_vals_win(CONF['vac'],d,_m-pd.DateOffset(months=p['hback']),_m); latest=_asof(CONF['vac'],d,0)
        if len(_vals)>=2 and not np.isnan(latest):
            _srt=np.sort(_vals); sec=float(_srt[-2]); hold=latest
            if HUB_MAJ and len(_srt)>=HUB_MAJ: hold=max(latest,float(_srt[-HUB_MAJ]))   # walk54: or a majority of the published window at the line
            sc=min(pv,sec,hold)                   # two holds in the window, and the latest print still at the line (walk40's clause), or the majority (walk54)
            if np.isnan(best) or sc>best: best,who=sc,'X'
    return best,who
# THE EPISODES THE DAILY LINE STANDS ON ARE THE RULE'S OWN CALLS (correction of 9 September 2026). The line had been held
# at 1.00 from the day the rule frozen at today's lines would have fired, which in 1969, 1990 and 2001 preceded the call
# the rule actually made (28 July against 21 August 1969; 19 July against 3 August 1990; 22 March against 29 March 2001
# under v3.22), so the crossing was not the call the chronology table reports. From 1962 the line now follows the causal
# diary: from the day the rule opened a recession through the day it closed it; before 1962 (not shown) the frozen run.
_EPD=[(pd.Timestamp(e['open_pub']),(pd.Timestamp(e['close_pub']) if e.get('close_pub') else pd.Timestamp('2100-01-01'))) for e in EP if e.get('open_pub')]
def _inside_day(d):
    if d>=SITE_START: return any(a<=d<=b for a,b in _EPD)
    return any(a<=d<=b for a,b in FROZEN)
CLOSE=pd.Series([v if _inside_day(t) else np.nan for t,v in CLOSE_RAW.items()],index=CLOSE_RAW.index)   # the closer, read only while the rule's own episode is open
# ---- 17 September 2026 (Anthony: "as fast as possible, as safe as possible"): a day's reading uses only what was published
# ---- by that day, so it is fixed once the objects' rows published by then are fixed. The readings of every day up to a
# ---- week ago are kept in cache/daily_readings.pkl under a hash of exactly what they read - every object's pub, t and v
# ---- where pub <= that day, the co-signer's series to that day, the lines, the code of the four functions; a match
# ---- reuses them and reads only the days since, a mismatch (a revised history, a changed line) reads every day again.
# ---- Each kept day records which object set it was read from (inside or outside a recession) and is re-read if the
# ---- diary has moved it.
def _dr_hash(D):
    h=_hl0.md5(); D64=np.datetime64(pd.Timestamp(D))
    for nm,objs in (('A',PROP_A),('R',PROP_R),('C',CONF)):
        for k in sorted(objs):
            o=objs[k]; n=int(np.searchsorted(o['pub'],D64,side='right'))
            h.update(('%s:%s:%d'%(nm,k,n)).encode()); h.update(np.ascontiguousarray(o['pub'][:n]).tobytes()); h.update(np.ascontiguousarray(o['t'][:n]).tobytes()); h.update(np.ascontiguousarray(o['v'][:n],dtype=float).tobytes())
    if gCS is not None:
        s_=gCS[gCS.index<=pd.Timestamp(D)]; h.update(np.ascontiguousarray(s_.index.values).tobytes()); h.update(np.ascontiguousarray(s_.values,dtype=float).tobytes())
    h.update(repr((sorted(STRONG.items()),HUB_MAJ,p['hback'],CONF1,CONF2)).encode())
    for fn in (_reading,_asof,_vals_win,_cs_asof,_inside_day): _bhs_code_hash(fn.__code__,h)
    return h.hexdigest()
_DRP=os.path.join('cache','daily_readings.pkl'); _dr_keep=None; _dr_rows={}; _D_new=None
if DAYS:
    _D_new=DAYS[-1]-pd.Timedelta(days=7)
    try:
        _c=_pk0.load(open(_DRP,'rb'))
        if _c.get('hash')==_dr_hash(_c['D']): _dr_keep=_c['D']; _dr_rows=_c['rows']
    except Exception: _dr_keep=None
DV=[]; DR=[]; DP=[]; DB=[]; DD=[]; _dr_new={}; _n_reused=0
for d in DAYS:
    ins=_inside_day(d)
    if _dr_keep is not None and d<=_dr_keep and d in _dr_rows and _dr_rows[d][0]==ins: r,who=_dr_rows[d][1],_dr_rows[d][2]; _n_reused+=1
    else: r,who=_reading(PROP_R if ins else PROP_A,d)
    if _D_new is not None and d<=_D_new: _dr_new[d]=(ins,r,who)
    if np.isnan(r): continue
    r=float(max(0.0,r))
    DD.append(d); DR.append(r); DB.append(who); DP.append('open' if ins else '')
    DV.append(float(max(1.0,r)) if ins else float(min(0.99,r)))
if _D_new is not None:
    try: _pk0.dump({'D':_D_new,'hash':_dr_hash(_D_new),'rows':_dr_new},open(_DRP+'.tmp','wb')); os.replace(_DRP+'.tmp',_DRP)
    except Exception: pass
print('daily readings: %d days, %d reused%s'%(len(DAYS),_n_reused,(' (kept through %s)'%_dr_keep.date()) if _dr_keep is not None else ' (no kept readings matched: every day read)'))
# ---- THE HEIGHT INSIDE A RECESSION IS ITS DAMAGE (Anthony, 17 September 2026; fourth form, the one that stands, chosen in
# ---- collection 193 against ex-post severity - GDP lost, unemployment excess, industrial production lost, payroll depth -
# ---- rank correlation 0.98). One line. Outside an episode: the rule's reading, below 1.00. From the call day to the close
# ---- day: 1.00 plus the damage accumulated so far, in points of unemployment times months. The object is a WEEKLY
# ---- UNEMPLOYMENT RATE: the latest BLS first print published by that day, carried forward week by week by the insured
# ---- unemployment rate's movement since that print's month, scaled by a slope fitted only on the ten years of monthly
# ---- changes known on the call day (beta; first prints throughout). Base = the lowest first print of the twelve months
# ---- known at the call. Damage = sum over the published weeks since the call of max(0, U_hat - base) / 4.345. Complete
# ---- on the close day by construction; nothing after the close enters; each day's reading uses only that day's data.
_ufp=pd.read_csv(os.path.join(_ROOT,'186_realtime_channels_2026-09-15','vintages','UNRATE_firstprint.csv'))
_ufp['date']=pd.to_datetime(_ufp['date']); _ufp['published']=pd.to_datetime(_ufp['published']); _ufp=_ufp.sort_values('date')
_IUW=pd.concat([RT[RT.index<pd.Timestamp('1971-01-01')],spl[spl.index>=pd.Timestamp('1971-01-01')]]).sort_index() if 'RT' in globals() else spl.sort_index()
_IUW=_IUW[~_IUW.index.duplicated(keep='last')].dropna()
_IUPUB=pd.Series([rel_iu(t) for t in _IUW.index],index=_IUW.index)          # week ending -> publication day
def _mmi(y,m,known_by):
    w=_IUW[(_IUW.index.year==y)&(_IUW.index.month==m)]; w=w[_IUPUB.reindex(w.index)<=known_by]
    return float(w.mean()) if len(w) else np.nan
def _beta_at(call,years=10):
    known=_ufp[_ufp['published']<=call].tail(12*years+1); u=known['value'].values.astype(float)
    i=np.array([_mmi(x.year,x.month,call) for x in known['date']],dtype=float); du=np.diff(u); di=np.diff(i); k=~np.isnan(di)&~np.isnan(du)
    return float(np.sum(du[k]*di[k])/np.sum(di[k]*di[k])) if k.sum()>=24 and np.sum(di[k]*di[k])>0 else 1.0
# ---- fifth form (17 September 2026, Anthony: "the nowcast for current times, the data we already have for past times"):
# ---- for every published week from the call to the close, U(week) = the unemployment rate of the week's month AS PUBLISHED
# ---- TODAY where that month's rate exists (every week of a closed recession; the open one's months already printed);
# ---- otherwise - the open recession's latest weeks - the latest print carried by the insured-rate bridge. Base = the lowest
# ---- rate of the twelve months before the call month, as published today; beta from the ten years before the call.
# ---- Damage = sum of max(0, U - base) / 4.345, complete on the close day. Tested against 27 other objects on the data as
# ---- it stands (collection 195): the unemployment rate is the measure the others agree with most.
_ucur_df=pd.read_csv(os.path.join(_ROOT,'186_realtime_channels_2026-09-15','data','UNRATE.csv'))
_ucur=pd.Series(pd.to_numeric(_ucur_df.iloc[:,1],errors='coerce').values,index=pd.to_datetime(_ucur_df.iloc[:,0])).dropna().sort_index()
_ucur=_ucur[~_ucur.index.duplicated(keep='last')]
def _mm_all(y,m):
    w=_IUW[(_IUW.index.year==y)&(_IUW.index.month==m)]; return float(w.mean()) if len(w) else np.nan
def _beta_cur(call,years=10):
    m1=pd.Timestamp(call.year,call.month,1); hist=_ucur[(_ucur.index<m1)&(_ucur.index>=m1-pd.DateOffset(months=12*years+1))]
    du=np.diff(hist.values.astype(float)); im=np.array([_mm_all(x.year,x.month) for x in hist.index],dtype=float); di=np.diff(im); k=~np.isnan(di)&~np.isnan(du)
    return float(np.sum(du[k]*di[k])/np.sum(di[k]*di[k])) if k.sum()>=24 and np.sum(di[k]*di[k])>0 else 1.0
# ---- the scale of ten (17 September 2026, Anthony: "make it on a scale of 10 ... 10 being the worst possible recession"):
# ---- the recession's damage is the geometric mean of the rise's deepest point (points) and of the rise summed week by week
# ---- (point-months) - depth and cumulative loss, the two things the consensus weighs (NBER: depth, diffusion, duration;
# ---- Harding-Pagan / Claessens-Kose-Terrones: amplitude, duration, cumulative loss) - relative to the Great Depression on the
# ---- same arithmetic (unemployment 3.2 in 1929 to 24.9 in 1933, Lebergott/BLS annual rates: depth 21.7 points, 528.3
# ---- point-months over August 1929 - March 1933), on a logarithmic scale (Anthony, 17 Sep 08:50 PDT: "the worst one being
# ---- the Great Depression ... the rest based off of the Great Depression being a 10"): score = 10 * ln(1 + sqrt(depth*sum)) /
# ---- ln(1 + sqrt(21.7*528.3)) - a Richter scale: each point is a fixed multiple (1.6x) of the damage. The Depression is 10;
# ---- 2007-09 reads 5.8, 2020 5.3, 2024 2.3. (The square-root form of 08:30 PDT read 3.7, 3.3, 1.4; a linear form would read
# ---- 1.3, 1.1, 0.2.) Collection 196.
# ---- 08:55 PDT, Anthony tried the linear form (score = 10 * sqrt(depth*sum)/sqrt(21.7*528.3): 2007-09 1.3, 2020 1.1, 2024 0.2;
# ---- deployed 15:52Z) and at 08:58 kept the logarithmic one: "you just gave me the answer ... lets keep it as it is now".
_DEP_DEPTH=21.7; _DEP_PM=528.3; _DEP_X=(_DEP_DEPTH*_DEP_PM)**0.5
def _score(depth,pm): return 10.0*np.log1p((max(depth,0.0)*max(pm,0.0))**0.5)/np.log1p(_DEP_X)
_DMG_CUM={}; _DMG_ROWS=[]
for _a,_b in _EPD:
    if _a<SITE_START: continue
    _m1=pd.Timestamp(_a.year,_a.month,1); _pre=_ucur[(_ucur.index<_m1)&(_ucur.index>=_m1-pd.DateOffset(months=12))]
    if len(_pre)<6: continue
    base=float(_pre.min()); B=_beta_cur(_a)
    wk=[(_t,_p) for _t,_p in _IUPUB.items() if _p>_a and _p<=_b]
    rows=[]; cum=0.0; depth=0.0
    for _t,_p in wk:
        _mk=pd.Timestamp(_t.year,_t.month,1)
        if _mk in _ucur.index: u=float(_ucur[_mk]); how='published'
        else:
            _lm=_ucur.index[-1]; u0=float(_ucur.iloc[-1]); m0=_mm_all(_lm.year,_lm.month)
            u=u0+B*(float(_IUW[_t])-m0) if m0==m0 else u0; how='nowcast'
        ex=max(0.0,u-base); cum+=ex/4.345; depth=max(depth,ex); sc=_score(depth,cum); rows.append((_p,sc))
        _DMG_ROWS.append(dict(published=_p.date().isoformat(),week_ending=_t.date().isoformat(),call=_a.date().isoformat(),close=(None if _b.year==2100 else _b.date().isoformat()),unemployment=round(u,2),how=how,base=base,depth_pts=round(depth,2),point_months=round(cum,3),score_0_10=round(sc,3)))
    _DMG_CUM[_a]=(base,B,pd.Series(dict(rows),dtype=float).sort_index(),cum,depth)   # v3.57: an episode opened after the last claims print has no rows yet
# the damage data, rewritten at every build (weekly with the claims): the live folder and the damage-grade collection
_dmg_df=pd.DataFrame(_DMG_ROWS)
for _pth in (os.path.join('out','damage_weekly.csv'),os.path.join(_ROOT,'193_damage_grade_2026-09-17','out','damage_weekly_live.csv')):
    try: os.makedirs(os.path.dirname(_pth),exist_ok=True); _dmg_df.to_csv(_pth,index=False)
    except Exception as _e: print('damage_weekly.csv not written:',_e)
def _damage(d,call):
    if call not in _DMG_CUM: return 0.0
    s=_DMG_CUM[call][2]
    if len(s)==0: return 0.0
    s=s[s.index<=d]
    return float(s.iloc[-1]) if len(s) else 0.0
# ---- v3.73 (23 September 2026, collection 333; collection 327; Anthony: 'is there a way to meet the consensus? find it!!!'): THE GRADE IN THREE DIMENSIONS. The
# ---- labour dimension above (unemployment depth x point-months) is joined by output (real GDP peak-to-trough x cumulative loss inside the
# ---- episode) and production (industrial production, the same) on the same logarithmic scale with the Great Depression at 10; the grade is
# ---- their mean. Against the ex-post consensus of 196 (six measures, thirteen episodes) it orders 75 of 78 pairs as the consensus does
# ---- (Spearman 0.978; the labour dimension alone 72, 0.938); no weight was fitted. Vintages by the fifth form's rule: printed quarters
# ---- and months as published today, the open recession's unprinted quarter bridged by GDPNow. s2/damage_dimensions.py.
_D3={}; _DIM_EP={}; _DIM_ROWS=[]; _DIM_NOTE='not run'; _DIM_ANCH=None
try:
    import importlib.util as _iu333c
    _spd=_iu333c.spec_from_file_location('damage_dimensions',os.path.join('s2','damage_dimensions.py')); _dd333=_iu333c.module_from_spec(_spd); _spd.loader.exec_module(_dd333)
    _cur333=_dd333.load_current(os.path.join(_ROOT,'onset-detector-new-2026-08-23','27_realtime_vintages','alfred_all_vintages')); _DIM_ANCH=dict(_dd333.DEP)
    for _a,_b in _EPD:
        if _a not in _DMG_CUM: continue
        _wk=[(pd.Timestamp(r['week_ending']),pd.Timestamp(r['published'])) for r in _DMG_ROWS if r['call']==_a.date().isoformat()]
        _openep=(_b.year==2100); _path=_dd333.episode_path(_cur333,_a,(None if _openep else _b),_wk,open_episode=_openep)
        _lab=_DMG_CUM[_a][2]
        if not len(_path): continue
        _g={}
        for _p in _path.index:
            _ls=_lab[_lab.index<=_p]; _lv=float(_ls.iloc[-1]) if len(_ls) else 0.0
            _g[_p]=_dd333.grade(_lv,float(_path.loc[_p,'output']),float(_path.loc[_p,'production']))
            _DIM_ROWS.append(dict(call=_a.date().isoformat(),published=_p.date().isoformat(),labour_0_10=round(_lv,3),output_0_10=round(float(_path.loc[_p,'output']),3),production_0_10=round(float(_path.loc[_p,'production']),3),grade_0_10=round(_g[_p],3),gdp_pt_pct=float(_path.loc[_p,'gdp_pt']),gdp_cum_pct_quarters=float(_path.loc[_p,'gdp_cum']),gdp_nowcast=bool(_path.loc[_p,'gdp_nowcast']),ip_pt_pct=float(_path.loc[_p,'ip_pt']),ip_cum_pct_months=float(_path.loc[_p,'ip_cum'])))
        _D3[_a]=pd.Series(_g,dtype=float).sort_index(); _last=_path.iloc[-1]; _lsv=float(_lab.iloc[-1]) if len(_lab) else 0.0
        _DIM_EP[_a]=dict(damage_labour=round(_lsv,2),damage_output=round(float(_last['output']),2),damage_production=round(float(_last['production']),2),gdp_pt_pct=round(float(_last['gdp_pt']),2),gdp_cum_pct_quarters=round(float(_last['gdp_cum']),2),gdp_nowcast=bool(_last['gdp_nowcast']),ip_pt_pct=round(float(_last['ip_pt']),2),ip_cum_pct_months=round(float(_last['ip_cum']),1))
    _DIM_NOTE='ran: %d episodes; GDP vintage %s, production vintage %s, GDPNow %s'%(len(_D3),_cur333['gdp_vintage'].date(),_cur333['ip_vintage'].date(),('%s %.2f%% (%s)'%(_cur333['nowcast']['quarter'].strftime('%Y-Q')+str((_cur333['nowcast']['quarter'].month-1)//3+1),_cur333['nowcast']['rate'],_cur333['nowcast']['vintage'].date()) if _cur333.get('nowcast') else 'none'))
    try: pd.DataFrame(_DIM_ROWS).to_csv(os.path.join('out','damage_dimensions_weekly.csv'),index=False)
    except Exception as _e: print('damage_dimensions_weekly.csv not written:',_e)
except Exception as _e333c:
    _DIM_NOTE='did not run (%r); the labour dimension alone stands'%(_e333c,)
print('v3.73 damage dimensions:',_DIM_NOTE)
def _damage3(d,call):
    if call in _D3 and len(_D3[call]):
        s=_D3[call][_D3[call].index<=d]
        return float(s.iloc[-1]) if len(s) else 0.0
    return _damage(d,call)
for _e in EP:   # the record table shows each recession's damage score (17 September 2026)
    if not _e.get('open_pub'): continue
    _a=pd.Timestamp(_e['open_pub']); _b=pd.Timestamp(_e['close_pub']) if _e.get('close_pub') else pd.Timestamp(today)
    if _a in _DMG_CUM: _e['damage_score']=round(_damage3(_b,_a),1); _e['damage_pm']=round(_DMG_CUM[_a][3],1); _e['damage_depth']=round(_DMG_CUM[_a][4],1); _e.update(_DIM_EP.get(_a,{}))   # v3.73: the grade in three dimensions
DMG=[]
for i,d in enumerate(DD):
    if DP[i]=='open' and d>=SITE_START:
        ep=[(a,b) for a,b in _EPD if a<=d<=b]
        if ep:
            a,b=ep[0]; dmg=_damage3(d,a); DMG.append(round(dmg,2)); DV[i]=1.0+dmg; continue   # v3.73: the grade in three dimensions
    DMG.append(None)
print('v3.73 grade at the close, by episode (labour, output, production -> grade):',[(a.date().isoformat(),_DIM_EP.get(a,{}).get('damage_labour'),_DIM_EP.get(a,{}).get('damage_output'),_DIM_EP.get(a,{}).get('damage_production'),round(_damage3(b,a),2)) for a,b in _EPD if a in _DMG_CUM])
print('damage at the close, by episode (score of 10; point-months; depth):',[(a.date().isoformat(),round(_damage(b,a),2),round(_DMG_CUM[a][3],1),round(_DMG_CUM[a][4],1)) for a,b in _EPD if a in _DMG_CUM],'| weekly rows',len(_DMG_ROWS),'nowcast rows',sum(1 for r in _DMG_ROWS if r['how']=='nowcast'))
_tick('daily series')
SERIES_D=pd.DataFrame({'value':DV,'reading':DR,'phase':DP,'branch':DB,'damage':DMG},index=pd.DatetimeIndex(DD)); SERIES_D=SERIES_D[SERIES_D.index>=SITE_START]
# ---- collection 335 (23 September 2026; plan item 18 and L7): THE NEAR-MISS LOG. Outside an episode the line is the distance of the
# ---- nearest branch to its line (1.00 = a call); every spell at or above 0.80 is logged - start, end, the highest reading, the branch -
# ---- as the false-alarm audit of the future and the margin the expansion ledger files each year. Evidence only; nothing moves.
NEAR_MISSES=[]
try:
    _nm=None
    for _t,_row in SERIES_D.iterrows():
        _hot=(_row['phase']!='open') and (_row['value'] is not None) and (float(_row['value'])>=0.80)
        if _hot and _nm is None: _nm=dict(start=_t.date().isoformat(),end=_t.date().isoformat(),max=float(_row['value']),branch=_row['branch'],days=1)
        elif _hot: _nm.update(end=_t.date().isoformat(),days=_nm['days']+1); _nm['max']=max(_nm['max'],float(_row['value'])); _nm['branch']=_row['branch'] if float(_row['value'])>=_nm['max'] else _nm['branch']
        elif _nm is not None: NEAR_MISSES.append(_nm); _nm=None
    if _nm is not None: NEAR_MISSES.append(_nm)
    for _x in NEAR_MISSES: _x['max']=round(_x['max'],3); _x['branch']=_br(_x['branch']) if '_br' in globals() else _x['branch']
    print('near misses (>= 0.80 outside an episode): %d spells; the last %s'%(len(NEAR_MISSES),NEAR_MISSES[-1] if NEAR_MISSES else None))
except Exception as _e: print('near-miss log not built:',_e)
SERIES=SERIES[SERIES.index>=SITE_START]
# ---- the latest readings, and the forward log ----
def lastv(s): s=s.dropna(); return float(s.iloc[-1]), s.index[-1].date().isoformat()
def nxt_thu(d):
    d=pd.Timestamp(d); return (d+pd.offsets.Week(weekday=3)).date().isoformat()
def nxt_claims(through,days=12):
    # the Thursday whose release carries the week after the last week in hand (claims: week end + 12 days; the insured week
    # and the state rates: + 19). A release day already past whose data are not yet in hand stays the 'next' (marked pending).
    t=pd.Timestamp(through)+pd.Timedelta(days=days)
    # audit-0924 (24 Sep 2026): a Thursday already gone by is not printed as the next release with '(released; not yet
    # posted)' - the next Thursday is. A feed that stops arriving is for the checks and the watchdogs, not for the page.
    while t<pd.Timestamp(today): t=t+pd.Timedelta(days=7)
    return t.date().isoformat()
def first_fri(d):
    m=(pd.Timestamp(d)+pd.offsets.MonthBegin(1)); f=m+pd.offsets.Week(weekday=4) if m.weekday()!=4 else m; return f.date().isoformat()
R=[]
_tick('readings')
def nxt_survey(through):
    # the next survey week (the week containing the 12th of the month after the last one in hand); its rate arrives 12 days after that Saturday
    m=pd.Timestamp(through)+pd.DateOffset(months=1); d=pd.Timestamp(m.year,m.month,12); sat=d+pd.Timedelta(days=(5-d.weekday())%7)
    return nxt_claims(sat,12)
def add(side,name,series,line,through=None,nxt=''):
    v,dt=lastv(series)
    if isinstance(nxt,int): nxt=nxt_claims(dt,nxt)
    elif nxt=='survey': nxt=nxt_survey(dt)
    R.append(dict(side=side,object=name,reading=round(v,4),line=line,ratio=round(v/line,3) if line else None,through=through or dt,next=nxt))
add('open',f"insured rate, rise above its {p['look']}-week low"+(' (co-signed within 0.2 of the line)' if COS else ''),RAW['U']*p['u45'],p['u45'],nxt=nxt_claims(lastv(RAW['U'])[1],19))
add('open','insured rate, rise above its 52-week low',RAW['L']*p['low'],p['low'],nxt=nxt_claims(lastv(RAW['L'])[1],19))
add('open',('initial claims, 4-week mean above its base (the higher of its 52-week low and 85% of its 5-year median), percent' if 'ALPHA' in globals() else 'initial claims, 4-week mean above its 52-week low, percent')+(' (co-signed within 15 of the line)' if COS else ''),RAW['I']*p['ic'],p['ic'],nxt=12)
if COS: add('open','household co-signer: 3-month average unemployment rate above its 12-month low, as last published (signs a near-line insured-rate or claims proposal)',g.dropna(),COS_THR,nxt=first_fri(today))
add('open',f"Sahm gap (three-month average unemployment rate above its twelve-month low, as it stood on the release day; it "
            f"proposes only with the vacancy rate {p['vl']:g} or more off its 4-month high in two of the prior {p['hback']:g} months)",
    RAW['X']*p['sahm'],p['sahm'],nxt=first_fri(today))   # v3.71d (22 September 2026): the vacancy condition and its look-back, from the rule
add('open',f'sudden stop: one week of initial claims above the claims base, percent (fires with the S&P 500 {KC[1]} percent under its 20-day high)',gKr*KC[0],float(KC[0]),nxt=12)
_TNAME={'unemp':'"unemployment"','layoffs':'"layoffs"','laidoff':'"laid off"'}
for _tag,(_tdd,_tgg,_trel) in (GT_TERMS.items() if 'GT_TERMS' in globals() else ([('unemp',(GT_DAY,GT7,GT_REL))] if 'GT_REL' in globals() else [])):
    add('open',f'sudden stop: the search week - 7-day mean of Google searches for {_TNAME.get(_tag,_tag)} above its base, percent (fires with the S&P 500 20 percent under its 20-day high at that day\'s close; known the next morning; the earliest term fires)',_trel.dropna(),float(KC[0]),nxt='daily')
_crd=((1-_SPX/_SPX.rolling(20,min_periods=10).max())*100).dropna()     # the market gate at the latest close (the search week reads the day's close; the claims week the close before its release)
add('open',f'sudden stop: S&P 500 below its high of the prior twenty trading days, percent, at the latest close (the claims week reads the close before its release, the search week the day\'s close)',_crd,float(KC[1]),nxt='daily')
# v3.63 (Core v7-W, collection 289): the activity opener's four objects, as s2/activity_opener.py read them for this build
if _AO_ST.get('reading'):
    _aor=_AO_ST['reading']; _aol=_AO_ST.get('lines') or {}
    add('open','activity opener: industrial production as published, below its high of the prior twelve months, log points (one of four conditions, with the S&P 500 %g percent below its 250-day high, the policy rate %g point above its 365-day low and state breadth at %g percent; the cell and gate the causal walk from 1948 chose)'%(100*_aol.get('market',0.10),_aol.get('tightening',0.10),100*_aol.get('breadth_share',0.33)),pd.Series([100*_aor['production_fall12']],index=[pd.Timestamp(_aor['production_vintage'])]),100*_aol.get('production',0.02),nxt=_ao_next())
    add('open','activity opener: S&P 500 below its high of the prior 250 trading days, log percent, at the latest close',pd.Series([100*_aor['market_drawdown']],index=[pd.Timestamp(_aor['market_close_date'])]),100*_aol.get('market',0.10),nxt='daily')
    if 'policy_rise' in _aor:
        add('open','activity opener: the policy rate above its low of the prior 365 days, points (the FOMC target range\'s upper limit, FRED DFEDTARU)',pd.Series([float(_aor['policy_rise'])],index=[pd.Timestamp(_aor['policy_date'])]),_aol.get('tightening',0.10),nxt=_AO_ST.get('next_fomc') or '')
    if 'breadth_share' in _aor:
        add('open','activity opener: state breadth, the share of states with the insured-rate proxy 0.45 point above its twelve-month low, in the latest month public (the gate)',pd.Series([float(_aor['breadth_share'])],index=[pd.Timestamp(_aor['breadth_month']+'-01')]),_aol.get('breadth_share',0.33),through=_aor['breadth_month'],nxt=_AO_ST.get('next_breadth_publication') or '')
if gW is not None: add('open',f"survey-week insured rate, rise above its 52-week low (branch W, line {p['wline']})",RAW['W']*p['wline'],p['wline'],nxt='survey')
if gV is not None: add('open',f"survey-week insured rate, rise above its 52-week low (branch V, line {p['wline2']})",RAW['V']*p['wline2'],p['wline2'],nxt='survey')
if gB is not None: add('open','state breadth, share of states with the insured rate 0.20 above its 52-week low',RAW['B']*p['bshare'],p['bshare'],nxt=19)
add('confirm','vacancy rate, 4-month mean below its 4-month maximum (openings as they stood on the JOLTS release day)',cV*p['vl'],p['vl'],nxt='JOLTS, next release')
add('confirm','hours pair (factory hours 2% off their 12-month high and nondurable jobs -1.2% over 3 months, as they stood on the release day; 1 = both)',cH,1.0,nxt=first_fri(today))
add('confirm',('housing x rate pair (starts or building permits 29 log points below their 12-month high, and the unemployment rate 0.4 above its 18-month low, each as it stood on its release day; 1 = both halves at their lines)' if 'mkpair_either_asof' in globals() else 'housing x rate pair (starts and the unemployment rate, each as it stood on its release day; 1 = both halves at their lines)'),cP*p['hline'],p['hline'],nxt='housing starts, next release')
add('confirm',f"starts x vacancy pair (starts {p['starts']:g} log points below their 12-month high and the vacancy rate {p['vl']:g} off its "
                f"4-month high; 1 = both)",cSV,1.0,nxt='housing starts, next release')   # v3.71d (22 September 2026): the lines are the rule's, not constants
add('confirm','paper spread (the wider of AA financial and AA nonfinancial 30-day paper over the 3-month bill), 13-week mean above its 39-week low, points',cS*p['spr'],p['spr'],nxt='H.15 week, next posting')
add('close','initial claims 3-week mean, drop from its 26-week maximum, log points',pd.Series(_FI['drop'].values,index=_CW),float(D_),nxt=12)
add('close','run of falling weeks',pd.Series(_FI['run'].values,index=_CW).astype(float),3.0,nxt=12)
add('close','hump above the 52-week minimum, log points',pd.Series(_FI['amp'].values,index=_CW),20.0,nxt=12)
add('close','S&P 500 above its 26-week low on the release day, percent',pd.Series(sp_,index=_CW),float(S_),nxt=12)
add('close','continued claims 4-week mean below its 26-week maximum, log points',pd.Series(fc_,index=_CW),3.0,nxt=12)
add('close','insured rate 4-week mean below its 26-week maximum, tenths',pd.Series(du_,index=_CW),3.0,nxt=12)
logp=os.path.join(LIVE,'live','LIVE_LOG_v321.tsv'); new=not os.path.exists(logp)
with open(logp,'a') as f:
    if new: f.write('run_date\tside\tobject\treading\tline\tat_or_above\tdata_through\n')
    for r in R: f.write(f"{today}\t{r['side']}\t{r['object']}\t{r['reading']}\t{r['line']}\t{'YES' if r['line'] and r['reading']>=r['line'] else 'no'}\t{r['through']}\n")
# ---- THE CALENDAR THE PAGE KEEPS: every release the rule reads for the next 150 days, with its time (Eastern), so the
# page can tell from its own clock which release comes next, which have come out since it was built, and when it
# updates. Weekly claims Thursdays 8:30 (the Wednesday before Thanksgiving); the H.15 week Fridays 4:15 PM; the dated
# BLS and Census days from cache/release_schedule.csv.
import importlib.util as _ilu
_sp=_ilu.spec_from_file_location('bhs_schedule',os.path.join(os.getcwd(),'bhs_schedule.py')); _bs=_ilu.module_from_spec(_sp); _sp.loader.exec_module(_bs)
CAL=_bs.calendar(150)     # date, time (Eastern), kind, what, expected (beyond the fetched calendars: the usual timing)
_dated_through=_bs.dated_through()
# ---- the next releases the rule reads, earliest first ----
def _nextcal(path,col):
    try:
        c=pd.read_csv(path); d=pd.to_datetime(c[col],errors='coerce').dropna(); d=d[d>pd.Timestamp(today)]
        return d.min().date().isoformat() if len(d) else None
    except Exception: return None
NEXT=[dict(date=nxt_claims(lastv(RAW['I'])[1],12),what='Weekly claims (initial claims, continued claims, insured unemployment rate), Department of Labor, 8:30 ET'),
      dict(date=first_fri(today),what='Employment Situation (unemployment rate, factory hours, nondurable employment), BLS, 8:30 ET')]
# the published schedules (cache/release_schedule.csv, BLS and Census, sourced in the file) first, then the lab's release
# calendars; if neither reaches past today, the usual timing from the last month of data (JOLTS about five weeks after
# the reference month, starts about two and a half weeks after it)
def _sched(series):
    try:
        c=pd.read_csv('cache/release_schedule.csv'); c=c[c['series']==series]; d=pd.to_datetime(c['release_date'],errors='coerce').dropna(); d=d[d>pd.Timestamp(today)]
        return d.min().date().isoformat() if len(d) else None
    except Exception: return None
def _usual(through,months,day):
    t=pd.Timestamp(through)+pd.DateOffset(months=months); t=t.replace(day=min(day,28))
    while t<=pd.Timestamp(today): t=(t+pd.DateOffset(months=1)).replace(day=min(day,28))
    return t.date().isoformat()
_j=_sched('JTSJOL') or _nextcal('cache/jolts_release_calendar_2004_2026.csv','release_date')
NEXT.append(dict(date=_j or _usual(lastv(G)[1],2,5),what='JOLTS (job openings), BLS, 10:00 ET'+('' if _j else ' - about this date, not yet scheduled')))
_h=_sched('HOUST') or _nextcal('cache/relcal_HOUST.csv','first_release')
NEXT.append(dict(date=_h or _usual(lastv(MX)[1],2,17),what='Housing starts, Census, 8:30 ET'+('' if _h else ' - about this date, not yet scheduled')))
_e=_sched('UNRATE')
if _e: NEXT[1]['date']=_e
NEXT.append(dict(date=next((c['date'] for c in CAL if c['kind']=='h15'),'weekly'),what='H.15 week (commercial paper and bill rates), Federal Reserve, 4:15 PM ET on the first business day after the week'))
NEXT.sort(key=lambda z:(0,z['date']) if len(z['date'])==10 else (1,z['date']))

# ---- v3.71b (22 September 2026, collection 310): the H.15 and S&P 500 rows' texts made exact ----
# ---- every feed the rule reads: where it comes from, how often it updates, what it is through, when it updates next ----
def _fthr(x):
    try: return lastv(x)[1]
    except Exception: return None
def _dim_thr(sid):   # v3.73 feeds (23 September 2026, collection 333): the last observation of the latest vintage in the ALFRED table
    try:
        t_=pd.read_csv(os.path.join(_ROOT,'onset-detector-new-2026-08-23','27_realtime_vintages','alfred_all_vintages',sid+'_all_vintages.csv'),index_col=0); v_=pd.to_numeric(t_[t_.columns[-1]],errors='coerce').dropna()
        return pd.Timestamp(v_.index[-1])
    except Exception: return None
def _fval(x,fmt='{:,.0f}',suf=''):
    # the latest value of a feed, as it stands, for the data inventory
    try: return fmt.format(lastv(x)[0])+suf
    except Exception: return None
_h15next=next((c['date'] for c in CAL if c['kind']=='h15'),None)
_nxt=lambda w: next((n['date'] for n in NEXT if n['what'].startswith(w)),None)
def _bnote():
    # audit-0924 (25 Sep 2026): no note. The breadth object reads the states' insured rates as FRED posts them each Friday
    # (the Department's current file), not the first-print archive, so the archive's eight missing 2025 weeks never hold
    # it back; the note used to say they did.
    return None
# ---- 358 (23 September 2026): the data page's cadences, sources and next days made exact (display only; the rule untouched) ----
# FRED posts DFEDTARU every day, weekends included, at about 8:01 AM ET (51 archived stamps since January 2025); an FOMC decision
# reaches it in the next morning's post (7 of 7 changes since 2024). The Board posts the H.15 every business day at 4:15 PM ET.
# Google's days, as the tool reads them (tz=0), are complete at midnight UTC (8 PM ET in summer, 7 PM in winter). FRED posts the
# S&P 500 close the same evening (about 8 PM ET). The state insured rates run one week behind initial claims. Evidence:
# 358_data_page_audit_2026-09-23 (out/wayback_updated.json, out/probe.json, out/checks.json, out/fomc_day.json).
from zoneinfo import ZoneInfo as _ZI358
_now358=datetime.datetime.now(_ZI358('America/New_York'))
def _fred_daily_next():   # FRED's next daily post of DFEDTARU (about 8:01 AM ET, every day)
    d=_now358.date() if (_now358.hour,_now358.minute)<(8,1) else _now358.date()+datetime.timedelta(days=1)
    return d.isoformat()
def _h15_next():          # the Board's next business-day post of the H.15, 4:15 PM ET
    d=_now358.date()
    if not (d.weekday()<5 and d not in _bs.federal_holidays(d.year) and (_now358.hour,_now358.minute)<(16,15)):
        d+=datetime.timedelta(days=1)
        while d.weekday()>=5 or d in _bs.federal_holidays(d.year): d+=datetime.timedelta(days=1)
    return d.isoformat()
def _utc_day_end_next():  # the next end of a UTC day, as a New York date (Google's days are read with tz=0; weekends included)
    u=datetime.datetime.now(datetime.timezone.utc)
    return (datetime.datetime(u.year,u.month,u.day,tzinfo=datetime.timezone.utc)+datetime.timedelta(days=1)).astimezone(_ZI358('America/New_York')).date().isoformat()
def _h15_through():       # the latest date the H.15 row's series are printed through (DCPF1M and DCPN30 daily, WTB3MS weekly)
    ds=[]
    for p_ in (os.path.join(_ROOT,'25_fred_daily_weekly','fred_daily','DCPF1M.csv'),os.path.join(_ROOT,'25_fred_daily_weekly','fred_daily','DCPN30.csv'),os.path.join(_ROOT,'25_fred_daily_weekly','fred_weekly','WTB3MS.csv')):
        try:
            q_=pd.read_csv(p_); v_=q_[pd.to_numeric(q_.iloc[:,1],errors='coerce').notna()]; ds.append(str(v_.iloc[-1,0])[:10])
        except Exception: pass
    return max(ds) if ds else _fthr(cS)
_tick('feeds')
FEEDS=[
 dict(name='Initial claims, continued claims, insured unemployment rate',source='Department of Labor (the UI claims news release; ALFRED vintages after it)',every='Weekly - Thursday 8:30 AM ET (Wednesday before a Thursday holiday)',through=_fthr(ICfp),next=_nxt('Weekly claims'),url='https://www.dol.gov/ui/data.pdf',value=_fval(ICfp,'{:,.0f}',' initial claims, week ending '+str(_fthr(ICfp))),auto='yes'),
 dict(name='State insured unemployment rates (the breadth object)',source='Department of Labor (page 8 of the weekly release; the advance state table of the release PDF while the archive catches up)',every='Weekly - Thursday 8:30 AM ET, one week behind initial claims',through=_fthr(RAW['B']),next=_nxt('Weekly claims'),url='https://oui.doleta.gov/unemploy/claims.asp',value=None,auto='yes',note=_bnote()),
 dict(name='Unemployment rate, factory hours, nondurable employment',source='Bureau of Labor Statistics, Employment Situation',every='Monthly - usually the first Friday, 8:30 AM ET',through=_fthr(g_asof),next=_nxt('Employment Situation'),url='https://www.bls.gov/news.release/empsit.toc.htm',value=_fval(g_asof,'{:.2f}',' Sahm gap, points (the unemployment rate object the rule reads)'),auto='yes'),
 dict(name='Job openings (the vacancy rate)',source='Bureau of Labor Statistics, JOLTS',every='Monthly - about five weeks after the month, 10:00 AM ET',through=_fthr(G),next=_nxt('JOLTS'),url='https://www.bls.gov/jlt/',value=_fval(G,'{:+.2f}',' points from its four-month high (the confirmer needs the vacancy rate falling)'),auto='yes'),
 dict(name='Housing starts and building permits',source='Census Bureau, New Residential Construction',every='Monthly - about the 17th, 8:30 AM ET',through=_fthr(MX),next=_nxt('Housing starts'),url='https://www.census.gov/construction/nrc/index.html',value=_fval(MX,'{:.1f}',' log points below the 12-month high (the line is 29)'),auto='yes'),
 dict(name='Commercial paper and three-month bill rates (the spread)',source='Federal Reserve, H.15 selected interest rates',every='Daily - the Board posts the H.15 every business day at 4:15 PM ET, carrying the previous business day\'s rates (the bill rate is a weekly series)',through=_h15_through(),next=_h15_next(),   # 358: was the H.15 week (through=_fthr(cS), next=_h15next)
     url='https://www.federalreserve.gov/releases/h15/',value=_fval(cS,'{:.2f}',' points, the wider paper market over the 3-month bill (the line is 0.90)'),auto='yes'),
 dict(name='S&P 500 daily close (the market gate of the sudden stop, the activity opener and the concurrence branch, and a confirmation of the claims closer)',source='Yahoo Finance close at the 5:05 PM ET run, corrected to the official close on FRED (SP500), which FRED posts the same evening, about 8 PM ET',every='Every trading day - read at the 5:05 PM ET run',through=_fthr(_SPX),next='the next weekday close',url='https://finance.yahoo.com/quote/%5EGSPC/',value=_fval(_SPX,'{:,.2f}',' at the close'),auto='yes'),
 dict(name='Industrial production, as published (the activity opener)',source='Federal Reserve, G.17 Industrial Production and Capacity Utilization (each month as first published: ALFRED vintages)',every='Monthly - about the 16th, 9:15 AM ET',through=(_AO_ST.get('reading') or {}).get('production_last_month'),next=_ao_next(),url='https://www.federalreserve.gov/releases/g17/current/',value=None,auto='yes'),
 dict(name='Federal funds target range, upper limit (the activity opener\'s tightening condition)',source='Federal Reserve, FOMC statement (FRED DFEDTARU, the daily series)',every='Daily - FRED posts the series every day, weekends included, at about 8:01 AM ET; it moves only at an FOMC decision (eight scheduled meetings a year, the statement at 2:00 PM ET), carried by the next morning\'s post',through=(_AO_ST.get('reading') or {}).get('policy_date'),next=_fred_daily_next(),   # 358: was the FOMC days (next=_AO_ST.get('next_fomc'))
     url='https://fred.stlouisfed.org/series/DFEDTARU',value=None,auto='yes'),
 dict(name='State continued weeks claimed, ETA 539 (the activity opener\'s breadth gate)',source='Department of Labor, ETA 539 weekly state claims (continued weeks claimed, by state), over state payroll employment (BLS, from FRED)',every='Monthly - each month is read 21 days after it ends, from the Department\'s weekly file',through=(_AO_ST.get('reading') or {}).get('breadth_month'),next=_AO_ST.get('next_breadth_publication'),url='https://oui.doleta.gov/unemploy/claims.asp',value=None,auto='yes'),
 dict(name='State unemployment rates, all 51 (the second opener)',source='Bureau of Labor Statistics, Local Area Unemployment Statistics, as first printed (ALFRED initial releases)',
      every='Monthly - with the State Employment and Unemployment release, about three weeks after the month, 10:00 AM ET',
      through=(SB_ST.get('through') or '')[:10] or None,next=SB_ST.get('next_release'),url='https://www.bls.gov/news.release/laus.htm',
      value=('%.0f%% of states' % (100*float(SB_ST['latest_share']))) if SB_ST.get('latest_share') is not None else None,auto='yes'),
 # v3.73 feeds (23 September 2026, collection 333): the grade's output dimension reads real GDP and, for the unprinted quarter, GDPNow; the payroll closer reads payrolls with the jobs report
 dict(name='Real GDP (the damage grade\'s output dimension)',source='Bureau of Economic Analysis, Gross Domestic Product news release (FRED GDPC1, the latest vintage)',every='Quarterly - the advance estimate about four weeks after the quarter, revised in each of the next two months; 8:30 AM ET',
      through=(lambda _q: (_q.strftime('%Y-%m') if _q is not None else None))(_dim_thr('GDPC1')),next=_sched('GDPC1'),url='https://www.bea.gov/data/gdp/gross-domestic-product',value=None,auto='yes'),
 dict(name='GDPNow (the output dimension\'s bridge for the quarter not yet printed)',source='Federal Reserve Bank of Atlanta, GDPNow (FRED GDPNOW, every update as a vintage)',every='Several times a month, on the days of the releases it reads (FRED carries each update between about 10:30 AM and 1 PM ET); the Atlanta Fed posts its schedule',
      through=(lambda _q: (_q.strftime('%Y-%m') if _q is not None else None))(_dim_thr('GDPNOW')),next=_sched('GDPNOW'),url='https://www.atlantafed.org/cqer/research/gdpnow',value=None,auto='yes'),
 dict(name='Sahm rule, real time (the comparator on the speed panel)',source='FRED SAHMREALTIME',every='Monthly - FRED posts it on the morning of the employment report, after the Bureau\'s 8:30 AM ET release',through=(lambda: (lambda _c: pd.to_datetime(_c.iloc[:,0]).max().strftime('%Y-%m') if len(_c) else None)(pd.read_csv('cache/SAHMREALTIME.csv')) if os.path.exists('cache/SAHMREALTIME.csv') else None)(),next=_nxt('Employment Situation'),url='https://fred.stlouisfed.org/series/SAHMREALTIME',value=(lambda: (lambda _c: '{:.2f}'.format(float(_c.iloc[-1,1]))+' (the rule fires at 0.50)' if len(_c) else None)(__import__('pandas').read_csv('cache/SAHMREALTIME.csv')) if os.path.exists('cache/SAHMREALTIME.csv') else None)(),auto='yes'),
]
_TSRC={'unemp':'"unemployment"','layoffs':'"layoffs"','laidoff':'"laid off"'}
_TQ={'unemp':'unemployment','layoffs':'layoffs','laidoff':'laid%20off'}
for _tg,(_a,_b,_r) in (GT_TERMS.items() if 'GT_TERMS' in globals() else []):
    FEEDS.append(dict(name=f'Search week: Google searches for {_TSRC.get(_tg,_tg)} (the sudden stop\'s second labour datum)',source='Google Trends, United States, daily index stitched onto one scale and extended each day',every="Daily - a day's index is complete when the day ends in UTC (8 PM ET in summer, 7 PM in winter), weekends included; read at every weekday close",through=_fthr(_r),next=_utc_day_end_next(),auto='yes',url='https://trends.google.com/trends/explore?date=today%203-m&geo=US&q='+_TQ.get(_tg,_tg),value=_fval(_r,'{:+.1f}',' per cent, the 7-day mean over its base (the line is 35)')))
_FEED_IDS=[('Initial claims','ICSA, CCSA, IURSA'),('State insured','ETA 539 state insured rates'),('Unemployment rate, factory','UNRATE, AWHMAN, NDMANEMP, PAYEMS'),('Job openings','JTSJOL, CLF16OV'),
           ('Housing starts','HOUST, PERMIT'),('Commercial paper','DCPF1M, DCPN30, WTB3MS'),('S&P 500','^GSPC'),('Sahm rule','SAHMREALTIME'),('Industrial production','INDPRO'),('Federal funds target','DFEDTARU'),('State continued weeks','ETA 539'),('State unemployment rates','LAUS state rates (51)'),('Real GDP','GDPC1'),('GDPNow','GDPNOW')]   # GDPC1, GDPNOW, PAYEMS: v3.73
from zoneinfo import ZoneInfo as _ZI0
_now_et=datetime.datetime.now(_ZI0('America/New_York'))
for _f in FEEDS:   # 17 September 2026: the data page names the series behind each feed; a 'next weekday' becomes its date
    if isinstance(_f.get('next'),str) and 'next weekday' in _f['next']:
        # the S&P 500: today's close if the market has not closed yet today, else the next weekday's; the search week
        # (today's index is known tomorrow morning): the next weekday
        if _f['name'].startswith('S&P') and _now_et.weekday()<5 and (_now_et.hour<16 or str(_f.get('through') or '')<str(today)): _d=pd.Timestamp(today)
        else:
            _d=pd.Timestamp(today)+pd.Timedelta(days=1)
            while _d.weekday()>=5: _d=_d+pd.Timedelta(days=1)
        _f['next']=_d.date().isoformat()
    _f['ids']=next((v_ for k_,v_ in _FEED_IDS if _f['name'].startswith(k_)),None)
    if _f['ids'] is None and _f['name'].startswith('Search week'):
        _m_=_re.search(r'searches for ("[^"]+")',_f['name'])
        _f['ids']='Google Trends '+(_m_.group(1) if _m_ else '')
# 17 September 2026 (Anthony: "just provide the data"): each feed's "where it stands" is the latest published value of
# every series it names, in the ID column's order and nothing else - the monthly series from their vintage tables' last
# column (the value as first published, which is what the rule reads), the weekly and daily ones from the current files
_AL0=os.path.join(_ROOT,'onset-detector-new-2026-08-23','27_realtime_vintages','alfred_all_vintages')
_D0=os.path.join(_ROOT,'24_bristow_rule_lab','workspace','lab','data','fred_weekly'); _C25=os.path.join(_ROOT,'25_fred_daily_weekly')
def _last_num(p_):
    q_=pd.read_csv(p_); v_=pd.to_numeric(q_.iloc[:,1],errors='coerce').dropna(); return float(v_.iloc[-1])
def _last_vint(sid):
    t_=pd.read_csv(os.path.join(_AL0,sid+'_all_vintages.csv'),index_col=0); v_=pd.to_numeric(t_[t_.columns[-1]],errors='coerce').dropna(); return float(v_.iloc[-1])
_RAWF={'ICSA':(lambda: _last_num(os.path.join(_D0,'ICSA.csv')),'{:,.0f}'),'CCSA':(lambda: _last_num(os.path.join(_D0,'CCSA.csv')),'{:,.0f}'),'IURSA':(lambda: _last_num(os.path.join(_D0,'IURSA.csv')),'{:.1f}'),
 'UNRATE':(lambda: _last_vint('UNRATE'),'{:.1f}'),'AWHMAN':(lambda: _last_vint('AWHMAN'),'{:.1f}'),'NDMANEMP':(lambda: _last_vint('NDMANEMP'),'{:,.0f}'),
 'PAYEMS':(lambda: _last_vint('PAYEMS'),'{:,.0f}'),'GDPC1':(lambda: _last_vint('GDPC1'),'{:,.1f}'),'GDPNOW':(lambda: _last_vint('GDPNOW'),'{:.2f}'),   # v3.73
 'JTSJOL':(lambda: _last_vint('JTSJOL'),'{:,.0f}'),'CLF16OV':(lambda: _last_vint('CLF16OV'),'{:,.0f}'),'HOUST':(lambda: _last_vint('HOUST'),'{:,.0f}'),'PERMIT':(lambda: _last_vint('PERMIT'),'{:,.0f}'),
 'DCPF1M':(lambda: _last_num(os.path.join(_C25,'fred_daily','DCPF1M.csv')),'{:.2f}'),'DCPN30':(lambda: _last_num(os.path.join(_C25,'fred_daily','DCPN30.csv')),'{:.2f}'),'WTB3MS':(lambda: _last_num(os.path.join(_C25,'fred_weekly','WTB3MS.csv')),'{:.2f}'),
 '^GSPC':(lambda: lastv(_SPX)[0],'{:,.2f}'),'SAHMREALTIME':(lambda: _last_num('cache/SAHMREALTIME.csv'),'{:.2f}'),'INDPRO':(lambda: float((_AO_ST.get('reading') or {})['production_level']),'{:.4f}'),'DFEDTARU':(lambda: float((_AO_ST.get('reading') or {})['policy_rate']),'{:.2f}')}
# the units, as the publisher states them (Anthony, 17 September 2026: "make sure the proper units are displayed for each datum")
_UNITS_FEED={'ICSA':'claims, seasonally adjusted','CCSA':'claims, seasonally adjusted','IURSA':'percent, seasonally adjusted','UNRATE':'percent, seasonally adjusted','AWHMAN':'hours per week, seasonally adjusted',
 'NDMANEMP':'thousands of persons, seasonally adjusted','JTSJOL':'thousands of openings, seasonally adjusted','CLF16OV':'thousands of persons, seasonally adjusted','HOUST':'thousands of units, seasonally adjusted annual rate',
 'PERMIT':'thousands of units, seasonally adjusted annual rate','DCPF1M':'percent','DCPN30':'percent','WTB3MS':'percent','^GSPC':'index points','SAHMREALTIME':'percentage points','INDPRO':'index, 2017=100, seasonally adjusted','DFEDTARU':'percent',
 'PAYEMS':'thousands of persons, seasonally adjusted','GDPC1':'billions of chained 2017 dollars, seasonally adjusted annual rate','GDPNOW':'percent change from the prior quarter, seasonally adjusted annual rate'}   # v3.73
# audit-0924 (24 Sep 2026): the period of each series' latest value, printed beside its units when it is not the row's
_WKY={'ICSA','CCSA','IURSA'}; _QTR={'GDPC1','GDPNOW'}
def _series_last_date(x_):
    try:
        if x_ in _WKY:
            q_=pd.read_csv(os.path.join(_D0,x_+'.csv')); ok_=pd.to_numeric(q_.iloc[:,1],errors='coerce').notna(); return pd.Timestamp(q_[ok_].iloc[-1,0])
        if x_ in ('UNRATE','AWHMAN','NDMANEMP','PAYEMS','GDPC1','GDPNOW','JTSJOL','CLF16OV','HOUST','PERMIT'):
            t_=pd.read_csv(os.path.join(_AL0,x_+'_all_vintages.csv'),index_col=0); v_=pd.to_numeric(t_[t_.columns[-1]],errors='coerce').dropna(); return pd.Timestamp(v_.index[-1])
    except Exception: return None
    return None
def _pkey(x_,d):
    d=pd.Timestamp(d)
    if x_ in _QTR: return '%d:Q%d'%(d.year,(d.month-1)//3+1)
    if x_ in _WKY: return 'week ending '+d.strftime('%b')+' '+str(d.day)+', '+str(d.year)
    return d.strftime('%b %Y')
def _period_note(x_,f_):
    d_=_series_last_date(x_)
    if d_ is None: return ''
    try: rk_=_pkey(x_,pd.Timestamp(str(f_.get('through'))[:10]))
    except Exception: rk_=None
    k_=_pkey(x_,d_)
    return '' if k_==rk_ else ', '+k_
_GT90={}   # the search terms as Google shows them: the past-90-days view (0-100), last complete day
try:
    for _tg in _TSRC:
        _gp=os.path.join(_ROOT,'108_high_frequency_speed_2026-09-10','google_trends','live',_tg+'_google90_daily.csv')
        if os.path.exists(_gp):
            _gd=pd.read_csv(_gp); _gd=_gd[~_gd['partial'].astype(bool)]
            if len(_gd): _GT90[_tg]=(str(_gd['date'].iloc[-1]),float(_gd['value'].iloc[-1]))
except Exception as _e: print('google 90-day view not read:',_e)
for _f in FEEDS:
    _f['values']=[]
    try:
        if _f['name'].startswith('State continued weeks'):   # v3.63: the breadth gate's share, and the month it reads
            _aob=(_AO_ST.get('reading') or {}); _f['value']='{:.0%}'.format(float(_aob['breadth_share']))
            _f['values']=[('ETA 539',_f['value'],'share of states with the insured-rate proxy 0.45 point over its twelve-month low, '+pd.Timestamp(str(_aob.get('breadth_month'))[:7]+'-01').strftime('%b %Y'))]; continue
        if _f['name'].startswith('State unemployment rates'):   # v3.72: the second opener's own breadth, on the states' first prints
            _f['value']='{:.0%}'.format(float(SB_ST['latest_share']))
            _f['values']=[('LAUS state rates (51)',_f['value'],'share of the 51 states whose own Sahm gap on first prints stands at or above 0.70, '+pd.Timestamp(str(SB_ST.get('through'))[:7]+'-01').strftime('%b %Y'))]; continue
        if _f['name'].startswith('State insured'):
            _f['value']='{:.1%}'.format(lastv(RAW['B'])[0]*p['bshare']); _f['values']=[('ETA 539',_f['value'],'share of states with the insured rate 0.20 point over its 52-week low')]; continue
        if _f['name'].startswith('Search week'):
            _tg=next((k_ for k_,v_ in _TSRC.items() if v_ in _f['name']),None)
            if _tg and _tg in _GT90:
                _f['value']='{:.0f}'.format(_GT90[_tg][1]); _f['through']=_GT90[_tg][0]
                _f['values']=[('Google Trends',_f['value'],'index, 0-100 over the past 90 days, the last complete day')]
            elif _tg: _f['value']='{:.1f}'.format(lastv(GT_TERMS[_tg][1])[0]); _f['values']=[('Google Trends',_f['value'],'index, the program\'s stitched scale')]
            continue
        _ids=[x_.strip() for x_ in (_f.get('ids') or '').split(',') if x_.strip() in _RAWF]
        if _ids:
            _f['values']=[(x_,_RAWF[x_][1].format(_RAWF[x_][0]()),_UNITS_FEED.get(x_,'')+_period_note(x_,_f)) for x_ in _ids]
            _f['value']='; '.join(v_ for _,v_,_ in _f['values'])
    except Exception as _e: print('feed value not set for',_f['name'][:30],':',_e)
# ---- v3.71c (22 September 2026, collection 310): a paper rate the Board has not printed since an earlier day carries that day, beside its value;
# ---- the row's 'in hand through' is the week the spread reads, and the Board prints n.a. for a maturity when too few trades settle.
for _f in FEEDS:
    if not _f['name'].startswith('Commercial paper'): continue
    try:
        _thr=pd.Timestamp(_f.get('through')); _nv=[]
        for x_,v_,u_ in _f.get('values') or []:
            _pp={'DCPF1M':os.path.join(_C25,'fred_daily','DCPF1M.csv'),'DCPN30':os.path.join(_C25,'fred_daily','DCPN30.csv')}.get(x_)
            if _pp:
                _q=pd.read_csv(_pp); _q=_q[pd.to_numeric(_q.iloc[:,1],errors='coerce').notna()]; _ld=pd.Timestamp(_q.iloc[-1,0])
                if _ld<_thr-pd.Timedelta(days=4): u_=u_+', last printed '+_ld.strftime('%b')+' '+str(_ld.day)+', '+str(_ld.year)
            _nv.append((x_,v_,u_))
        _f['values']=_nv
    except Exception as _e: print('paper rate days not set:',_e)
# the readings table carries the same next-release days (they are computed after the readings, so patched here);
# each row also says what kind of release moves it, so the page can roll the date forward by its own clock
for r in R:
    if r['next']=='JOLTS, next release': r['next']=next(n['date'] for n in NEXT if n['what'].startswith('JOLTS')); r['next_kind']='jolts'
    elif r['next']=='housing starts, next release': r['next']=next(n['date'] for n in NEXT if n['what'].startswith('Housing')); r['next_kind']='starts'
    elif r['next']=='daily': r['next_kind']='daily'
    elif r['next']=='H.15 week, next posting': r['next_kind']='h15'; r['next']=next((c['date'] for c in CAL if c['kind']=='h15'),r['next'])
    elif r['next']==first_fri(today): r['next_kind']='jobs'
    else: r['next_kind']='claims'
# the data inventory: each feed also carries the rule's own object, at the reading the readings table shows
_FOBJ=[('Initial claims','initial claims, 4-week mean above its base'),
       ('State insured','state breadth, share of states'),
       ('Unemployment rate, factory hours','Sahm gap (three-month average'),
       ('Job openings','vacancy rate, 4-month mean'),   # v3.71e (22 September 2026): the object's own words, not the bare word
       ('Housing starts','housing'),
       ('Commercial paper','paper'),
       ('S&P 500 daily close','sudden stop: S&P 500 below its high'),
       ('Search week: Google searches for "unemployment"','searches for "unemployment"'),
       ('Search week: Google searches for "layoffs"','searches for "layoffs"'),
       ('Search week: Google searches for "laid off"','searches for "laid off"'),
       ('Industrial production','activity opener: industrial production'),('Federal funds target','activity opener: the policy rate'),
       ('State continued weeks','activity opener: state breadth')]   # v3.63 (collection 289)
for _f in FEEDS:
    _key=next((o for n,o in _FOBJ if _f['name'].startswith(n)),None)
    if not _key: continue
    _row=next((r for r in R if _key in r['object']),None)
    if not _row: continue
    _f['object']=_row['object']; _f['object_reading']=round(float(_row['reading']),3); _f['object_line']=_row['line']
    if not _f.get('value'):
        _f['value']='{:.2f} of the line {} - {}'.format(_row['reading'],_row['line'],_row['object'][:80])

# ---- the announcements: when the rule spoke against when the committee did (peaks and troughs) ----
# THE SAHM COMPARATOR IS FRED'S OWN REAL-TIME SERIES (SAHMREALTIME, refreshed by bhs_update.py). Audit of 8 September
# 2026: the page had carried the rule's own Sahm object (the gap on first prints) under FRED's name; the two agree on
# every crossing of 0.50 inside a recession since 1960 but the rule's object also crosses in June 2003, FRED's does not.
_sf=pd.read_csv('cache/SAHMREALTIME.csv',index_col=0,parse_dates=True).iloc[:,0].dropna() if os.path.exists('cache/SAHMREALTIME.csv') else g.dropna()
SAHM=_sf[_sf.index>=SITE_START]
# v3.63 (collection 289): the 1950s announcement days, sourced (collections 187 and 247; the live walk chain had dated every
# pre-1961 turn to the first Business Conditions Digest, 1 October 1961). No 1950s trough day is sourced in hand; none is invented.
# v3.66 (22 September 2026, collection 295; Anthony: "if they didnt announce the four then dont put anything there"): the NBER's committee
# announced its first turn on 3 June 1980; the four (1948, 1953, 1957, 1960) were never announced - dated in research
# publications only - so they carry no announcement day at the peak or the trough, and the panel prints nothing for them.
_FOUR_P=('1948-11','1953-07','1957-08','1960-04'); _FOUR_T=('1949-10','1954-05','1958-04','1961-02')
for _k in _FOUR_P: ANN[_k]=None
for _k in _FOUR_T: TANN[_k]=None
_ANN_SRC={'1948-11':'Moore (1955), The Diffusion of Business Cycles: the first NBER publication carrying the date','1953-07':'Moore (1955), The Diffusion of Business Cycles: the first NBER publication carrying the date','1957-08':'Moore (1958), Measuring Recessions, JASA: the first NBER publication carrying the date'}
ANNS=[]
for e in epis:
    om=pd.Timestamp(e['open_month']+'-01'); hit=[i for i in range(13) if abs((om.year-PK[i].year)*12+om.month-PK[i].month)<=9]
    if not hit: continue
    i=hit[0]; pkm=PK[i].strftime('%Y-%m'); trm=TR[i].strftime('%Y-%m')
    pa=ANN.get(pkm); ta=TANN.get(trm)
    ANNS.append(dict(peak=pkm,trough=trm,peak_ann=pa,trough_ann=ta,rule_open=e['open_pub'],rule_close=e.get('close_pub'),rule_open_month=e['open_month'],rule_close_month=e.get('close_month'),close_basis=e.get('close_basis'),
                     source=('dated by the NBER, never announced' if pkm in _FOUR_P else ((_ANN_SRC.get(pkm) or ('committee' if PK[i]>=pd.Timestamp('1979-01-01') else 'Business Conditions Digest, first issue carrying the date')) if pa else 'not dated by the NBER'))))
PROV=bool(SERIES.index[-1]>pd.Timestamp(lastv(g_asof)[1]).replace(day=1))   # the last month is provisional until its employment report is out
# ---- the Sahm rule in real time, for the same rows: the first month at or above 0.50 in FRED's SAHMREALTIME, on its release day ----
SAHM_CALLS=[]; _armed=True
for m,v in _sf.items():
    if _armed and v>=0.5: SAHM_CALLS.append((_pu(m),m)); _armed=False
    elif not _armed and v<0.5: _armed=True
_used=set()
for a in ANNS:
    nb=a['source']!='not dated by the NBER'
    lo=(pd.Timestamp(a['peak']+'-01') if nb else pd.Timestamp(a['rule_open_month']+'-01'))-pd.DateOffset(months=6)
    hi=(pd.Timestamp(a['trough']+'-01') if nb else pd.Timestamp((a.get('rule_close_month') or a['rule_open_month'])+'-01'))+pd.DateOffset(months=3)
    hit=[(pub,m) for pub,m in SAHM_CALLS if lo<=m<=hi]
    a['sahm_peak']=hit[0][0].date().isoformat() if hit else None; a['sahm_month']=hit[0][1].strftime('%Y-%m') if hit else None
    for h in hit: _used.add(h[1])
SAHM_OTHER=[dict(pub=pub.date().isoformat(),month=m.strftime('%Y-%m')) for pub,m in SAHM_CALLS if m not in _used and m>=pd.Timestamp('1969-01-01')]
# ---- THE BRISTOW RULE OF PAPER 1 (Hall and Bristow 2026), for the trough panel (17 September 2026): a recession ends the
# ---- month the Sahm indicator peaks - the arg max over the crossing episode (months at or above 0.50) plus the twelve
# ---- months after it, on FRED's real-time series as the paper's replication code computes it (reproduce.py, bristow()).
# ---- The day that date became visible: the release of the first reading below that peak.
def _episodes_sahm(s,thr=0.5):
    out,cur=[],[]
    for d_,v_ in s.items():
        if v_>=thr: cur.append(d_)
        elif cur: out.append(cur); cur=[]
    if cur: out.append(cur)
    return out
for a in ANNS:
    a['bristow_end']=None; a['bristow_known']=None
    try:
        nb=a['source']!='not dated by the NBER'
        P_=pd.Timestamp(a['peak']+'-01') if nb else pd.Timestamp(a['rule_open_month']+'-01')
        T_=pd.Timestamp(a['trough']+'-01') if nb else pd.Timestamp((a.get('rule_close_month') or a['rule_open_month'])+'-01')
        e_=[x for x in _episodes_sahm(_sf) if x[0]>=P_-pd.DateOffset(months=1) and x[0]<=T_+pd.DateOffset(months=12)]
        if e_:
            w_=_sf[e_[0][0]:e_[0][-1]+pd.DateOffset(months=12)]; end_=w_.idxmax(); v_=float(w_.max())
            after_=_sf[_sf.index>end_]; low_=after_[after_<v_]
            if len(low_):
                a['bristow_end']=end_.strftime('%Y-%m'); a['bristow_known']=_pu(low_.index[0]).date().isoformat()
    except Exception as _e: print('bristow rule (Paper 1) for',a.get('trough'),'not computed:',_e)
print('Bristow Rule (Paper 1) ends:',[(a['trough'],a['bristow_end'],a['bristow_known']) for a in ANNS])


# ---- v3.59 (20 September 2026; Anthony: "remove the leg channels from the data section ... if they are no longer in use"):
# ---- the leg tier is retired (v3.57) and its channel inventory is gone from the state and the data page. The data page
# ---- lists the eleven series the rule reads, the front page's, and the backstop tier's (bhs_site.py).
LEG_FEEDS=[]; LEG_STATUS={}; _stale=[]

from zoneinfo import ZoneInfo as _ZI
state=dict(built=str(today),built_at=datetime.datetime.now(_ZI('America/New_York')).strftime('%Y-%m-%d %H:%M'),next_releases=NEXT,feeds=FEEDS,leg_feeds=LEG_FEEDS,leg_status=LEG_STATUS,leg_channels_stale=_stale,calendar=CAL,calendar_dated_through=(_dated_through.isoformat() if _dated_through else None),announcements=ANNS,sahm_other=SAHM_OTHER,sahm=dict(dates=[t.strftime('%Y-%m') for t in SAHM.index],values=[round(float(v),3) for v in SAHM.values]),version=VERSION,walk=WALK,notes=dict(vacancy='job openings (JOLTS, over the labor force; the vintages exist from July 2010)',vintage='every monthly object - the unemployment rate, housing starts, factory hours, nondurable employment, job openings - is read for each month from the series as it stood on the day that month first appeared; weekly claims from the Department of Labor advance figures; the paper and bill rates and the S&P 500 are never revised',objects_added=('the starts x vacancy pair (a confirmer of the weak proposers), the sudden stop (one week of claims over its base with the S&P 500 under its 20-day high the same week), the paper spread on the wider of the financial and nonfinancial paper markets'+(' ; from v3.27 the sudden stop also reads the search week - the 7-day mean of Google searches for unemployment over the same base, known the next morning, with the S&P 500 at that day\'s close - and fires on the earlier of the claims week and the search week (the series exists from 2004 and enters there)' if 'GT_REL' in globals() else '')+(' ; from v3.29 the search week reads three labour terms - unemployment, layoffs, laid off - each over its own base, and fires on the earliest' if 'GT_TERMS' in globals() and len(GT_TERMS)>1 else '')+(' ; the housing x rate pair is confirmed by starts or by building permits at the starts line (permits as they stood on the day: ALFRED vintages from August 1999, the Economic Indicators tables as printed for 1969 and 1990, the current file elsewhere as a declared bound)' if 'mkpair_either_asof' in globals() else '')),arithmetic='every one-decimal object is read in exact tenths; a reading equal to its line is at the line',cosigner=('a proposal by the insured unemployment rate or by initial claims within 0.2 point (15 points for claims) above its line fires only if the three-month average unemployment rate, as last published, stands at least 0.2 point above its twelve-month low' if COS else None),lines_fixed=bool(COS),claims_base=('the four-week mean of initial claims is measured from the higher of its 52-week low and 85 percent of its trailing five-year median, as published' if 'ALPHA' in globals() else None)),lines={k:(None if v is None else v) for k,v in p.items()},standing=standing,carried_legs=[dict(letter=r['letter'],channel=r['channel'],mechanism=r['mechanism'],config='%s h%s q%s/%sy/h%s x %s h%s q%s ch%s'%(r['direction'],r['p_horizon'],r['p_q'],r['p_win'],r['p_hold'],r['confirmer'],r['c_hold'],r['c_q'],r['c_horizon']),screen_peaks=r['screen_peaks'],record_unchanged=(r['carried']=='True'),proposals=r['proposals']) for r in CARRY_TABLE if r['channel'] not in CARRY_EXCLUDED],carried_excluded=CARRY_EXCLUDED,pending_proposals=[dict(published=a,dated=b,leg=L,lapses=(pd.Timestamp(a)+pd.Timedelta(days=400)).date().isoformat()) for a,b,L in PENDING_NOW],realtime_note='v3.57 (20 September 2026): the rule has no leg tier. The alarm is the core\'s own call - the insured-rate, claims, survey-week and breadth proposers confirmed by vacancies, hours, starts, the paper-bill spread or the market - and the record shown is the record the site would have shown on the day: 1969 -35, 1973 -60, 1980 -35, 1981 -64, 1990 -76, 2001 -2, 2007 -7, 2020 +12, 2024 +3 days to the end of the peak month, zero false alarms. The leg tier (v3.46-v3.56) back-dated calls to leg proposals the core later confirmed; those dates were not real-time alarms and are retired with it (collection 260).',
           opening=dict(dates=[t.strftime('%Y-%m') for t in OPEN.index],values=[round(float(v),3) for v in OPEN['indicator']],branch=list(OPEN['branch'])),
           closing=dict(dates=[t.strftime('%Y-%m-%d') for t in CLOSE.index[CLOSE.index>=pd.Timestamp('1967-01-01')]],values=[None if np.isnan(v) else round(float(v),3) for v in CLOSE[CLOSE.index>=pd.Timestamp('1967-01-01')]]),
           frozen_episodes=[dict(open=a.date().isoformat(),close=(None if b.year==2100 else b.date().isoformat())) for a,b in FROZEN],
           nber=[dict(peak=pk.strftime('%Y-%m'),trough=tr.strftime('%Y-%m')) for pk,tr in zip(PK,TR)],
           chronology=epis,episodes=EP,series=dict(frequency='Daily, on release days',dates=[t.strftime('%Y-%m-%d') for t in SERIES_D.index],values=[round(float(v),3) for v in SERIES_D['value']],damage=[(None if (x is None or (isinstance(x,float) and not np.isfinite(x))) else x) for x in SERIES_D['damage']],reading=[round(float(v),3) for v in SERIES_D['reading']],phase=list(SERIES_D['phase']),branch=list(SERIES_D['branch']),provisional=False),series_monthly=dict(dates=[t.strftime('%Y-%m') for t in SERIES.index],values=[round(float(v),3) for v in SERIES['value']],reading=[round(float(v),3) for v in SERIES['reading']],phase=list(SERIES['phase']),branch=list(SERIES['branch'])),readings=R,
           through=dict(claims=lastv(ICfp)[1],insured_rate=lastv(spl)[1],unemployment_rate=lastv(g_asof)[1],vacancy=lastv(G)[1],sp500=lastv(_SPX)[1],spread=lastv(cS)[1],search=(lastv(GT_REL)[1] if 'GT_REL' in globals() else None),search_terms=({k:lastv(v[2])[1] for k,v in GT_TERMS.items()} if 'GT_TERMS' in globals() else None)))
# NaN IS NOT JSON. Python writes it happily and reads it back happily, so nothing on this Mac ever noticed, but
# JSON.parse and every strict parser reject it: on 18 September the published state file carried 9,521 NaNs in
# series.damage and the off-Mac watchdog could not read a single field of it. Anyone opening the file in a browser
# or replicating from it hit the same wall. Non-finite numbers are written as null, which is valid and means the
# same thing, and allow_nan=False then refuses to write the file at all if one ever survives the scrub.
def _json_safe(o):
    if isinstance(o,float): return None if not np.isfinite(o) else o
    if isinstance(o,dict): return {k:_json_safe(v) for k,v in o.items()}
    if isinstance(o,(list,tuple)): return [_json_safe(v) for v in o]
    return o
state=_json_safe(state)
state['backstop_opener']=dict(gate_weeks=13,collection='256_backstop_opener_replay_2026-09-20',calls=[(a.date().isoformat(),b.strftime('%Y-%m')) for a,b in _BS_CALLS][-12:],events=[(e[0].date().isoformat(),e[1],e[3]) for e in BS_EVENTS],
    note='The backstop tier (SOS_NSA, LMSI-30, CFNAI-MA3; the publishers\' own lines) may open an episode when the walked rule stands closed, once its union has been ON for thirteen consecutive weeks (one quarter). Replayed causally over 1956-2026 it changes nothing and false-alarms never (collection 256); the plain, ungated opener was refused there. It is insurance against a recession the core misses. An episode it opens is tagged b.')
state['leg_tier']='retired (v3.57, 20 September 2026, collection 260): the rule calls with its core alone; the gated backstop opener (256) stays'
state['diary_continued']=[(e[0].date().isoformat(),e[1],e[3]) for e in NEW_EVENTS]
# ---- v3.60 (21 September 2026, collection 278): CORE V6 - the labour core with the activity opener; E5 channel-dark rules ----
# ---- v3.63 (21 September 2026, collection 289): CORE V7-W - the labour core (E13t) with the activity opener's walked cell and breadth gate ----
state['activity_opener']=_json_safe(dict(collection='289_core_v7w_live_port_2026-09-21',rule=_AO_ST.get('rule'),lines=_AO_ST.get('lines'),reading=_AO_ST.get('reading'),
    next_production_release=_ao_next(),next_fomc=_AO_ST.get('next_fomc'),next_breadth_publication=_AO_ST.get('next_breadth_publication'),
    channels=_AO_ST.get('channels'),walked_calls=_AO_ST.get('walked_calls'),notes=_AO_ST.get('notes'),
    calls_at_todays_lines=[(a.date().isoformat(),b.strftime('%Y-%m')) for a,b in _AO_CALLS],
    events=[(e[0].date().isoformat(),e[1],e[3]) for e in AO_EVENTS],
    note='Core v7-W (v3.63): the activity opener fires when industrial production as published is at least 2 log points below its high of the prior twelve months, the S&P 500 at least 10 per cent below its high of the prior 250 trading days, the policy rate at least 0.10 point above its low of the prior 365 days, and at least a third of the states have their insured-rate proxy 0.45 point above its twelve-month low in the latest month public (21 days after it ends). It opens only what the labour core has not seen (leg P, on the backstop opener\'s bars: never inside an open episode, never within 183 days of a close). The cell and the gate are the causal walk\'s from 1948 (collection 288: learning only from recessions already dated at each cut - 1920, 1923, 1926, 1929 and 1937 first). Walked with the labour core (E13t), the tool calls 13 of 13 recessions, 12 inside three months before to one month after the end of the peak month (1960 +122 days the residual; from v3.68 the concurrence branch calls 1960 at -5 and all 13 are inside), with no false alarm on either chronology; the opener\'s own walked calls are 1948-09-27, 1953-08-31 and 1957-08-26, and three inside recessions the core had already opened. Disclosed: the breadth month must be public within about 21 days (at 35 or 45 days the walk false-alarms in October 1956); the gate\'s 1956 margin is about three states, and on the lab\'s other historical claims panel the October 1956 firing passes the gate; the live breadth object is built from the Department\'s weekly ETA 539 file (collection 289, T4: the walk is unchanged when it replaces the walked object from 1985).'))
state['core']='v7-W: the labour core (walk 97 lines; E13t; walked from 1956) + the activity opener (production, market, tightening and the state-breadth gate; walked from 1948; leg P) + the gated backstop opener (leg b)'
state['walked_record']=dict(first_cut=1948,core_first_cut='1949-07-12',retrospective_closes=pg.get('retro_closes'),opener_walked_calls=pg.get('walked_opener_calls'),
    note=pg.get('note'),collections='288 (the walk), 289 (the port)')
# ---- v3.68 (22 September 2026, collections 300 and 301): THE CONCURRENCE BRANCH in the state ----
_cbw=pg.get('concurrence_branch') or {}
state['concurrence_branch']=_json_safe(dict(collection='300_the_four_round2_2026-09-21 (A2); port 301_the_four_round3_2026-09-22',
    line=0.010,rule=_cbw.get('rule'),walked_line_by_cut=_cbw.get('walked'),walked_diary=_cbw.get('diary'),status=_CB_NOTE,
    calls_at_todays_lines=[(a.date().isoformat(),b.strftime('%Y-%m')) for a,b in _CB_CALLS][-12:],
    proposers_of_those_calls=[(d.date().isoformat(),m.strftime('%Y-%m'),w) for d,m,w in _CB_ALL][-12:],
    events=[(e[0].date().isoformat(),e[1],e[3]) for e in CB_EVENTS],activity_picture=_AO_ST.get('activity_picture'),
    note=('The labour side and the activity side read together: a labour proposal (the insured unemployment rate, the survey-week rate, '
          'initial claims or state breadth over its line) that still stands is confirmed on the first day, up to four months after its '
          'month, on which the activity picture holds - industrial production as published 1.0 log point below its twelve-month high, '
          'the S&P 500 10 per cent below its 250-day high, the policy rate 0.10 above its 365-day low and a third of the states 0.45 over '
          'their twelve-month low. Walked from 12 July 1949 on official-recognition knowledge dates (v3.70; from 1956 in v3.68; the production line chosen at every cut from none, 0.015 and 0.010: 0.010 every '
          'time); every walked call is inside a recession; it opens 1960 on 25 April 1960, five days before the end of the peak month '
          '(was 30 August, +122). Held out one recession at a time, the walk is unchanged (collection 300).')))
# ---- v3.72 (22 September 2026, collection 311; E31): the state breadth in the state ----
state['state_breadth']=_json_safe(dict(collection='311_second_route_2024_type_call_2026-09-22 (E31); data 312 and 313',
    gap_line=(SB_ST.get('cell') or {}).get('gap'),share_line=(SB_ST.get('cell') or {}).get('share'),rearm_line=(SB_ST.get('cell') or {}).get('rearm'),   # rearm_line: v3.73 (E31b)
    states=SB_ST.get('states'),through=SB_ST.get('through'),published=SB_ST.get('published'),
    latest_share=SB_ST.get('latest_share'),next_release=SB_ST.get('next_release'),substitute=SB_ST.get('substitute'),   # substitute: collection 336, the state-rate bridge
    fires=(SB_ST.get('fires') or []),fires_with_vacancies=[(str(d.date()),m.strftime('%Y-%m'),round(sh,3)) for d,m,sh in SB_OPENER],
    stood_down=SB_BLOCKED,events=[(e[0].date().isoformat(),e[1],e[3]) for e in SB_EVENTS],
    note=('The second opener. The share of states whose own Sahm gap - the three-month average of the state unemployment rate '
          'above its twelve-month low, each month as first printed - stands at or above 0.70; when at least 40 per cent of the '
          'states are there, and the vacancy gap stood at its line in two of the prior months, and the rule has stood closed for '
          'a quarter, it opens a recession. On the states own first prints back to March 1994 it fired four times: inside the 2001 '
          'recession, inside 2007-09, once thirty-three days after the 2020 close (the quarter rule stood it down) and on 17 May '
          '2024, inside the window. It changes no call or close on this record - the labour core called 2024 on 3 May, earlier - '
          'and it is here so that a 2024-type recession has a second route (collections 311, 312, 313).')))
def _ch_age(x,monthly=False):
    # days from the END of the period the latest reading covers to today. A monthly series is dated by its reference
    # month, which the state writes as the month's first day ('2026-08-01' is August): it is aged from the month's last
    # day, never from its first (21 September 2026: aged from the first, the August jobs report read 51 days old)
    try:
        x=str(x); d=pd.Timestamp(x[:7]+'-01')+pd.offsets.MonthEnd(0) if (monthly or len(x)==7) else pd.Timestamp(x[:10])
        return (pd.Timestamp(today)-d).days
    except Exception: return None
_th=state.get('through') or {}
# (channel, latest reading, limit in days, substitute, monthly). Each limit is the longest a reading can be before the
# next one is due on the publisher's own calendar, plus a day or two: claims 12 (13 on a holiday week), the insured
# rate a week more, the jobs report 41 (a December report on 10 January), JOLTS about 71, the H.15 week 10 (11 after a
# Monday holiday), the close 4 over a long weekend, G.17 about 35. Past the limit a channel is stale; past twice, dark.
_CH=[('initial and continued claims, insured unemployment rate (DOL weekly)',_th.get('claims'),13,'the states\' own ETA 539 weekly claims (published through federal shutdowns)',False),
     ('insured unemployment rate as the proposers read it',_th.get('insured_rate'),20,'the states\' ETA 539 insured rates',False),
     ('unemployment rate, factory hours, nondurable jobs (BLS Employment Situation)',_th.get('unemployment_rate'),45,'the Chicago Fed real-time unemployment forecast; ADP private payrolls (LSEG first prints)',True),
     ('job openings (BLS JOLTS)',_th.get('vacancy'),80,'the Indeed Hiring Lab postings index',True),
     ('paper and bill rates (Federal Reserve H.15)',_th.get('spread'),12,'FRED DCPN30, DCPF1M and DTB3 (the Federal Reserve is not shut in a shutdown)',False),
     ('S&P 500 close',_th.get('sp500'),5,'the official FRED SP500 close',False),
     ('industrial production as published (Federal Reserve G.17)',(_AO_ST.get('reading') or {}).get('production_vintage'),45,'the FRED current file of INDPRO (flagged: revised values)',False),
     ('the policy rate (FOMC target range, FRED DFEDTARU)',(_AO_ST.get('reading') or {}).get('policy_date'),10,'the FOMC statement on federalreserve.gov (the rate carried from the last reading until then)',False),
     ('state breadth (ETA 539 continued weeks by state, over payrolls)',(_AO_ST.get('reading') or {}).get('breadth_month'),56,'the ETA 5159 monthly report (slower), then the last month read',True),   # v3.63
     ('state unemployment rates, all 51 (BLS LAUS first prints; the second opener)',(SB_ST.get('through') or '')[:7] or None,56,'the states\' ETA 539 insured-rate acceleration, the share over 0.60 for the Sahm-gap share over 0.40 (collection 336; at most two months)',True)]   # collection 336
state['channels']=[]
for _n,_l,_lim,_s,_mo in _CH:
    _a=_ch_age(_l,_mo) if _l else None
    _st='dark' if _a is None or _a>2*_lim else ('stale' if _a>_lim else 'current')
    _row=dict(channel=_n,last=_l,age_days=_a,limit_days=_lim,status=_st,substitute=_s if _st!='current' else None)
    if _n.startswith('initial and continued claims') and CLAIMS_SUB.get('active'):   # collection 329: the substitute is reading
        _row.update(status='substitute',substitute=_s,substitute_weeks=CLAIMS_SUB.get('substitute_weeks'),release_through=CLAIMS_SUB.get('last_release_week'),drill=CLAIMS_SUB.get('drill'))
    if _n.startswith('job openings') and VAC_BRIDGE.get('active'):   # v3.73 (collection 330): the Indeed bridge is carrying the object
        _row.update(status='substitute',substitute=_s,substitute_months=VAC_BRIDGE.get('months'),drill=VAC_BRIDGE.get('drill'),indeed_through=VAC_BRIDGE.get('indeed_through'))
    if _n.startswith('job openings') and VAC_BRIDGE.get('dark'): _row.update(status='dark',note=VAC_BRIDGE.get('note'))
    if _n.startswith('state unemployment rates'):   # collection 336: the state-rate bridge
        _sbs=(SB_ST.get('substitute') or {})
        if _sbs.get('months'): _row.update(status='substitute',substitute=_s,substitute_months=_sbs.get('months'),drill=_sbs.get('drill'))
        elif 'reads dark' in str(_sbs.get('note','')): _row.update(status='dark',note=_sbs.get('note'))
    state['channels'].append(_row)
state['claims_substitute']=CLAIMS_SUB
state['first_prints']=FIRSTPRINTS   # E66
state['vacancy_bridge']=_json_safe(VAC_BRIDGE)   # v3.73
state['near_misses']=dict(line=0.80,spells=NEAR_MISSES,note='spells outside an episode with the index at or above 0.80: the margin-to-line monitor (plan item 18); evidence, nothing moves')   # collection 335
if REV_DRILL.get('active'): state['revision_drill']=_json_safe({k:v for k,v in REV_DRILL.items() if k!='paths'})   # collection 334: a drill build says so
if BADPRINT.get('active'): state['bad_print_drill']=_json_safe({k:v for k,v in BADPRINT.items() if k!='file'})   # collection 378: a drilled build says so
state['payroll_backstop']=_json_safe(dict(collection='323_payroll_backstop_closer_e38_2026-09-22',rule='three consecutive payroll gains in one vintage and the three-month unemployment rate 0.3 under its high since the open, on the employment situation release day, ninety days into an episode no other closer has closed',**PB_ST))
state['damage']=_json_safe(dict(form='three dimensions (v3.73, collection 327): the mean of labour (unemployment depth x point-months), output (real GDP peak-to-trough x cumulative loss) and production (industrial production, the same), each the log of the geometric mean with 1929-33 at 10',anchors=_DIM_ANCH,status=_DIM_NOTE,consensus='196: 75 of 78 pairs ordered as the six-measure consensus, Spearman 0.978'))
state['chronology_watch']=dict(lesson_pending=os.path.exists(os.path.join('chronology','lesson_pending.json')),pending=(json.load(open(os.path.join('chronology','lesson_pending.json'))) if os.path.exists(os.path.join('chronology','lesson_pending.json')) else None),entries=(len((json.load(open(os.path.join('chronology','announcements.json'))) or {}).get('recessions') or []) if os.path.exists(os.path.join('chronology','announcements.json')) else 0))
state['realtime_note']=(state.get('realtime_note') or '')+' v3.73 (23 September 2026, collection 333): the damage grade in three dimensions - labour (unemployment depth x point-months), output (real GDP peak-to-trough x cumulative loss inside the episode; GDPNow for the unprinted quarter) and production (industrial production, the same) - each on the logarithmic scale with 1929-33 at 10 and averaged, which orders 75 of 78 pairs of the thirteen episodes as the ex-post consensus does; the payroll backstop closer (three payroll gains and the unemployment rate turned down 0.3, ninety days into a recession no other closer has ended - never first on the record); the state breadth re-arms only below 0.25 (E31b); the claims and the vacancy channels carry their own substitutes through a dark release (the states\' ETA 539 file; the Indeed postings index for at most two JOLTS months); the committee watch reads the NBER\'s announcements and raises a flag for a dating lesson.'
state['realtime_note']=(state.get('realtime_note') or '')+' v3.62 (21 September 2026): Core v6 - the activity opener (industrial production as published 2.5 log points below its twelve-month high with the S&P 500 20 per cent below its 250-day high, the lines a causal walk from 1948 chose) may open a recession the labour core has not yet seen; since 1948 it has not fired outside a recession, and since 1956 never before the labour core, so it changes no call on this record.'
state['realtime_note']=state['realtime_note']+' v3.63 (21 September 2026): Core v7-W - the record shown begins in 1948 and is walked throughout: the activity opener (production, market, the policy rate and a state-breadth gate, the cell a causal walk from 1948 chose) calls 1948 (27 September 1948, 64 days before the end of the peak month), 1953 (31 August 1953, +31) and 1957 (26 August 1957, -5); the labour core, walkable from 1956, calls the rest as before (1960 +122). Thirteen of thirteen, twelve inside the window, no false alarm. The closes of 1950-03-09 and 1954-06-03 are retrospective (the core\'s first walked configuration, January 1956).'
# ---- v3.64 (21 September 2026, collection 291; Anthony: "WHY DO WE HAVE LEGS?! ... DO NOT USE LEGS IF THEY DATE RETROSPECTIVELY.
# ---- ADD THE THINGS TO THE ACTUAL CORE"). The leg tier that back-dated calls was retired in v3.57; its empty keys leave the
# ---- state here, and every part of the rule is named as a branch of one core. No branch dates retrospectively: every call and
# ---- every close is dated to its own day (the activity closer, collection 291, replaced the last two borrowed closes).
_BRANCH={'U':'labour core: insured unemployment rate','L':'labour core: insured unemployment rate','W':'labour core: survey-week insured rate',
         'V':'labour core: survey-week insured rate','I':'labour core: initial claims','B':'labour core: state breadth',
         'X':'labour core: Sahm gap with falling vacancies','K':'labour core: sudden stop','C':'labour core: closer','H':'labour core: closer',
         'J':'labour core: closer','P':'activity opener','A':'activity closer','b':'backstop','Y':'concurrence branch: a labour proposal with the activity picture','N':'state breadth: the states\' own Sahm gaps','E':'labour core: payroll backstop closer'}   # Y: v3.68; N: v3.72; E: v3.73
def _br(x): return _BRANCH.get(x,x) if x else None
_CLOSERS=('C','H','J','K','R','T','Q','S','E')   # E: v3.73, the payroll backstop closer   # v3.68b (22 September 2026, collection 301): a close by the letter K is the continued-claims closer, not the sudden stop
def _brk(kind,x): return 'labour core: closer' if (kind in ('CLOSE','closed') and x in _CLOSERS) else _br(x)
for _x in (state.get('near_misses') or {}).get('spells') or []: _x['branch']=_br(_x.get('branch'))   # collection 335: the near-miss spells name their branch
for _k in ('leg_feeds','leg_status','leg_channels_stale','carried_legs','carried_excluded','leg_tier','pending_proposals'): state.pop(_k,None)
for _k in ('newlegs','warnw','warnp','extra','carry'): (state.get('lines') or {}).pop(_k,None)
for _lst in (state.get('episodes') or [], state.get('chronology') or []):
    for _e in _lst:
        if 'open_leg' in _e: _e['open_branch']=_br(_e.pop('open_leg'))
        if 'close_leg' in _e: _e['close_branch']=_brk('CLOSE',_e.pop('close_leg'))
_s=state.get('standing') or {}
if 'leg' in _s: _s['branch']=_brk(_s.get('state'),_s.pop('leg'))
for _key in ('diary_continued',):
    if state.get(_key): state[_key]=[(a,b,_brk(b,c)) for a,b,c in state[_key]]
for _key in ('activity_opener','backstop_opener','concurrence_branch'):
    if isinstance(state.get(_key),dict) and state[_key].get('events'): state[_key]['events']=[(a,b,_brk(b,c)) for a,b,c in state[_key]['events']]
if isinstance(state.get('activity_opener'),dict) and state['activity_opener'].get('note'):
    state['activity_opener']['note']=state['activity_opener']['note'].replace("(leg P, on the backstop opener's bars:","(on the backstop's bars:")
if isinstance(state.get('backstop_opener'),dict) and state['backstop_opener'].get('note'):
    state['backstop_opener']['note']=state['backstop_opener']['note'].replace(' An episode it opens is tagged b.',' An episode it opens is marked as the backstop\'s.')
state['core']=('v7-W: one rule, one core. Its branches: the labour core (the insured unemployment rate, the survey-week insured rate, initial claims, '
               'state breadth, the Sahm gap with falling vacancies, the sudden stop - each confirmed by vacancies, hours, housing, the paper spread '
               'or the market - and the labour closer); the activity opener and the activity closer (walked from 1948 on the pre-war recessions); '
               'the concurrence branch (a labour proposal still standing, confirmed on a day the activity picture holds; walked from 1949; v3.68, v3.70); the labour closer\'s fourth confirmation, the strong flow (v3.71); the state breadth, the second opener (v3.72); and the backstop')
state['realtime_note']=('v3.71 (22 September 2026, collection 310; E29, the best version, with collections 304 and 309; Anthony: "update the site with version E29 on it"): the rule ends 1948-49 on 28 October 1949 (-3 days; was +87) by the activity closer, which now also waits for factory employment, as published, to turn up; 1957-58 on 23 May 1958 (+23; was +51) by the claims closer with a fourth confirmation, a strong and lasting fall in initial claims with the S&P 500 10 per cent above its low; 1960-61 on 30 January 1961 (-29; was +66) and 1973-75 on 1 May 1975 (+31; was +38); and it calls 1973 on 17 September 1973 (-74; was -60). All thirteen calls fall within three months before to one month after the end of the peak month and all thirteen closes within a month either side of the end of the trough month, with no false alarm on the NBER and Paper 1. Today\'s lines move in two places, the vacancy line (0.25, was 0.20) and the vacancy look-back (12 months, was 9). The walked diary is w7w5.')   # v3.71 (22 September 2026, collection 310)
# ---- v3.65 (21 September 2026, collection 291; Anthony: "I dont want things that are from the frozen rule displayed on the
# ---- website"): the frozen backcast's episodes and the two series read against them leave the published state (no page
# ---- reads them); the walk the site stands on is named. The frozen run at today's lines still continues the diary.
for _k in ('frozen_episodes','opening','closing'): state.pop(_k,None)
state['walk']=('Core v7-W, walked from 1948: the activity opener and the activity closer (collections 288 and 291) and the '
               'labour core under E13t (276 p2thin; the code is walk97.py), ported in 289 and 291; with the concurrence branch '
               'and the continued-claims closer on the extended claims (collection 300, walk p3k18), ported in 301 (v3.68); on '
               'official-recognition knowledge dates, the labour core and the branch walked from 12 July 1949 and the breadth gate from 29 '
               'January 1954, with the weekly claims of 1957-61 on their documented release days and K dated by its release (collection '
               '303, walk e19a; v3.70); the state breadth as a second opener (E31, collections 311-313; v3.72); E29, the best version: E22cb\'s ties on closes and robustness (collection 304), the activity closer\'s jobs '
               'condition (E26, collection 309), the tie in C\'s drop at the centre and C\'s strong-flow confirmation (E28, E29, collection 310; walk e29; v3.71)')
_wr=state.get('walked_record') or {}
_wr['collections']='288 (the walk), 289 (the port), 291 (the walked closer), 292 (legs to core: tested, nothing added), 300 (the concurrence branch; K on the extended claims), 301 (the port, v3.68), 303 (official-recognition knowledge dates; the documented claims calendar; the port, v3.70), 304 (round 5: ties on closes and robustness, E22cb), 309 (the activity closer\'s jobs condition, E26), 310 (the tie in C\'s drop and the strong flow, E28 and E29; the port, v3.71), 311 (the second route to a 2024-type call: E31), 312 and 313 (the states\' first prints, 1994-2026; the port, v3.72)'
state['walked_record']=_wr
# ---- R10 (24 September 2026, collection 372): the state's schema version, stamped and checked before the state is written; a port that
# ---- drops a key the page or the ops readers need stops here, with the list, not on the reader's screen. s2/schema.py is the one place.
import importlib.util as _iu372; _sp372=_iu372.spec_from_file_location('bhs_schema',os.path.join('s2','schema.py')); _schema372=_iu372.module_from_spec(_sp372); _sp372.loader.exec_module(_schema372)
_schema372.stamp(state); _pr372=_schema372.check(state)
if _pr372: raise SystemExit('R10: the state is not schema %d as this build defines it: %s'%(_schema372.SCHEMA_VERSION,'; '.join(_pr372)))
json.dump(state,open(os.path.join(LIVE,'bhs_state.json'),'w'),allow_nan=False)
json.dump(state,open('out/bhs_state.json','w'),allow_nan=False)
_tick('state written')
print('opening',OPEN.index.min().strftime('%Y-%m'),'->',OPEN.index.max().strftime('%Y-%m'),len(OPEN),'months; >=1 in',(OPEN['indicator']>=1).sum())
print('frozen episodes',[(a.date().isoformat(),b.date().isoformat()) for a,b in FROZEN])
print('latest twelve:',', '.join(f"{t:%Y-%m} {v:.2f}{b}" for t,v,b in zip(OPEN.index[-12:],OPEN['indicator'][-12:],OPEN['branch'][-12:])))
print('closing latest:',', '.join(f"{t:%m-%d} {v:.2f}" for t,v in CLOSE.tail(6).items()))
print('standing',standing); print('episodes',len(epis),'site episodes',len(EP))
print('series latest:',', '.join(f"{t:%Y-%m} {v:.2f}{p}" for t,v,p in zip(SERIES.index[-6:],SERIES['value'][-6:],SERIES['phase'][-6:])))
print('daily series:',len(SERIES_D),'release days',SERIES_D.index[0].date(),'->',SERIES_D.index[-1].date(),'| latest:',', '.join(f"{t:%Y-%m-%d} {v:.2f}{p}" for t,v,p in zip(SERIES_D.index[-6:],SERIES_D['value'][-6:],SERIES_D['phase'][-6:])))
print('daily >=1 days',int((SERIES_D['value']>=1).sum()),'held 0.99:',[t.strftime('%Y-%m-%d') for t,v in SERIES_D['value'].items() if v==0.99][:12],'held 1.00:',[t.strftime('%Y-%m-%d') for t,v,r in zip(SERIES_D.index,SERIES_D['value'],SERIES_D['reading']) if v==1.0 and r<1][:12])
for r in R: print(f"{r['side']:8s} {r['object'][:70]:70s} {r['reading']:9.3f} / {r['line']}  through {r['through']}")
print('sahm rule, real time:',[(a['peak'],a['sahm_peak']) for a in ANNS],'| other crossings since 1969:',SAHM_OTHER)
