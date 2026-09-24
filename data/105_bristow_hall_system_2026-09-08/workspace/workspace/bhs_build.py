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
          os.path.join(_R,'37_*','*.csv'),'cache/objects.pkl','cache/alfred_first_*.csv','cache/relcal_*.csv','cache/surveys/*.csv','cache/SAHMREALTIME.csv']
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
with contextlib.redirect_stdout(io.StringIO()): exec(src)
open=_bhs_real_open
print('closers memo: %d hit, %d recomputed, %d passed, %d unkeyed (fingerprint %s)'%(_BHS_MEMO_STATS['hit'],_BHS_MEMO_STATS['miss'],_BHS_MEMO_STATS['passed'],_BHS_MEMO_STATS.get('unkeyed',0),_BHS_FP[:8])+('; recomputed: '+'; '.join(_BHS_MEMO_STATS.get('missed',[])[:8]) if _BHS_MEMO_STATS['miss'] else '')+('; UNKEYED: '+'; '.join(sorted(_BHS_MEMO_STATS['unkeyed_names'])) if _BHS_MEMO_STATS.get('unkeyed') else ''))
_tick('exec walk94 head')
out.close()
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
    return t+''.join(_walk_chain(m,seen) for m in _re.findall(r"exec\(open\('(walk\w+\.py)'\)",t))
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
PENDING_NOW = sorted({(a.date().isoformat(), b.strftime('%Y-%m'), L) for a, b, L in PENDING if (pd.Timestamp(today) - a).days <= 400})
print('pending leg proposals (passed the record bar, core not yet confirmed, inside 400 days):', PENDING_NOW)
FROZEN=[]; _cur=None
for x in _t:
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
conf=np.maximum.reduce([sp_/S_,fc_/3.0,du_/3.0])
cs=np.minimum.reduce([_FI['drop'].values/D_,_FI['run'].values/3.0,_FI['amp'].values/20.0,conf])
CLOSE=pd.Series(cs,index=_CW).clip(lower=0); CLOSE_RAW=CLOSE.copy()
# read only while the frozen rule has an episode open (a close cannot be proposed when nothing is open)
CLOSE=pd.Series([v if any(a<=t<=b for a,b in FROZEN) else np.nan for t,v in CLOSE.items()],index=CLOSE.index)
# ---- the chronology from the causal walk ----
pg=pickle.load(open(f'cache/{VAR}_prog.pkl','rb')); LOG=sorted(pg['log'],key=lambda z:z[0])
epis=[]; cur=None
for pub,kind,dt,leg in LOG:
    if kind=='OPEN': cur={'open_pub':pub.date().isoformat(),'open_month':dt.strftime('%Y-%m'),'open_leg':leg}
    elif cur is not None: cur.update(close_pub=pub.date().isoformat(),close_month=dt.strftime('%Y-%m'),close_leg=leg); epis.append(cur); cur=None
if cur is not None: epis.append(cur)
# the reading must carry the clauses the diary was walked with: an X open on 3 May 2024 exists only under the majority hold
if any(e['open_pub']=='2024-05-03' and e['open_leg']=='X' for e in epis) and not HUB_MAJ: raise SystemExit('bhs_build: the diary opens 3 May 2024 by X (the majority hold) but HUB_MAJ is None - the walk chain was not read')
last=LOG[-1]; standing={'state':'open' if last[1]=='OPEN' else 'closed','since':last[0].date().isoformat(),'dated':last[2].strftime('%Y-%m'),'leg':last[3]}
# ---- THE ONE LINE (the site's series). Recessions dated by the rule: the causal diary from 1962, and before 1962 the
# rule at its final lines (the walk begins in 1962). Outside a recession the line is the rule's reading with the
# branches' arming - the distance to the next opening call - held below 1.00 (at most 0.99) where the frozen rule did
# not speak; from the month the rule opened through the month it closed it is the reading without arming, held at
# least at 1.00 (the rule has the recession open); it drops below 1.00 the month after the close. Nothing is smoothed
# and nothing is capped: the crossings are the rule's own calls and the heights are its readings.
# THE PAGE BEGINS IN JANUARY 1962: the first January at which the rule's lines were chosen from the past alone. The
# recessions before 1962 were used to choose them and are not shown (Anthony's ruling, 8 September 2026).
SITE_START=pd.Timestamp('1962-01-01')
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
    _DMG_CUM[_a]=(base,B,pd.Series(dict(rows)).sort_index(),cum,depth)
# the damage data, rewritten at every build (weekly with the claims): the live folder and the damage-grade collection
_dmg_df=pd.DataFrame(_DMG_ROWS)
for _pth in (os.path.join('out','damage_weekly.csv'),os.path.join(_ROOT,'193_damage_grade_2026-09-17','out','damage_weekly_live.csv')):
    try: os.makedirs(os.path.dirname(_pth),exist_ok=True); _dmg_df.to_csv(_pth,index=False)
    except Exception as _e: print('damage_weekly.csv not written:',_e)
def _damage(d,call):
    if call not in _DMG_CUM: return 0.0
    s=_DMG_CUM[call][2]; s=s[s.index<=d]
    return float(s.iloc[-1]) if len(s) else 0.0
for _e in EP:   # the record table shows each recession's damage score (17 September 2026)
    if not _e.get('open_pub'): continue
    _a=pd.Timestamp(_e['open_pub']); _b=pd.Timestamp(_e['close_pub']) if _e.get('close_pub') else pd.Timestamp(today)
    if _a in _DMG_CUM: _e['damage_score']=round(_damage(_b,_a),1); _e['damage_pm']=round(_DMG_CUM[_a][3],1); _e['damage_depth']=round(_DMG_CUM[_a][4],1)
DMG=[]
for i,d in enumerate(DD):
    if DP[i]=='open' and d>=SITE_START:
        ep=[(a,b) for a,b in _EPD if a<=d<=b]
        if ep:
            a,b=ep[0]; dmg=_damage(d,a); DMG.append(round(dmg,2)); DV[i]=1.0+dmg; continue
    DMG.append(None)
print('damage at the close, by episode (score of 10; point-months; depth):',[(a.date().isoformat(),round(_damage(b,a),2),round(_DMG_CUM[a][3],1),round(_DMG_CUM[a][4],1)) for a,b in _EPD if a in _DMG_CUM],'| weekly rows',len(_DMG_ROWS),'nowcast rows',sum(1 for r in _DMG_ROWS if r['how']=='nowcast'))
_tick('daily series')
SERIES_D=pd.DataFrame({'value':DV,'reading':DR,'phase':DP,'branch':DB,'damage':DMG},index=pd.DatetimeIndex(DD)); SERIES_D=SERIES_D[SERIES_D.index>=SITE_START]
SERIES=SERIES[SERIES.index>=SITE_START]
# ---- the latest readings, and the forward log ----
def lastv(s): s=s.dropna(); return float(s.iloc[-1]), s.index[-1].date().isoformat()
def nxt_thu(d):
    d=pd.Timestamp(d); return (d+pd.offsets.Week(weekday=3)).date().isoformat()
