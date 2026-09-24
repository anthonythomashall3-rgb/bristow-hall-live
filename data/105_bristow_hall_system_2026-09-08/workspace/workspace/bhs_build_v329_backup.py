"""THE BRISTOW HALL SYSTEM — the rule as a published series, and the forward log (collection 105, 8 September 2026).
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
# THE WALK THE SITE STANDS ON is named in cache/bhs_version.json: {"walk": "walk39.py", "var": "w39", "version": "v3.22"}.
# Walks from walk39 on carry the walk loop behind the marker "# ---- the walk itself"; walk38 and before split at the
# "Y0,Y1,VAR=" line. The preamble defines the objects, the release-day functions and build_v.
VERS=json.load(open('cache/bhs_version.json')) if os.path.exists('cache/bhs_version.json') else dict(walk='walk38.py',var='w38',version='v3.21')
WALK,VAR,VERSION=VERS['walk'],VERS['var'],VERS['version']
sys.argv=['x','2011','2012','wbhs']
_wsrc=open(WALK).read()
src=_wsrc.split("# ---- the walk itself")[0] if "# ---- the walk itself" in _wsrc else _wsrc.split("Y0,Y1,VAR=int(sys.argv[1])")[0]
with contextlib.redirect_stdout(io.StringIO()): exec(src)
out.close()
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
def score_rows(P):
    branches=[('U',P['U'],C1),('L',P['L'],C2),('I',P['I'],C1),('W',P['W'],C2),('V',P['V'],C2),('B',P['B'],C2),('Um',P.get('Um'),C1),('Lm',P.get('Lm'),C2)]
    rows={}
    for t in idx:
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
    return pd.DataFrame({'indicator':{k:v[0] for k,v in rows.items()},'branch':{k:v[1] for k,v in rows.items()}}).dropna(subset=['indicator'])
OPEN=score_rows(dict(U=U,L=L,I=I,W=Wm,V=Vm,B=Bm,X=X,K=Km,Um=Umm,Lm=Lmm))                                   # armed: the distance to the next call
OPENU=score_rows(dict(U=mm(RAW['U']),L=mm(RAW['L']),I=mm(RAW['I']),W=mm(RAW['W']),V=mm(RAW['V']),B=mm(RAW['B']),X=mm(RAW['X']),K=_kmm(mm(RAW['K']),RAW['KS']),Um=mm(RAW['Um']),Lm=mm(RAW['Lm'])))   # unarmed: the reading inside a recession
# the line ends at the last month with a proposer's reading (the windows would otherwise carry it into months without data)
_lastm=max(x.dropna().index.max() for x in [RAW['U'],RAW['L'],RAW['I'],RAW['X'],RAW['W'],RAW['V'],RAW['B'],RAW['K'],RAW['KS']] if x is not None).replace(day=1)
OPEN=OPEN[OPEN.index<=_lastm]; OPENU=OPENU[OPENU.index<=_lastm]
# THE SERIES IS MADE CONSISTENT WITH THE RULE'S OWN CALLS. The branch scores above ignore the re-arming of each leg, the
# hub's two-month hold as the walk applies it and the six-month minimum expansion, so a score can sit at or above 1.00
# in a month the rule does not speak. The rule frozen at its walk-end lines is run in full (build_v) and its episodes taken:
# inside an episode the series reads at least 1.00, outside it reads at most 0.99. At or above 1.00 means the rule is in
# a recession it has called; the distance below 1.00 says how far the nearest branch stands from speaking.
with contextlib.redirect_stdout(io.StringIO()): _r,_t=build_v(p)
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
DV=[]; DR=[]; DP=[]; DB=[]; DD=[]
for d in DAYS:
    ins=_inside_day(d)
    r,who=_reading(PROP_R if ins else PROP_A,d)
    if np.isnan(r): continue
    r=float(max(0.0,r))
    DD.append(d); DR.append(r); DB.append(who); DP.append('open' if ins else '')
    DV.append(float(max(1.0,r)) if ins else float(min(0.99,r)))
SERIES_D=pd.DataFrame({'value':DV,'reading':DR,'phase':DP,'branch':DB},index=pd.DatetimeIndex(DD)); SERIES_D=SERIES_D[SERIES_D.index>=SITE_START]
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
from zoneinfo import ZoneInfo as _ZI
state=dict(built=str(today),built_at=datetime.datetime.now(_ZI('America/New_York')).strftime('%Y-%m-%d %H:%M'),next_releases=NEXT,feeds=FEEDS,calendar=CAL,calendar_dated_through=(_dated_through.isoformat() if _dated_through else None),announcements=ANNS,sahm_other=SAHM_OTHER,sahm=dict(dates=[t.strftime('%Y-%m') for t in SAHM.index],values=[round(float(v),3) for v in SAHM.values]),version=VERSION,walk=WALK,notes=dict(vacancy='job openings (JOLTS, over the labor force; the vintages exist from July 2010)',vintage='every monthly object - the unemployment rate, housing starts, factory hours, nondurable employment, job openings - is read for each month from the series as it stood on the day that month first appeared; weekly claims from the Department of Labor advance figures; the paper and bill rates and the S&P 500 are never revised',objects_added=('the starts x vacancy pair (a confirmer of the weak proposers), the sudden stop (one week of claims over its base with the S&P 500 under its 20-day high the same week), the paper spread on the wider of the financial and nonfinancial paper markets'+(' ; from v3.27 the sudden stop also reads the search week - the 7-day mean of Google searches for unemployment over the same base, known the next morning, with the S&P 500 at that day\'s close - and fires on the earlier of the claims week and the search week (the series exists from 2004 and enters there)' if 'GT_REL' in globals() else '')+(' ; from v3.29 the search week reads three labour terms - unemployment, layoffs, laid off - each over its own base, and fires on the earliest' if 'GT_TERMS' in globals() and len(GT_TERMS)>1 else '')+(' ; the housing x rate pair is confirmed by starts or by building permits at the starts line (permits as they stood on the day: ALFRED vintages from August 1999, the Economic Indicators tables as printed for 1969 and 1990, the current file elsewhere as a declared bound)' if 'mkpair_either_asof' in globals() else '')),arithmetic='every one-decimal object is read in exact tenths; a reading equal to its line is at the line',cosigner=('a proposal by the insured unemployment rate or by initial claims within 0.2 point (15 points for claims) above its line fires only if the three-month average unemployment rate, as last published, stands at least 0.2 point above its twelve-month low' if COS else None),lines_fixed=bool(COS),claims_base=('the four-week mean of initial claims is measured from the higher of its 52-week low and 85 percent of its trailing five-year median, as published' if 'ALPHA' in globals() else None)),lines={k:(None if v is None else v) for k,v in p.items()},standing=standing,
           opening=dict(dates=[t.strftime('%Y-%m') for t in OPEN.index],values=[round(float(v),3) for v in OPEN['indicator']],branch=list(OPEN['branch'])),
           closing=dict(dates=[t.strftime('%Y-%m-%d') for t in CLOSE.index[CLOSE.index>=pd.Timestamp('1967-01-01')]],values=[None if np.isnan(v) else round(float(v),3) for v in CLOSE[CLOSE.index>=pd.Timestamp('1967-01-01')]]),
           frozen_episodes=[dict(open=a.date().isoformat(),close=(None if b.year==2100 else b.date().isoformat())) for a,b in FROZEN],
           nber=[dict(peak=pk.strftime('%Y-%m'),trough=tr.strftime('%Y-%m')) for pk,tr in zip(PK,TR)],
           chronology=epis,episodes=EP,series=dict(frequency='Daily, on release days',dates=[t.strftime('%Y-%m-%d') for t in SERIES_D.index],values=[round(float(v),3) for v in SERIES_D['value']],reading=[round(float(v),3) for v in SERIES_D['reading']],phase=list(SERIES_D['phase']),branch=list(SERIES_D['branch']),provisional=False),series_monthly=dict(dates=[t.strftime('%Y-%m') for t in SERIES.index],values=[round(float(v),3) for v in SERIES['value']],reading=[round(float(v),3) for v in SERIES['reading']],phase=list(SERIES['phase']),branch=list(SERIES['branch'])),readings=R,
           through=dict(claims=lastv(ICfp)[1],insured_rate=lastv(spl)[1],unemployment_rate=lastv(g_asof)[1],vacancy=lastv(G)[1],sp500=lastv(_SPX)[1],spread=lastv(cS)[1],search=(lastv(GT_REL)[1] if 'GT_REL' in globals() else None),search_terms=({k:lastv(v[2])[1] for k,v in GT_TERMS.items()} if 'GT_TERMS' in globals() else None)))
json.dump(state,open(os.path.join(LIVE,'bhs_state.json'),'w'))
json.dump(state,open('out/bhs_state.json','w'))
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
