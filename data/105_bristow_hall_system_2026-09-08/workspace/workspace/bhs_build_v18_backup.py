"""THE BRISTOW HALL SYSTEM — the rule as a published series, and the forward log (collection 105, 8 September 2026).
Builds, from the lab's data as fetched, (1) the rule's reading: one number a month, the strongest branch of v3.21's
peak side at its walk-end lines, a branch reading being min(the proposer's largest ratio to its line over the last
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
LIVE=os.path.join(os.environ['HOME'],'mnt','Onset Detector Data','105_bristow_hall_system_2026-09-08')
os.makedirs(os.path.join(LIVE,'live'),exist_ok=True)
today=datetime.date.today()
# ---- the opening indicator: branch scores over their lines ----
p=CFG
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
G=vgap2(p['vk'],p['vb']); Hc,MX=mkpair3(p['starts'],p['half'],3,p['minw']); Hh=mkhours(p['hrs'],p['nd'])
gU=(spl-spl.rolling(p['look'],min_periods=p['look']).min().shift(1)).dropna()/p['u45']
gL=(spl-spl.rolling(52,min_periods=52).min().shift(1)).dropna()/p['low']
m4=ICfp.dropna().rolling(4).mean(); gI=((m4/m4.rolling(52,min_periods=52).min().shift(1)-1)*100).dropna()/p['ic']
gX=(g/p['sahm']).dropna()
RAW=dict(U=gU.copy(),L=gL.copy(),I=gI.copy(),X=gX.copy())
gW=(SI-SI.rolling(52,min_periods=52).min().shift(1)).dropna()/p['wline'] if p.get('wline') else None
gV=(SI-SI.rolling(52,min_periods=52).min().shift(1)).dropna()/p['wline2'] if p.get('wline2') else None
gB=(BR/p['bshare']).dropna() if p.get('bshare') else None
RAW.update(W=None if gW is None else gW.copy(),V=None if gV is None else gV.copy(),B=None if gB is None else gB.copy())
cV=(G/p['vl']).dropna(); cH=(Hh['gap']/Hh['line']).dropna(); cP=(MX/p['hline']).dropna(); cS=(GSP/p['spr']).dropna()
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
            if v>=1.0: out[t]=0.0; armed=False; last=t     # the branch fires and is disarmed; the call itself is the episode, not this reading
            else: out[t]=v
        else:
            if rearm=='zero' and v<=0: armed=True
            elif rearm=='window' and v<1.0 and last is not None and t>=last+pd.DateOffset(months=months): armed=True
            elif rearm=='half' and v<0.5: armed=True
            elif rearm=='line' and v<1.0: armed=True
            out[t]=v if armed else 0.0
    return out
gU=armed_ratio(gU,'zero'); gL=armed_ratio(gL,'window'); gI=armed_ratio(gI,'zero')
if gW is not None: gW=armed_ratio(gW,'zero')
if gV is not None: gV=armed_ratio(gV,'window')
if gB is not None: gB=armed_ratio(gB,'half')
gX=armed_ratio(gX,'line')
idx=pd.date_range('1948-01-01',pd.Timestamp(today).replace(day=1),freq='MS')
def mm(x): return None if x is None else x.resample('MS').max().reindex(idx)
U,L,I,X,Wm,Vm,Bm=mm(gU),mm(gL),mm(gI),mm(gX),mm(gW),mm(gV),mm(gB)
Vc,Hpm,Ppm,Spm=mm(cV),mm(cH),mm(cP),mm(cS)
C1=[Vc,Hpm,Spm]; C2=[Ppm,Spm]
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
    branches=[('U',P['U'],C1),('L',P['L'],C2),('I',P['I'],C1),('W',P['W'],C2),('V',P['V'],C2),('B',P['B'],C2)]
    rows={}
    for t in idx:
        best=np.nan; who=''
        for nm,leg,confs in branches:
            if leg is None: continue
            w=leg[(leg.index>=t-pd.DateOffset(months=4))&(leg.index<=t)].dropna()
            if not len(w): continue
            sc=min(float(w.max()),best_conf(confs,t))
            if np.isnan(sc): continue
            if np.isnan(best) or sc>best: best,who=sc,nm
        pv=P['X'].get(t,np.nan)
        if not np.isnan(pv):
            w=Vc[(Vc.index>=t-pd.DateOffset(months=p['hback']))&(Vc.index<=t)].dropna().sort_values()
            wl=Vc[Vc.index<=t].dropna()
            sc=min(pv,float(w.iloc[-2]) if len(w)>=2 else np.nan,float(wl.iloc[-1]) if len(wl) else np.nan)      # the hub's hold: the vacancy at its line in TWO months of the window, and STILL at it in its latest reading (walk40)
            if not np.isnan(sc) and (np.isnan(best) or sc>best): best,who=sc,'X'
        rows[t]=(best,who)
    return pd.DataFrame({'indicator':{k:v[0] for k,v in rows.items()},'branch':{k:v[1] for k,v in rows.items()}}).dropna(subset=['indicator'])
OPEN=score_rows(dict(U=U,L=L,I=I,W=Wm,V=Vm,B=Bm,X=X))                                   # armed: the distance to the next call
OPENU=score_rows(dict(U=mm(RAW['U']),L=mm(RAW['L']),I=mm(RAW['I']),W=mm(RAW['W']),V=mm(RAW['V']),B=mm(RAW['B']),X=mm(RAW['X'])))   # unarmed: the reading inside a recession
# the line ends at the last month with a proposer's reading (the windows would otherwise carry it into months without data)
_lastm=max(x.dropna().index.max() for x in [RAW['U'],RAW['L'],RAW['I'],RAW['X'],RAW['W'],RAW['V'],RAW['B']] if x is not None).replace(day=1)
OPEN=OPEN[OPEN.index<=_lastm]; OPENU=OPENU[OPENU.index<=_lastm]
# THE SERIES IS MADE CONSISTENT WITH THE RULE'S OWN CALLS. The branch scores above ignore the re-arming of each leg, the
# hub's two-month hold as the walk applies it and the six-month minimum expansion, so a score can sit at or above 1.00
# in a month the rule does not speak. The rule frozen at its v3.21 lines is run in full (build_v) and its episodes taken:
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
# of the housing pair), JOLTS (the vacancy rate), housing starts, and the H.15 week (the paper spread, on its Friday). Each object is carried at the day it was published; the reading on a day uses only what was
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
PROP_A={'U':_pubdf(gU,_wk12),'L':_pubdf(gL,_wk12),'I':_pubdf(gI,_wk5),'X':_pubdf(gX,_pu)}
PROP_R={'U':_pubdf(RAW['U'],_wk12),'L':_pubdf(RAW['L'],_wk12),'I':_pubdf(RAW['I'],_wk5),'X':_pubdf(RAW['X'],_pu)}
for _k,_a,_r,_f in (('W',gW,RAW['W'],_sv),('V',gV,RAW['V'],_sv),('B',gB,RAW['B'],_wk19)):
    if _a is not None: PROP_A[_k]=_pubdf(_a,_f); PROP_R[_k]=_pubdf(_r,_f)
# the housing x rate pair as the rule reads it: each month's reading is set the day both halves are in (mkpair3's events)
def _pair_pub():
    rate=(((UR-UR.rolling(p['minw']).min())*10).round()/p['half']); mmv=lh.rolling(3).mean(); hh=((lh.rolling(12).max()-mmv)/p['starts'])
    ev=[(_rel(_RELH,m,17),'D',m) for m in hh.dropna().index]+[(_pu(m),'U',m) for m in rate.dropna().index if m>=pd.Timestamp('1960-01-01')]
    ev.sort(key=lambda x:(x[0],x[1])); lastD=None; lastU=None; rows=[]
    for d,kind,m in ev:
        if kind=='D': lastD=m if (lastD is None or m>lastD) else lastD
        else: lastU=m if (lastU is None or m>lastU) else lastU
        if lastD is None or lastU is None: continue
        v=min(hh.get(lastD,np.nan),rate.get(lastU,np.nan))
        if np.isnan(v): continue
        rows.append((d,max(lastD,lastU),float(v)/p['hline']))
    df=pd.DataFrame(rows,columns=['pub','t','v']).sort_values(['pub','t']).reset_index(drop=True)
    return dict(pub=df['pub'].values.astype('datetime64[ns]'),t=df['t'].values.astype('datetime64[ns]'),v=df['v'].values,tmax=np.maximum.accumulate(df['t'].values.astype('datetime64[ns]')))
CONF={'vac':_pubdf(cV,_pj),'hours':_pubdf(cH,_pu),'pair':_pair_pub(),'spread':_pubdf(cS,_sp)}
CONF1=['vac','hours','spread']; CONF2=['pair','spread']
_alld=set()
for _o in list(PROP_R.values())+list(CONF.values()): _alld.update(pd.DatetimeIndex(_o['pub']).tolist())
DAYS=sorted(d for d in _alld if pd.Timestamp('1948-01-01')<=d<=pd.Timestamp(today))
def _reading(P,d):
    best=np.nan; who=''
    cvals={c:_asof(CONF[c],d,6) for c in CONF}
    for nm,confs in (('U',CONF1),('L',CONF2),('I',CONF1),('W',CONF2),('V',CONF2),('B',CONF2)):
        if nm not in P: continue
        pv=_asof(P[nm],d,4)
        if np.isnan(pv): continue
        cc=[cvals[c] for c in confs if not np.isnan(cvals[c])]
        if not cc: continue
        cv=max(cc)
        sc=min(pv,cv)
        if np.isnan(best) or sc>best: best,who=sc,nm
    pv=_asof(P['X'],d,0)                     # the Sahm gap as last published
    if not np.isnan(pv):
        sec=_asof(CONF['vac'],d,p['hback'],second=True); latest=_asof(CONF['vac'],d,0)
        if not np.isnan(sec) and not np.isnan(latest):
            sc=min(pv,sec,latest)                 # two holds in the window, and the latest print still at the line (walk40's clause)
            if np.isnan(best) or sc>best: best,who=sc,'X'
    return best,who
def _inside_day(d): return any(a<=d<=b for a,b in FROZEN)
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
def first_fri(d):
    m=(pd.Timestamp(d)+pd.offsets.MonthBegin(1)); f=m+pd.offsets.Week(weekday=4) if m.weekday()!=4 else m; return f.date().isoformat()
R=[]
def add(side,name,series,line,through=None,nxt=''):
    v,dt=lastv(series); R.append(dict(side=side,object=name,reading=round(v,4),line=line,ratio=round(v/line,3) if line else None,through=through or dt,next=nxt))
add('open','insured rate, rise above its 91-week low',RAW['U']*p['u45'],p['u45'],nxt=nxt_thu(today))
add('open','insured rate, rise above its 52-week low',RAW['L']*p['low'],p['low'],nxt=nxt_thu(today))
add('open','initial claims, 4-week mean above its 52-week low, percent',RAW['I']*p['ic'],p['ic'],nxt=nxt_thu(today))
add('open','Sahm gap on first prints',RAW['X']*p['sahm'],p['sahm'],nxt=first_fri(today))
if gW is not None: add('open','survey-week insured rate, rise above its 52-week low',RAW['W']*p['wline'],p['wline'],nxt=nxt_thu(today))
if gV is not None: add('open','survey-week insured rate, rise above its 52-week low',RAW['V']*p['wline2'],p['wline2'],nxt=nxt_thu(today))
if gB is not None: add('open','state breadth, share of states with the insured rate 0.20 above its 52-week low',RAW['B']*p['bshare'],p['bshare'],nxt=nxt_thu(today))
add('confirm','vacancy rate, 4-month mean below its 4-month maximum',cV*p['vl'],p['vl'],nxt='JOLTS, next release')
add('confirm','hours pair (factory hours 2% off their 12-month high and nondurable jobs -1.2% over 3 months; 1 = both)',cH,1.0,nxt=first_fri(today))
add('confirm','housing x rate pair (starts and the unemployment rate; 1 = both halves at their lines)',cP*p['hline'],p['hline'],nxt='housing starts, next release')
add('confirm','paper spread, 13-week mean above its 39-week low, points',cS*p['spr'],p['spr'],nxt='H.15 week, next posting')
add('close','initial claims 3-week mean, drop from its 26-week maximum, log points',pd.Series(_FI['drop'].values,index=_CW),float(D_),nxt=nxt_thu(today))
add('close','run of falling weeks',pd.Series(_FI['run'].values,index=_CW).astype(float),3.0,nxt=nxt_thu(today))
add('close','hump above the 52-week minimum, log points',pd.Series(_FI['amp'].values,index=_CW),20.0,nxt=nxt_thu(today))
add('close','S&P 500 above its 26-week low on the release day, percent',pd.Series(sp_,index=_CW),float(S_),nxt=nxt_thu(today))
add('close','continued claims 4-week mean below its 26-week maximum, log points',pd.Series(fc_,index=_CW),3.0,nxt=nxt_thu(today))
add('close','insured rate 4-week mean below its 26-week maximum, tenths',pd.Series(du_,index=_CW),3.0,nxt=nxt_thu(today))
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
NEXT=[dict(date=nxt_thu(today),what='Weekly claims (initial claims, continued claims, insured unemployment rate), Department of Labor, 8:30 ET'),
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
# the readings table carries the same next-release days (they are computed after the readings, so patched here);
# each row also says what kind of release moves it, so the page can roll the date forward by its own clock
for r in R:
    if r['next']=='JOLTS, next release': r['next']=next(n['date'] for n in NEXT if n['what'].startswith('JOLTS')); r['next_kind']='jolts'
    elif r['next']=='housing starts, next release': r['next']=next(n['date'] for n in NEXT if n['what'].startswith('Housing')); r['next_kind']='starts'
    elif r['next']=='daily': r['next_kind']='daily'
    elif r['next']=='H.15 week, next posting': r['next_kind']='h15'; r['next']=next((c['date'] for c in CAL if c['kind']=='h15'),r['next'])
    elif r['next']==first_fri(today): r['next_kind']='jobs'
    else: r['next_kind']='claims'
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
PROV=bool(SERIES.index[-1]>pd.Timestamp(lastv(g)[1]).replace(day=1))   # the last month is provisional until its employment report is out
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
state=dict(built=str(today),built_at=datetime.datetime.now(_ZI('America/New_York')).strftime('%Y-%m-%d %H:%M'),next_releases=NEXT,calendar=CAL,calendar_dated_through=(_dated_through.isoformat() if _dated_through else None),announcements=ANNS,sahm_other=SAHM_OTHER,sahm=dict(dates=[t.strftime('%Y-%m') for t in SAHM.index],values=[round(float(v),3) for v in SAHM.values]),version=VERSION,walk=WALK,notes=dict(vacancy=('job openings and the labor force as first printed (from July 2010, where the vintages exist)' if 'rel_ic' in globals() and '_vfp' in globals() else 'vacancies from JOLTS (the current print)')),lines={k:(None if v is None else v) for k,v in p.items()},standing=standing,
           opening=dict(dates=[t.strftime('%Y-%m') for t in OPEN.index],values=[round(float(v),3) for v in OPEN['indicator']],branch=list(OPEN['branch'])),
           closing=dict(dates=[t.strftime('%Y-%m-%d') for t in CLOSE.index[CLOSE.index>=pd.Timestamp('1967-01-01')]],values=[None if np.isnan(v) else round(float(v),3) for v in CLOSE[CLOSE.index>=pd.Timestamp('1967-01-01')]]),
           frozen_episodes=[dict(open=a.date().isoformat(),close=(None if b.year==2100 else b.date().isoformat())) for a,b in FROZEN],
           nber=[dict(peak=pk.strftime('%Y-%m'),trough=tr.strftime('%Y-%m')) for pk,tr in zip(PK,TR)],
           chronology=epis,episodes=EP,series=dict(frequency='Daily, on release days',dates=[t.strftime('%Y-%m-%d') for t in SERIES_D.index],values=[round(float(v),3) for v in SERIES_D['value']],reading=[round(float(v),3) for v in SERIES_D['reading']],phase=list(SERIES_D['phase']),branch=list(SERIES_D['branch']),provisional=False),series_monthly=dict(dates=[t.strftime('%Y-%m') for t in SERIES.index],values=[round(float(v),3) for v in SERIES['value']],reading=[round(float(v),3) for v in SERIES['reading']],phase=list(SERIES['phase']),branch=list(SERIES['branch'])),readings=R,
           through=dict(claims=lastv(ICfp)[1],insured_rate=lastv(spl)[1],unemployment_rate=lastv(g)[1],vacancy=lastv(G)[1],sp500=lastv(_SPX)[1],spread=lastv(cS)[1]))
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