def nxt_claims(through,days=12):
    # the Thursday whose release carries the week after the last week in hand (claims: week end + 12 days; the insured week
    # and the state rates: + 19). A release day already past whose data are not yet in hand stays the 'next' (marked pending).
    t=pd.Timestamp(through)+pd.Timedelta(days=days); s=t.date().isoformat()
    return s if t>pd.Timestamp(today) else s+' (released; not yet posted)'
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
add('open','Sahm gap (three-month average unemployment rate above its twelve-month low, as it stood on the release day)',RAW['X']*p['sahm'],p['sahm'],nxt=first_fri(today))
add('open',f'sudden stop: one week of initial claims above the claims base, percent (fires with the S&P 500 {KC[1]} percent under its 20-day high)',gKr*KC[0],float(KC[0]),nxt=12)
_TNAME={'unemp':'"unemployment"','layoffs':'"layoffs"','laidoff':'"laid off"'}
for _tag,(_tdd,_tgg,_trel) in (GT_TERMS.items() if 'GT_TERMS' in globals() else ([('unemp',(GT_DAY,GT7,GT_REL))] if 'GT_REL' in globals() else [])):
    add('open',f'sudden stop: the search week - 7-day mean of Google searches for {_TNAME.get(_tag,_tag)} above its base, percent (fires with the S&P 500 20 percent under its 20-day high at that day\'s close; known the next morning; the earliest term fires)',_trel.dropna(),float(KC[0]),nxt='daily')
_crd=((1-_SPX/_SPX.rolling(20,min_periods=10).max())*100).dropna()     # the market gate at the latest close (the search week reads the day's close; the claims week the close before its release)
add('open',f'sudden stop: S&P 500 below its high of the prior twenty trading days, percent, at the latest close (the claims week reads the close before its release, the search week the day\'s close)',_crd,float(KC[1]),nxt='daily')
if gW is not None: add('open',f"survey-week insured rate, rise above its 52-week low (branch W, line {p['wline']})",RAW['W']*p['wline'],p['wline'],nxt='survey')
if gV is not None: add('open',f"survey-week insured rate, rise above its 52-week low (branch V, line {p['wline2']})",RAW['V']*p['wline2'],p['wline2'],nxt='survey')
if gB is not None: add('open','state breadth, share of states with the insured rate 0.20 above its 52-week low',RAW['B']*p['bshare'],p['bshare'],nxt=19)
add('confirm','vacancy rate, 4-month mean below its 4-month maximum (openings as they stood on the JOLTS release day)',cV*p['vl'],p['vl'],nxt='JOLTS, next release')
add('confirm','hours pair (factory hours 2% off their 12-month high and nondurable jobs -1.2% over 3 months, as they stood on the release day; 1 = both)',cH,1.0,nxt=first_fri(today))
add('confirm',('housing x rate pair (starts or building permits 29 log points below their 12-month high, and the unemployment rate 0.4 above its 18-month low, each as it stood on its release day; 1 = both halves at their lines)' if 'mkpair_either_asof' in globals() else 'housing x rate pair (starts and the unemployment rate, each as it stood on its release day; 1 = both halves at their lines)'),cP*p['hline'],p['hline'],nxt='housing starts, next release')
add('confirm','starts x vacancy pair (starts 29 log points below their 12-month high and the vacancy rate 0.20 off its 4-month high; 1 = both)',cSV,1.0,nxt='housing starts, next release')
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
NEXT.append(dict(date=next((c['date'] for c in CAL if c['kind']=='h15'),'weekly'),what='H.15 week (commercial paper and bill rates), Federal Reserve, 4:15 PM ET on the first business day of the week; the S&P 500 close is read on claims days'))
NEXT.sort(key=lambda z:(0,z['date']) if len(z['date'])==10 else (1,z['date']))

# ---- every feed the rule reads: where it comes from, how often it updates, what it is through, when it updates next ----
def _fthr(x):
    try: return lastv(x)[1]
    except Exception: return None
def _fval(x,fmt='{:,.0f}',suf=''):
    # the latest value of a feed, as it stands, for the data inventory
    try: return fmt.format(lastv(x)[0])+suf
    except Exception: return None
_h15next=next((c['date'] for c in CAL if c['kind']=='h15'),None)
_nxt=lambda w: next((n['date'] for n in NEXT if n['what'].startswith(w)),None)
def _bnote():
    # the object is a year-over-year share, so a week with no states in the Department's archive costs two readings:
    # its own and the week 52 weeks later. The state data can be in hand while the object waits for its base week.
    try:
        _w=pd.read_csv(os.path.expanduser('~/Projects/Onset Detector Data/45_dol_first_prints_2026-09/state_iu_first_print_wide.csv'),index_col=0,parse_dates=True)
        _d=_w.index.max(); _o=pd.Timestamp(_fthr(RAW['B']))
        if _d>_o:
            _base=_o+pd.Timedelta(days=7)-pd.DateOffset(weeks=52)
            return f"state data in hand through {_d.date()}; the object is a year-over-year share and its base week {_base.date()} is missing from the Department's archive, so it resumes when the gap passes"
    except Exception: pass
    return None
_tick('feeds')
FEEDS=[
 dict(name='Initial claims, continued claims, insured unemployment rate',source='Department of Labor (the UI claims news release; ALFRED vintages after it)',every='Weekly - Thursday 8:30 AM ET (Wednesday before a Thursday holiday)',through=_fthr(ICfp),next=_nxt('Weekly claims'),url='https://www.dol.gov/ui/data.pdf',value=_fval(ICfp,'{:,.0f}',' initial claims, week ending '+str(_fthr(ICfp))),auto='yes'),
 dict(name='State insured unemployment rates (the breadth object)',source='Department of Labor (page 8 of the weekly release; the advance state table of the release PDF while the archive catches up)',every='Weekly - Thursday 8:30 AM ET, two weeks behind initial claims',through=_fthr(RAW['B']),next=_nxt('Weekly claims'),url='https://oui.doleta.gov/unemploy/claims.asp',value=None,auto='yes',note=_bnote()),
 dict(name='Unemployment rate, factory hours, nondurable employment',source='Bureau of Labor Statistics, Employment Situation',every='Monthly - usually the first Friday, 8:30 AM ET',through=_fthr(g_asof),next=_nxt('Employment Situation'),url='https://www.bls.gov/news.release/empsit.toc.htm',value=_fval(g_asof,'{:.2f}',' Sahm gap, points (the unemployment rate object the rule reads)'),auto='yes'),
 dict(name='Job openings (the vacancy rate)',source='Bureau of Labor Statistics, JOLTS',every='Monthly - about five weeks after the month, 10:00 AM ET',through=_fthr(G),next=_nxt('JOLTS'),url='https://www.bls.gov/jlt/',value=_fval(G,'{:+.2f}',' points from its four-month high (the confirmer needs the vacancy rate falling)'),auto='yes'),
 dict(name='Housing starts and building permits',source='Census Bureau, New Residential Construction',every='Monthly - about the 17th, 8:30 AM ET',through=_fthr(MX),next=_nxt('Housing starts'),url='https://www.census.gov/construction/nrc/index.html',value=_fval(MX,'{:.1f}',' log points below the 12-month high (the line is 29)'),auto='yes'),
 dict(name='Commercial paper and three-month bill rates (the spread)',source='Federal Reserve, H.15 selected interest rates',every='Weekly - the first business day after the week, 4:15 PM ET',through=_fthr(cS),next=_h15next,url='https://www.federalreserve.gov/releases/h15/',value=_fval(cS,'{:.2f}',' points, the wider paper market over the 3-month bill (the line is 0.90)'),auto='yes'),
 dict(name='S&P 500 daily close (the market gate of the sudden stop)',source='Yahoo Finance daily close',every='Every trading day - read at the 4:20 PM ET run, and again at 5:00 PM',through=_fthr(_SPX),next='the next weekday close',url='https://finance.yahoo.com/quote/%5EGSPC/',value=_fval(_SPX,'{:,.2f}',' at the close'),auto='yes'),
 dict(name='Sahm rule, real time (the comparator on the speed panel)',source='FRED SAHMREALTIME',every='Monthly - with the employment report',through=(lambda: (lambda _c: pd.to_datetime(_c.iloc[:,0]).max().strftime('%Y-%m') if len(_c) else None)(pd.read_csv('cache/SAHMREALTIME.csv')) if os.path.exists('cache/SAHMREALTIME.csv') else None)(),next=_nxt('Employment Situation'),url='https://fred.stlouisfed.org/series/SAHMREALTIME',value=(lambda: (lambda _c: '{:.2f}'.format(float(_c.iloc[-1,1]))+' (the rule fires at 0.50)' if len(_c) else None)(__import__('pandas').read_csv('cache/SAHMREALTIME.csv')) if os.path.exists('cache/SAHMREALTIME.csv') else None)(),auto='yes'),
]
_TSRC={'unemp':'"unemployment"','layoffs':'"layoffs"','laidoff':'"laid off"'}
_TQ={'unemp':'unemployment','layoffs':'layoffs','laidoff':'laid%20off'}
for _tg,(_a,_b,_r) in (GT_TERMS.items() if 'GT_TERMS' in globals() else []):
    FEEDS.append(dict(name=f'Search week: Google searches for {_TSRC.get(_tg,_tg)} (the sudden stop\'s second labour datum)',source='Google Trends, United States, daily index stitched onto one scale and extended each day',every="Daily - the day's index is known the next morning; read at every weekday close",through=_fthr(_r),next='the next weekday close',auto='yes',url='https://trends.google.com/trends/explore?date=today%203-m&geo=US&q='+_TQ.get(_tg,_tg),value=_fval(_r,'{:+.1f}',' per cent, the 7-day mean over its base (the line is 35)')))
_FEED_IDS=[('Initial claims','ICSA, CCSA, IURSA'),('State insured','ETA 539 state insured rates'),('Unemployment rate, factory','UNRATE, AWHMAN, NDMANEMP'),('Job openings','JTSJOL, CLF16OV'),
           ('Housing starts','HOUST, PERMIT'),('Commercial paper','DCPF1M, DCPN30, WTB3MS'),('S&P 500','^GSPC'),('Sahm rule','SAHMREALTIME')]
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
 'JTSJOL':(lambda: _last_vint('JTSJOL'),'{:,.0f}'),'CLF16OV':(lambda: _last_vint('CLF16OV'),'{:,.0f}'),'HOUST':(lambda: _last_vint('HOUST'),'{:,.0f}'),'PERMIT':(lambda: _last_vint('PERMIT'),'{:,.0f}'),
 'DCPF1M':(lambda: _last_num(os.path.join(_C25,'fred_daily','DCPF1M.csv')),'{:.2f}'),'DCPN30':(lambda: _last_num(os.path.join(_C25,'fred_daily','DCPN30.csv')),'{:.2f}'),'WTB3MS':(lambda: _last_num(os.path.join(_C25,'fred_weekly','WTB3MS.csv')),'{:.2f}'),
 '^GSPC':(lambda: lastv(_SPX)[0],'{:,.2f}'),'SAHMREALTIME':(lambda: _last_num('cache/SAHMREALTIME.csv'),'{:.2f}')}
# the units, as the publisher states them (Anthony, 17 September 2026: "make sure the proper units are displayed for each datum")
_UNITS_FEED={'ICSA':'claims, seasonally adjusted','CCSA':'claims, seasonally adjusted','IURSA':'percent, seasonally adjusted','UNRATE':'percent, seasonally adjusted','AWHMAN':'hours per week, seasonally adjusted',
 'NDMANEMP':'thousands of persons, seasonally adjusted','JTSJOL':'thousands of openings, seasonally adjusted','CLF16OV':'thousands of persons, seasonally adjusted','HOUST':'thousands of units, seasonally adjusted annual rate',
 'PERMIT':'thousands of units, seasonally adjusted annual rate','DCPF1M':'percent','DCPN30':'percent','WTB3MS':'percent','^GSPC':'index points','SAHMREALTIME':'percentage points'}
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
        if _f['name'].startswith('State insured'):
            _f['value']='{:.0%}'.format(lastv(RAW['B'])[0]); _f['values']=[('ETA 539',_f['value'],'share of states with the insured rate 0.20 point over its 52-week low')]; continue
        if _f['name'].startswith('Search week'):
            _tg=next((k_ for k_,v_ in _TSRC.items() if v_ in _f['name']),None)
            if _tg and _tg in _GT90:
                _f['value']='{:.0f}'.format(_GT90[_tg][1]); _f['through']=_GT90[_tg][0]
                _f['values']=[('Google Trends',_f['value'],'index, 0-100 over the past 90 days, the last complete day')]
            elif _tg: _f['value']='{:.1f}'.format(lastv(GT_TERMS[_tg][1])[0]); _f['values']=[('Google Trends',_f['value'],'index, the programme\'s stitched scale')]
            continue
        _ids=[x_.strip() for x_ in (_f.get('ids') or '').split(',') if x_.strip() in _RAWF]
        if _ids:
            _f['values']=[(x_,_RAWF[x_][1].format(_RAWF[x_][0]()),_UNITS_FEED.get(x_,'')) for x_ in _ids]
            _f['value']='; '.join(v_ for _,v_,_ in _f['values'])
    except Exception as _e: print('feed value not set for',_f['name'][:30],':',_e)
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
       ('Job openings','vacancy'),
       ('Housing starts','housing'),
       ('Commercial paper','paper'),
       ('S&P 500 daily close','sudden stop: S&P 500 below its high'),
       ('Search week: Google searches for "unemployment"','searches for "unemployment"'),
       ('Search week: Google searches for "layoffs"','searches for "layoffs"'),
       ('Search week: Google searches for "laid off"','searches for "laid off"')]
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
ANNS=[]
for e in epis:
    om=pd.Timestamp(e['open_month']+'-01'); hit=[i for i in range(13) if abs((om.year-PK[i].year)*12+om.month-PK[i].month)<=9]
    if not hit: continue
    i=hit[0]; pkm=PK[i].strftime('%Y-%m'); trm=TR[i].strftime('%Y-%m')
    pa=ANN.get(pkm); ta=TANN.get(trm)
    ANNS.append(dict(peak=pkm,trough=trm,peak_ann=pa,trough_ann=ta,rule_open=e['open_pub'],rule_close=e.get('close_pub'),rule_open_month=e['open_month'],rule_close_month=e.get('close_month'),
                     source=('committee' if PK[i]>=pd.Timestamp('1979-01-01') else 'Business Conditions Digest, first issue carrying the date') if pa else 'not dated by the NBER'))
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


# ---- /data/: every channel the legs read, with the day each is in hand through and the day its file was last
# ---- refreshed (17 September 2026; until now the data page listed the eleven core series only). Nothing is typed:
# ---- each row is read from the file the leg loader reads, and the letters are the legs that read it.
_MECH_NAME={'A1':'money: policy and market rates','A2':'credit: bank balance sheets','A2/B1':'credit and plumbing: borrowings from the Fed',
 'A3':'equity','A4':'housing','A5':'energy and commodities','A6':'inventories and durables','A7':'fiscal','A8/A9':'labour supply',
 'B1':'plumbing','B2':'external','B3':'trade prices','B4':'supply chain','C4':'policy uncertainty','activity':'activity','consumer':'consumer','core labour':'labour (core objects)'}
_DEADNOTE={'DTB1':'ends August 2001; successor DTB1YR not yet priced','TOTRA':'ends April 2018; successor WALCL not yet priced','LOLAOL':'ends April 2018',
 'M14064USM144NNBR':'NBER Macrohistory, ends 1965','H0RIFSPPFM06NB':'ends August 1997; spliced onto DCPF3M','DTWEXM':'ends December 2019; successor DTWEXBGS not yet priced','M0852BUSM497NNBR':'NBER Macrohistory series, ended','M03002USM544NNBR':'NBER Macrohistory series, ended'}
def _lf_src(sid):
    if sid.startswith('WB_'): return ('World Bank, Commodity Price Data (the pink sheet)','https://www.worldbank.org/en/research/commodity-markets')
    if sid.startswith('DTS') or sid.startswith('UIBENEFITS'): return ('U.S. Treasury, Daily Treasury Statement (Fiscal Data)','https://fiscaldata.treasury.gov/datasets/daily-treasury-statement/deposits-and-withdrawals-of-operating-cash')
    if sid.startswith('EIAW'): return ('EIA, Weekly Petroleum Status Report','https://www.eia.gov/petroleum/supply/weekly/')
    if sid.startswith('EIA930'): return ('EIA, Hourly Electric Grid Monitor (EIA-930)','https://www.eia.gov/electricity/gridmonitor/')
    if sid.startswith('OFR'): return ('Office of Financial Research, Financial Stress Index','https://www.financialresearch.gov/financial-stress-index/')
    if sid=='PMMS30W': return ('Freddie Mac, Primary Mortgage Market Survey','https://www.freddiemac.com/pmms')
    if sid=='EPUDAILY': return ('Baker, Bloom and Davis, daily news-based policy uncertainty','https://www.policyuncertainty.com/us_monthly.html')
    if sid=='GPRDAILY': return ('Caldara and Iacoviello, geopolitical risk index (daily)','https://www.matteoiacoviello.com/gpr.htm')
    if sid in ('SKEW','VVIX'): return ('Cboe, index history','https://www.cboe.com/us/indices/dashboard/'+sid+'/')
    if sid.startswith('TSA'): return ('TSA, checkpoint travel numbers','https://www.tsa.gov/travel/passenger-volumes')
    if sid.startswith('INDEED'): return ('Indeed Hiring Lab, job postings index','https://data.indeed.com/')
    if sid=='WARN': return ('the 25 states\' WARN notice pages','/data/warn/')
    if sid=='UMCSENT': return ('University of Michigan, Surveys of Consumers','https://www.sca.isr.umich.edu/')
    return ('FRED series '+sid,'https://fred.stlouisfed.org/series/'+sid)
# the units each channel is published in: FRED's own statement for its series (cache/leg_release_dates.json, fetched
# once by bhs_update.py); the other publishers' units as they state them
_UNITS_OTHER={'DTSWITHHELD':'millions of dollars, the day','DTSWITHHELD_S20':'millions of dollars, 20-business-day sum','DTSWITHHELD_S65':'millions of dollars, 65-business-day sum',
 'DTSCUSTOMS':'millions of dollars, the day','DTSCUSTOMS_S20':'millions of dollars, 20-business-day sum','DTSCUSTOMS_S65':'millions of dollars, 65-business-day sum',
 'UIBENEFITS':'millions of dollars, the day','UIBENEFITS_S20':'millions of dollars, 20-business-day sum','UIBENEFITS_S65':'millions of dollars, 65-business-day sum','DTSCORP_S65':'millions of dollars, 65-business-day sum',
 'EIAWRPUPUS2':'thousand barrels per day','EIAWRPUPUS2_M4':'thousand barrels per day, 4-week mean','EIAWGFUPUS2':'thousand barrels per day','EIAWGFUPUS2_M4':'thousand barrels per day, 4-week mean',
 'EIAWDIUPUS2':'thousand barrels per day','EIAWDIUPUS2_M4':'thousand barrels per day, 4-week mean','EIAWCESTUS1':'thousand barrels','EIAWGTSTUS1':'thousand barrels',
 'EIA930DEMAND':'megawatthours, the day','EIA930DEMAND_S7':'megawatthours, 7-day sum','EIA930DEMAND_S28':'megawatthours, 28-day sum','TSATHRU':'passengers, the day','TSATHRU_S7':'passengers, 7-day sum','TSATHRU_S28':'passengers, 28-day sum',
 'OFRFSI':'index, 0 = average stress','OFRCREDIT':'index, contribution to the OFR FSI','OFRFUNDING':'index, contribution to the OFR FSI','OFRVOL':'index, contribution to the OFR FSI','OFRSAFE':'index, contribution to the OFR FSI','OFREQUITY':'index, contribution to the OFR FSI',
 'INDEEDSA':'index, February 1, 2020 = 100, seasonally adjusted','INDEEDNSA':'index, February 1, 2020 = 100','PMMS30W':'percent, 30-year fixed rate','EPUDAILY':'index','GPRDAILY':'index, 1985-2019 average = 100',
 'SKEW':'index points','VVIX':'index points','WB_CRUDE_OIL_AVERAGE':'dollars per barrel, monthly average','WB_CRUDE_OIL_DUBAI':'dollars per barrel, monthly average','WB_LEAD':'dollars per metric ton, monthly average','WB_NICKEL':'dollars per metric ton, monthly average',
 'WARN':'notices on file, 25 states'}
def _lf_units(sid):
    if sid in _UNITS_OTHER: return _UNITS_OTHER[sid]
    e_=_LRD.get(sid,{})
    if e_.get('units'):
        sa_=e_.get('sa') or ''
        return e_['units']+({'SA':', seasonally adjusted','SAAR':', seasonally adjusted annual rate','NSA':', not seasonally adjusted'}.get(sa_,''))
    return None
# the file each walked leg actually reads (walk94.py): a stale copy of the same series sits in 186/data from the walk's
# setup and must not be shown (17 September 2026: the page showed AUTHNOTT through July from the copy while leg H read
# August from 183/data). Any other channel: the copy the pipeline wrote last.
_LF_EXACT={'BBKMCOIX':'177_new_legs_priced_2026-09-15','AUTHNOTT':'183_transmission_channels_2026-09-15','DRSFRMACBS':'183_transmission_channels_2026-09-15',
 'NEWORDER':'183_transmission_channels_2026-09-15','DCPF3M':'176_financial_leg_conjunction_2026-09-15','H0RIFSPPFM06NB':'176_financial_leg_conjunction_2026-09-15',
 'DTB3':'176_financial_leg_conjunction_2026-09-15','GS10':'176_financial_leg_conjunction_2026-09-15','GS1':'176_financial_leg_conjunction_2026-09-15',
 'CFNAIMA3':'176_financial_leg_conjunction_2026-09-15','GACDFSA066MSFRBPHI':'176_financial_leg_conjunction_2026-09-15'}
def _lf_file(sid):
    if sid in _LF_EXACT:
        p_=os.path.join(_ROOT,_LF_EXACT[sid],'data',sid+'.csv')
        if os.path.exists(p_): return p_
    best_=None
    for d_ in (os.path.join(_ROOT,'190_month_standard_and_hf_legs_2026-09-16','data'),os.path.join(_ROOT,'186_realtime_channels_2026-09-15','data'),
               os.path.join(_ROOT,'186_realtime_channels_2026-09-15','data_highfreq'),os.path.join(_ROOT,'186_realtime_channels_2026-09-15','data_nber'),
               os.path.join(_ROOT,'183_transmission_channels_2026-09-15','data'),os.path.join(_ROOT,'177_new_legs_priced_2026-09-15','data'),
               os.path.join(_ROOT,'176_financial_leg_conjunction_2026-09-15','data')):
        p_=os.path.join(d_,sid+'.csv')
        if os.path.exists(p_):
            m_=os.path.getmtime(p_)
            if best_ is None or m_>best_[0]: best_=(m_,p_)
    return best_[1] if best_ else None
def _lf_read(p_):
    q_=pd.read_csv(p_); c_=list(q_.columns)
    z_=pd.Series(pd.to_numeric(q_[c_[1]],errors='coerce').values,index=pd.to_datetime(q_[c_[0]],errors='coerce')).dropna().sort_index()
    return z_[~z_.index.duplicated(keep='last')]
def _lf_cadence(z_):
    t_=z_.index[z_.index>=z_.index.max()-pd.Timedelta(days=730)]
    if len(t_)<9: t_=z_.index
    sp_=float((t_.max()-t_.min()).days)/max(1,len(t_)-1)
    return 'daily' if sp_<=2.5 else 'weekly' if sp_<=8 else 'monthly' if sp_<=32 else 'quarterly' if sp_<=95 else 'annual'
_LF={}   # sid -> row
_tick('before leg inventory')
def _lf_add(sid,letter,role):
    r_=_LF.get(sid)
    if r_ is None:
        p_=_lf_file(sid); src_,url_=_lf_src(sid); r_=dict(channel=sid,source=src_,url=url_,legs=[],confirms=[],through=None,refreshed=None,cadence=None,n=0,note=_DEADNOTE.get(sid))
        if p_:
            try:
                z_=_lf_read(p_); r_['through']=z_.index.max().date().isoformat(); r_['n']=int(len(z_)); r_['cadence']=_lf_cadence(z_)
                r_['refreshed']=datetime.date.fromtimestamp(os.path.getmtime(p_)).isoformat()
            except Exception as _e: r_['note']=f'file not readable: {_e}'
            fp_=os.path.join(_ROOT,'186_realtime_channels_2026-09-15','vintages',sid+'_firstprint.csv')
            if os.path.exists(fp_):
                try:
                    q_=pd.read_csv(fp_); r_['first_prints_through']=str(pd.to_datetime(q_['date']).max().strftime('%Y-%m')); r_['first_prints_published']=str(pd.to_datetime(q_['published']).max().date())
                except Exception: pass
        elif sid=='WARN':
            try:   # the 25 state files: the latest notice date each carries and the day the index was last rewritten
                _ix=os.path.join(_ROOT,'117_warn_notices_2026-09-14','data','warn_notices','_INDEX.json'); _recs=json.load(open(_ix))
                r_['through']=max(str(x_.get('to') or '')[:10] for x_ in _recs); r_['n']=int(sum(int(x_.get('n') or 0) for x_ in _recs)); r_['cadence']='daily (as the states post)'
                r_['refreshed']=datetime.date.fromtimestamp(os.path.getmtime(_ix)).isoformat(); r_['note']='%d states'%len(_recs)
            except Exception as _e: r_['note']=f'index not readable: {_e}'
        else: r_['note']=(r_['note'] or '')+' (no file found)'
        _LF[sid]=r_
    (r_['legs'] if role=='proposer' else r_['confirms']).append(letter)
_HFL={r_['letter'] for r_ in _HFT}
_CONFSID=dict({k_:v_[0] for k_,v_ in _CONF86.items()},**{k_:v_[0] for k_,v_ in _HF.H.L.CONFS.items()})
for _r in CARRY_TABLE:
    if _r['channel'] in CARRY_EXCLUDED: continue
    _lf_add(_r['channel'],_r['letter'],'proposer')
    if _r['confirmer'] in _CONFSID: _lf_add(_CONFSID[_r['confirmer']],_r['letter'],'confirmer')
_WALKED_CH={'A':[('BBKMCOIX','proposer')],'Y':[('UNRATE','proposer'),('HOUST','confirmer')],'G':[('BORROW','proposer'),('HOUST','confirmer')],'J':[('M1SL','proposer'),('HOUST','confirmer')],
 'F':[('WBUSAPPWNSAUS','proposer'),('AWHMAN','confirmer')],'m':[('WPU101','proposer'),('HOUST','confirmer')],'N':[('WARN','proposer')],
 'M':[('DCPF3M','proposer'),('H0RIFSPPFM06NB','proposer'),('DTB3','proposer'),('GS10','confirmer'),('GS1','confirmer')],'H':[('AUTHNOTT','proposer'),('GS10','confirmer'),('GS1','confirmer')],
 'D':[('DRSFRMACBS','proposer')],'O':[('NEWORDER','proposer')],'E':[('TOTRA','proposer'),('HOUST','confirmer')],'S':[('CASACBW027NBOG','proposer'),('INDPRO','confirmer')],
 'T':[('IPDCONGD','proposer'),('HOUST','confirmer')],'c':[('CCNSA','proposer'),('AWHMAN','confirmer')]}
_ARMED_WALKED=set(str(p.get('newlegs') or ''))|set(str(p.get('extra') or ''))|{'N'}
for _L,_chs in _WALKED_CH.items():
    if _L=='Z': continue
    for _sid,_role in _chs: _lf_add(_sid,_L,_role)
_LEG_STATUS={}
for _L in _WALKED_CH: _LEG_STATUS[_L]='walked' if _L in _ARMED_WALKED else 'defined, not armed'
for _r in CARRY_TABLE:
    if _r['channel'] in CARRY_EXCLUDED: continue
    _LEG_STATUS[_r['letter']]='carried (record unchanged)' if _r['carried']=='True' else 'carried (armed from 2026-09-16)'
for _r in _LF.values():
    _r['mechanism']=None
for _r in CARRY_TABLE:
    if _r['channel'] in _LF and not _LF[_r['channel']].get('mechanism'): _LF[_r['channel']]['mechanism']=_MECH_NAME.get(_r['mechanism'],_r['mechanism'])
for _sid,_m in {'BBKMCOIX':'activity','UNRATE':'labour (core objects)','HOUST':'housing (confirmer)','AWHMAN':'labour (confirmer)','INDPRO':'activity (confirmer)','MANEMP':'labour (confirmer)','AWOTMAN':'labour (confirmer)',
 'M1SL':'money: the stock','WARN':'labour: layoffs announced by statute','DCPF3M':'money: commercial paper','H0RIFSPPFM06NB':'money: finance paper (to 1997)','DTB3':'money: the bill rate','GS10':'money: the term spread (confirmer)','GS1':'money: the term spread (confirmer)',
 'AUTHNOTT':'housing: authorised, not started','DRSFRMACBS':'credit: mortgage delinquency','NEWORDER':'inventories and durables: capital goods orders','M03002USM544NNBR':'supply chain (confirmer)','M0852BUSM497NNBR':'labour (confirmer)',
 'DTSWITHHELD_S65':'payments (confirmer)','UIBENEFITS_S20':'payments (confirmer)','EIAWRPUPUS2_M4':'physical activity (confirmer)','WBUSAPPWNSAUS':'formation: business applications (weekly)'}.items():
    if _sid in _LF and not _LF[_sid].get('mechanism'): _LF[_sid]['mechanism']=_m
for _r in _HFT:
    if _r['proposer'] in _LF: _LF[_r['proposer']]['mechanism']=_HF_ROUTE.get(_r['family'],_r['family'])
_TITLES={}
try:
    import glob as _glob
    for _cf in _glob.glob(os.path.join(_ROOT,'189_walk_from_1948_2026-09-16','catalog','fred_nation_usa_*.json')):
        for _it in json.load(open(_cf)):
            if isinstance(_it,dict) and _it.get('id') and _it.get('title'): _TITLES[_it['id']]=_re.sub(r'\s*\(DISCONTINUED\)','',_it['title'])
except Exception as _e: print('catalog titles not read:',_e)
_TITLES.update({'WB_CRUDE_OIL_AVERAGE':'Crude oil, average of Brent, Dubai and WTI','WB_CRUDE_OIL_DUBAI':'Crude oil, Dubai','WB_LEAD':'Lead','WB_NICKEL':'Nickel',
 'DTSWITHHELD':'Withheld income and employment taxes, daily','DTSWITHHELD_S65':'Withheld taxes, 65-day sum','DTSCUSTOMS':'Customs duties, daily','DTSCORP_S65':'Corporate income taxes, 65-day sum',
 'UIBENEFITS':'Unemployment insurance benefits paid, daily','UIBENEFITS_S20':'UI benefits paid, 20-day sum','EIAWRPUPUS2':'Petroleum products supplied, weekly','EIAWRPUPUS2_M4':'Petroleum products supplied, 4-week mean',
 'EIAWGTSTUS1':'Gasoline stocks, weekly','OFREQUITY':'OFR financial stress index, equity valuation','PMMS30W':'30-year fixed mortgage rate, weekly','EPUDAILY':'Economic policy uncertainty, daily news index',
 'GPRDAILY':'Geopolitical risk index, daily','SKEW':'Cboe SKEW index','VVIX':'Cboe VVIX index','WARN':'WARN layoff notices, 25 states','H0RIFSPPFM06NB':'Finance company paper, 3-month, to 1997'})
for _r in _LF.values(): _r['title']=_TITLES.get(_r['channel'],_r['channel'])
# where each channel stands and when its source next publishes (17 September 2026): FRED channels from the release
# calendar bhs_update.py keeps in cache/leg_release_dates.json; the others by their sources' own clocks
try: _LRD=json.load(open(os.path.join('cache','leg_release_dates.json')))
except Exception: _LRD={}
def _next_bday(d,n=1):
    d=pd.Timestamp(d)
    while n>0:
        d=d+pd.Timedelta(days=1)
        if d.weekday()<5: n-=1
    return d
def _prev_bday(d):
    d=pd.Timestamp(d)-pd.Timedelta(days=1)
    while d.weekday()>=5: d=d-pd.Timedelta(days=1)
    return d
def _next_weekday_named(d,wd):   # next date after d with weekday wd (0=Mon)
    d=pd.Timestamp(d)+pd.Timedelta(days=1)
    while d.weekday()!=wd: d=d+pd.Timedelta(days=1)
    return d
def _nth_bday_of_next_month(d,n):
    m=(pd.Timestamp(d)+pd.offsets.MonthBegin(1)); x=m-pd.Timedelta(days=1); k=0
    while k<n:
        x=x+pd.Timedelta(days=1)
        if x.weekday()<5: k+=1
    return x
from pandas.tseries.holiday import USFederalHolidayCalendar as _USFH
_HOL=set(d_.date() for d_ in _USFH().holidays(start='2020-01-01',end=str(datetime.date.today().year+10)+'-12-31'))   # (17 Sep 2026, collection 201) ten years past today, always; was fixed at 2035-12-31
def _is_bday(d): return d.weekday()<5 and d.date() not in _HOL
def _first_bday(month_start):
    x=pd.Timestamp(month_start)
    while not _is_bday(x): x=x+pd.Timedelta(days=1)
    return x
def _first_weekday_of(month_start,wd):
    x=pd.Timestamp(month_start)
    while x.weekday()!=wd: x=x+pd.Timedelta(days=1)
    return x
def _leg_next(sid,through,cadence=None,arrived=None):
    # the ISO day the source next publishes. `arrived` is the day the channel's latest observation reached us: a release
    # dated today whose data is already in hand is done, and the next calendar day is shown
    _t=pd.Timestamp(today); _ts=str(today)
    e_=_LRD.get(sid,{})
    def _by_postings():   # (the next posting from the days FRED last posted the series, the median gap in days); None when they say nothing
        vs=sorted(pd.Timestamp(x) for x in (e_.get('vintages') or []))
        gaps=sorted((b-a).days for a,b in zip(vs[:-1],vs[1:]) if (b-a).days>0)
        if len(gaps)<2: return None
        g=gaps[len(gaps)//2]
        if 25<=g<=35:   # monthly: the same weekday and rank in the month when the postings keep one
            import collections as _co
            rk=_co.Counter((v.weekday(),(v.day-1)//7) for v in vs[-6:]).most_common(1)[0]
            if rk[1]>=3:
                wd,rank=rk[0]; m=vs[-1]+pd.offsets.MonthBegin(1)
                for _k in range(3):
                    x=_first_weekday_of(m,wd)+pd.Timedelta(days=7*rank)
                    if x>=_t and x.month==m.month: return x.date().isoformat(),g
                    m=m+pd.offsets.MonthBegin(1)
        nx=vs[-1]+pd.Timedelta(days=g)
        while nx<_t: nx=nx+pd.Timedelta(days=g)
        while not _is_bday(nx): nx=nx+pd.Timedelta(days=1)
        return nx.date().isoformat(),g
    _m2=(pd.Timestamp(through)+pd.offsets.MonthBegin(2)).normalize() if through else None   # the month after the next observation's month
    if sid in ('GS10','GS1') and _m2 is not None:   # H.15 monthly averages: the first business day of the following month
        x=_first_bday(_m2)
        while x<_t: x=_first_bday(x+pd.offsets.MonthBegin(1))
        return x.date().isoformat()
    if sid=='WTISPLC' and _m2 is not None:   # FRED's splice of the EIA monthly spot price: the first Wednesday of the following month
        x=_first_weekday_of(_m2,2)
        while x<_t: x=_first_weekday_of(x+pd.offsets.MonthBegin(1),2)
        return x.date().isoformat()
    if sid=='BSCICP02DEM460S' and _m2 is not None:   # the OECD indicator as FRED posts it: the 15th, or the next business day
        x=_m2+pd.Timedelta(days=14)
        while not _is_bday(x): x=x+pd.Timedelta(days=1)
        while x<_t:
            x=x+pd.offsets.MonthBegin(1)+pd.Timedelta(days=14)
            while not _is_bday(x): x=x+pd.Timedelta(days=1)
        return x.date().isoformat()
    if e_.get('dates'):
        ds=[x for x in e_['dates'] if x>=_ts]
        if ds and ds[0]==_ts and arrived==_ts and len(ds)>1: ds=ds[1:]
        if ds:
            # a series posted less often than its release's calendar (the monthly policy-uncertainty index inside the
            # daily EPU release): dated by its own posting rhythm
            if cadence!='daily' and len(e_['dates'])>=3 and (pd.Timestamp(e_['dates'][2])-pd.Timestamp(e_['dates'][0])).days<=6:
                est=_by_postings()
                if est and est[1]>=5: return est[0]
            return ds[0]
    est=_by_postings()   # no calendar (the delinquency rates: the Fed announces no day; the pattern of its postings)
    if est: return est[0]
    if sid.startswith('WB_'):
        # the pink sheet appears in the first days of the month; if this month's is not in hand yet, it is due now
        thr=pd.Timestamp(through) if through else None; due=_nth_bday_of_next_month(_t-pd.offsets.MonthBegin(1)-pd.Timedelta(days=1),3)
        return (due if (thr is None or (thr+pd.offsets.MonthBegin(1))<_t) and due>=_t else _nth_bday_of_next_month(_t,3)).date().isoformat()
    if sid.startswith('EIAW') or sid=='PMMS30W':   # EIA weekly petroleum: Wednesday 10:30 ET; Freddie Mac PMMS: Thursday 12:00 ET
        wd=2 if sid.startswith('EIAW') else 3; thr=pd.Timestamp(through) if through else None
        # due today if today is the release day and the week it carries is not in hand yet (the EIA week ends the Friday
        # before its Wednesday; the PMMS week is dated its Thursday)
        if _t.weekday()==wd and thr is not None and (_t-thr).days>(5 if wd==2 else 0): return _t.date().isoformat()
        return _next_weekday_named(_t,wd).date().isoformat()
    if sid=='WARN': return _next_bday(_t).date().isoformat()
    if cadence in ('weekly','monthly','quarterly','annual') and through:   # neither calendar nor posting days: by the series' own cadence
        nx=pd.Timestamp(through)+{'weekly':pd.Timedelta(days=7),'monthly':pd.DateOffset(months=1),'quarterly':pd.DateOffset(months=3),'annual':pd.DateOffset(years=1)}[cadence]
        while nx<=_t: nx=nx+{'weekly':pd.Timedelta(days=7),'monthly':pd.DateOffset(months=1),'quarterly':pd.DateOffset(months=3),'annual':pd.DateOffset(years=1)}[cadence]
        while not _is_bday(nx): nx=nx+pd.Timedelta(days=1)
        return nx.date().isoformat()
    # the daily sources without a calendar (the Daily Treasury Statement, OFR, EPU, GPR, Cboe)
    if through and pd.Timestamp(through)<_prev_bday(_t):   # behind by two business days or more: the next posting is due today
        return (_t if _t.weekday()<5 else _next_bday(_t)).date().isoformat()
    if sid.startswith(('DTS','UIBENEFITS','SKEW','VVIX')):   # the Daily Treasury Statement and Cboe's indexes are posted after 4 PM ET
        return (_t if (_t.weekday()<5 and _now_et.hour<16) else _next_bday(_t)).date().isoformat()
    return _next_bday(_t).date().isoformat()                                            # posted in the morning for the day before: the next business day
def _fmt_val(v,raw=None):
    # the value with the publisher's own decimals (47.8 stays 47.8, 3.63 stays 3.63), at most two, four below one
    a=abs(v); d_=None
    if raw is not None:
        s_=str(raw).strip()
        if _re.fullmatch(r'-?\d+(\.\d+)?',s_): d_=len(s_.split('.')[1].rstrip('0')) if '.' in s_ else 0
    if d_ is None: d_=0 if a>=1000 else 1 if a>=100 else 2
    d_=min(d_,4 if a<1 else 2)
    return ('{:,.%df}'%d_).format(v)
# the day each channel's latest observation reached us, kept across builds (the files are rewritten every run, so their
# dates say nothing): an entry is written when the through-day changes; its first appearance carries no arrival day
_LEDP=os.path.join('cache','leg_through_ledger.json')
try: _LEDGER=json.load(open(_LEDP))
except Exception: _LEDGER={}
for _r in _LF.values():
    _r['next']=None; _r['value']=None
    _led=_LEDGER.get(_r['channel']); _thr=_r.get('through')
    if _thr and (_led is None or _led.get('through')!=_thr): _LEDGER[_r['channel']]={'through':_thr,'day':str(today),'seen_change':_led is not None}
    _arr=_LEDGER.get(_r['channel'],{}).get('day') if _LEDGER.get(_r['channel'],{}).get('seen_change') else None
    try:
        _r['next']=_leg_next(_r['channel'],_r.get('through'),_r.get('cadence'),_arr)
        if _r.get('note') and 'end' in _r['note'] and 'successor' in _r['note'] or (_r.get('note') or '').startswith('NBER Macrohistory') or (_r.get('note') or '').startswith('ends'): _r['next']='ended'
    except Exception as _e: print('next-published day not set for',_r['channel'],':',_e)
    try:
        p_=_lf_file(_r['channel'])
        if p_:
            z_=_lf_read(p_); raw_=None
            try:   # the publisher's own decimals: the last row of the file as written
                q_=pd.read_csv(p_,dtype=str); q_=q_[pd.to_datetime(q_.iloc[:,0],errors='coerce')==z_.index[-1]]
                if len(q_): raw_=str(q_.iloc[-1,1])
            except Exception: pass
            _r['value']=_fmt_val(float(z_.iloc[-1]),raw_)
        elif _r['channel']=='WARN': _r['value']='{:,}'.format(int(_r.get('n') or 0))
    except Exception: pass
    _r['units']=_lf_units(_r['channel'])
try: os.makedirs('cache',exist_ok=True); json.dump(_LEDGER,open(_LEDP,'w'),indent=0)
except Exception as _e: print('through ledger not written:',_e)
_tick('leg inventory')
LEG_FEEDS=sorted(_LF.values(),key=lambda r_:((r_.get('mechanism') or 'zz'),r_['channel']))
for _r in LEG_FEEDS: _r['legs']=''.join(sorted(set(_r['legs']))); _r['confirms']=''.join(sorted(set(_r['confirms'])))
LEG_STATUS=_LEG_STATUS
# stale = older than its publisher's own lag allows, counted from the observation's period start (17 September 2026,
# tightened from 21/28/120/250 days): a daily series posts within a business day or two (the geopolitical index three),
# a weekly within two weeks (H.8's nine-day lag), a monthly within four months of the month's first day (the transportation
# index: June's on the first of October), a quarterly within eight of the quarter's first day (the delinquency rates: the
# next quarter's posting eight weeks after that quarter ends); the weekly business applications are posted monthly by
# the Census, so they get seven weeks
_LAG_OK={'WBUSAPPWNSAUS':55}
_stale=[r_['channel'] for r_ in LEG_FEEDS if r_['through'] and not (r_.get('note') or '').startswith(('ends','NBER')) and 'end' not in (r_.get('note') or '')
        and (pd.Timestamp(today)-pd.Timestamp(r_['through'])).days>_LAG_OK.get(r_['channel'],{'daily':7,'weekly':20,'monthly':125,'quarterly':245,'annual':500}.get((r_['cadence'] or 'monthly').split(' ')[0],125))]
print('leg channels:',len(LEG_FEEDS),'| dead:',sum(1 for r_ in LEG_FEEDS if r_.get('note') and 'end' in (r_['note'] or '')),'| stale beyond cadence:',_stale if _stale else 'none')

from zoneinfo import ZoneInfo as _ZI
state=dict(built=str(today),built_at=datetime.datetime.now(_ZI('America/New_York')).strftime('%Y-%m-%d %H:%M'),next_releases=NEXT,feeds=FEEDS,leg_feeds=LEG_FEEDS,leg_status=LEG_STATUS,leg_channels_stale=_stale,calendar=CAL,calendar_dated_through=(_dated_through.isoformat() if _dated_through else None),announcements=ANNS,sahm_other=SAHM_OTHER,sahm=dict(dates=[t.strftime('%Y-%m') for t in SAHM.index],values=[round(float(v),3) for v in SAHM.values]),version=VERSION,walk=WALK,notes=dict(vacancy='job openings (JOLTS, over the labor force; the vintages exist from July 2010)',vintage='every monthly object - the unemployment rate, housing starts, factory hours, nondurable employment, job openings - is read for each month from the series as it stood on the day that month first appeared; weekly claims from the Department of Labor advance figures; the paper and bill rates and the S&P 500 are never revised',objects_added=('the starts x vacancy pair (a confirmer of the weak proposers), the sudden stop (one week of claims over its base with the S&P 500 under its 20-day high the same week), the paper spread on the wider of the financial and nonfinancial paper markets'+(' ; from v3.27 the sudden stop also reads the search week - the 7-day mean of Google searches for unemployment over the same base, known the next morning, with the S&P 500 at that day\'s close - and fires on the earlier of the claims week and the search week (the series exists from 2004 and enters there)' if 'GT_REL' in globals() else '')+(' ; from v3.29 the search week reads three labour terms - unemployment, layoffs, laid off - each over its own base, and fires on the earliest' if 'GT_TERMS' in globals() and len(GT_TERMS)>1 else '')+(' ; the housing x rate pair is confirmed by starts or by building permits at the starts line (permits as they stood on the day: ALFRED vintages from August 1999, the Economic Indicators tables as printed for 1969 and 1990, the current file elsewhere as a declared bound)' if 'mkpair_either_asof' in globals() else '')),arithmetic='every one-decimal object is read in exact tenths; a reading equal to its line is at the line',cosigner=('a proposal by the insured unemployment rate or by initial claims within 0.2 point (15 points for claims) above its line fires only if the three-month average unemployment rate, as last published, stands at least 0.2 point above its twelve-month low' if COS else None),lines_fixed=bool(COS),claims_base=('the four-week mean of initial claims is measured from the higher of its 52-week low and 85 percent of its trailing five-year median, as published' if 'ALPHA' in globals() else None)),lines={k:(None if v is None else v) for k,v in p.items()},standing=standing,carried_legs=[dict(letter=r['letter'],channel=r['channel'],mechanism=r['mechanism'],config='%s h%s q%s/%sy/h%s x %s h%s q%s ch%s'%(r['direction'],r['p_horizon'],r['p_q'],r['p_win'],r['p_hold'],r['confirmer'],r['c_hold'],r['c_q'],r['c_horizon']),screen_peaks=r['screen_peaks'],record_unchanged=(r['carried']=='True'),proposals=r['proposals']) for r in CARRY_TABLE if r['channel'] not in CARRY_EXCLUDED],carried_excluded=CARRY_EXCLUDED,pending_proposals=[dict(published=a,dated=b,leg=L,lapses=(pd.Timestamp(a)+pd.Timedelta(days=400)).date().isoformat()) for a,b,L in PENDING_NOW],realtime_note='A leg proposal is a provisional open until the core opens within four hundred days after it; if the core does not, the proposal lapses and is a real-time false alarm. Over 1962-2025 the walked rule had none. The walked record is the record of the rule without the carried legs; the carried legs are armed from 2026-09-16 and their past firings are shown as a backtest.',
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
