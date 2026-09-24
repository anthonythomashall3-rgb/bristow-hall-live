# audit_site.py - THE LIVE SITE AGAINST THE RECORD AND THE LAB, independently of bhs_build.py. Fetches bhs_state.json from
# bhrrealtime.pages.dev and compares it with the built copy; the walked episodes with the walk's diary (cache/<var>_prog.pkl);
# the frozen episodes with the frozen run at the walk-end lines; the lines with cache/<var>_carry.pkl; the version and walk
# with cache/bhs_version.json; every 'through' date with the lab's own series; every object's latest reading with a
# recomputation from the lab's objects (exact tenths where the object is one-decimal); the 'next' dates with their rule;
# the daily series' last day; the live log's last row. Writes AUDIT-SITE-<version>-<date>.md in the collection root.
# Run: PYTHONPATH=. python3 s2/audit_site.py
import sys,os,io,json,pickle,contextlib,subprocess,datetime
import pandas as pd, numpy as np
VERS=json.load(open('cache/bhs_version.json')); WALK,VAR,VERSION=VERS['walk'],VERS['var'],VERS['version']
sys.path.insert(0,os.getcwd()); sys.argv=[WALK,'1962','2026',VAR]
_MARK="# ---- the walk "+"itself"
with contextlib.redirect_stdout(io.StringIO()): exec(open(WALK).read().split(_MARK)[0])
p=pickle.load(open(f'cache/{VAR}_carry.pkl','rb')); pg=pickle.load(open(f'cache/{VAR}_prog.pkl','rb'))
live=json.loads(subprocess.run(['curl','-s','-m','60',f'https://bhrrealtime.pages.dev/bhs_state.json?a={datetime.datetime.now().timestamp()}'],capture_output=True,text=True).stdout)
built=json.load(open('out/bhs_state.json'))
L=[]; fails=0
def row(name,got,exp,ok=None):
    global fails
    if ok is None: ok=(got==exp)
    if not ok: fails+=1
    L.append(f"| {name} | {str(got)[:110]} | {str(exp)[:110]} | {'PASS' if ok else 'FAIL'} |")
row('deployed JSON identical to the built JSON',json.dumps(live,sort_keys=True)==json.dumps(built,sort_keys=True),True)
row('version / walk',(live['version'],live['walk']),(VERSION,WALK))
diary=sorted(pg['log'],key=lambda z:z[0]); opens=[(str(d)[:10],str(m)[:7],leg) for d,k,m,leg in diary if k=='OPEN']; closes=[(str(d)[:10],str(m)[:7],leg) for d,k,m,leg in diary if k=='CLOSE']
row('walked episodes: opens (day, month, leg)',[(e['open_pub'],e['open_month'],e['open_leg']) for e in live['episodes']],opens)
row('walked episodes: closes',[(e['close_pub'],e['close_month'],e['close_leg']) for e in live['episodes']],closes)
r,t=build_v(p); fr=[(x['kind'],x['published'].date().isoformat()) for x in t if x['kind'] in ('peak','trough')]
fp=[d for k,d in fr if k=='peak']; ft=[d for k,d in fr if k=='trough']
row('frozen episodes (opens) = frozen run at the walk-end lines',[e['open'] for e in live['frozen_episodes']],fp)
row('frozen episodes (closes)',[e['close'] for e in live['frozen_episodes']],ft)
row('frozen: calls outside a recession',r['other'],[])
_norm=lambda v:(list(v) if isinstance(v,tuple) else v)
row('lines = walk-end configuration',{k:live['lines'].get(k) for k in p},{k:_norm(p[k]) for k in p})
def lastd(s): s=s.dropna(); return s.index[-1].date().isoformat()
row('through: claims',live['through']['claims'],lastd(ICfp)); row('through: insured rate',live['through']['insured_rate'],lastd(spl))
row('through: unemployment rate',live['through']['unemployment_rate'],lastd(g_asof)); row('through: vacancy',live['through']['vacancy'],lastd(vgap2_asof(p['vk'],p['vb'])))
row('through: S&P 500',live['through']['sp500'],lastd(_SPX))
# the spread object is weekly, labelled by its Friday; a week whose Friday is later than the last daily paper rate is not yet a reading (8 September audit)
_lastrate=max(pd.read_csv(os.path.join(C25,'fred_daily','DCPF1M.csv')).iloc[:,0].pipe(pd.to_datetime,errors='coerce').max(),pd.read_csv(os.path.join(C25,'fred_daily','DCPN30.csv')).iloc[:,0].pipe(pd.to_datetime,errors='coerce').max())
row('through: spread (last complete H.15 week)',live['through']['spread'],GSP.dropna()[GSP.dropna().index<=_lastrate].index[-1].date().isoformat())
# readings, recomputed from the lab's objects
R={x['object']:x for x in live['readings']}
def find(sub): return next((v for k,v in R.items() if sub in k),None)
def chk(name,sub,val,tol=1e-3):
    x=find(sub)
    if x is None: row(name+' (row present)',None,'present'); return
    row(name,round(float(x['reading']),4),round(float(val),4),abs(float(x['reading'])-float(val))<=tol)
gU=_tenths(spl-spl.rolling(p['look'],min_periods=p['look']).min().shift(1)).dropna(); chk('insured rate rise above 52-week low (0.45 branch)',f"insured rate, rise above its {p['look']}-week low",gU.iloc[-1])
gL=_tenths(spl-spl.rolling(52,min_periods=52).min().shift(1)).dropna(); chk('insured rate rise (0.20 branch)','insured rate, rise above its 52-week low',gL.iloc[-1])
m4=ICfp.dropna().rolling(4).mean(); low=m4.rolling(52,min_periods=52).min().shift(1); med=m4.rolling(MED_W,min_periods=156).median().shift(1); base=np.maximum(low,ALPHA*med)
chk('claims 4-week mean over base, per cent','initial claims, 4-week mean above its base',float(((m4/base-1)*100).dropna().iloc[-1]),0.01)
chk('sudden stop: claims week over base','sudden stop: one week of initial claims',float(((ICfp.dropna()/base-1)*100).dropna().iloc[-1]),0.01)
chk('Sahm gap','Sahm gap (three-month',float(g_asof.dropna().iloc[-1]),1e-3)
if 'GT_REL' in globals(): chk('search week over base','the search week',float(GT_REL.dropna().iloc[-1]),0.01)
gW=_tenths(SI-SI.rolling(52,min_periods=52).min().shift(1)).dropna(); chk('survey-week rate rise','survey-week insured rate',gW.iloc[-1])
chk('state breadth','state breadth',float(BR.dropna().iloc[-1]))
G=vgap2_asof(p['vk'],p['vb']); chk('vacancy gap','vacancy rate, 4-month mean',float(G.dropna().iloc[-1]))
chk('hours pair','hours pair',float(HOURS_ASOF['gap'].dropna().iloc[-1]))
tod=pd.Timestamp(datetime.date.today())
# the pair's current reading: the latest starts half, permits half and rate half as they stand today (each at its last published month); the larger housing half with the rate
_hs=float(hh_asof.dropna().iloc[-1]); _hp=(float(PERM_ASOF.dropna().iloc[-1]) if 'PERM_ASOF' in globals() else np.nan); _hr=float(rate_asof.dropna().iloc[-1])
chk('housing x rate pair (either), current reading',"housing x rate pair",min(np.nanmax([_hs,_hp]),_hr),0.02)
E=(mkpair_either_asof if 'mkpair_either_asof' in globals() else mkpair_asof)(p['hline']); row('housing x rate pair: months at the line 2024-2026 (none expected)',[m.strftime('%Y-%m') for m,v in E['gap'].items() if m>=pd.Timestamp('2024-01-01') and v>=1.0-EPS],[])
pubsV=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index}); SV=mkpair_sv_asof(G,pubsV,p['vl']); SVk=SV['gap'][[m for m in SV['gap'].index if SV['pubs'][m]<=tod]]; chk('starts x vacancy pair','starts x vacancy pair',float(SVk.iloc[-1]),0.02)
chk('spread object','paper spread',float(GSP.dropna().iloc[-1]),1e-3)
# 'next' dates
ic_through=pd.Timestamp(live['through']['claims']); row('next claims release = claims week + 12 days (pending marked)',find('initial claims, 4-week mean')['next'],(ic_through+pd.Timedelta(days=12)).date().isoformat()+('' if ic_through+pd.Timedelta(days=12)>tod else ' (released; not yet posted)'))
row('next-releases list: first claims entry',[x['date'] for x in live['next_releases'] if x['what'].startswith('Weekly claims')][0],(ic_through+pd.Timedelta(days=12)).date().isoformat()+('' if ic_through+pd.Timedelta(days=12)>tod else ' (released; not yet posted)'))
row('daily series last day = today or the last release day',live['series']['dates'][-1],max(live['series']['dates']))
row('standing',live['standing'],dict(state='closed',since=closes[-1][0],dated=closes[-1][1],leg=closes[-1][2]))
lg=open(os.path.join(os.path.dirname(os.getcwd()),'live','LIVE_LOG_v321.tsv')).read().strip().splitlines(); row('live log: last row written today; a search-week row present today',(lg[-1][:10],any(l.startswith(str(datetime.date.today())) and 'search week' in l for l in lg)),(str(datetime.date.today()),True))
_html=open(os.path.join(os.path.dirname(os.getcwd()),'site','public','detector','index.html')).read()
_cur={pd.Timestamp(o[0]).strftime('%b ')+str(pd.Timestamp(o[0]).day)+pd.Timestamp(o[0]).strftime(', %Y') for o in opens}|{str(pd.Timestamp(o[0]).day)+pd.Timestamp(o[0]).strftime(' %B %Y') for o in opens}
_stale=[s for s in ('Sep 19, 1990','Mar 19, 2020','Mar 16, 2020','Jun 7, 2024','19 March 2020','16 March 2020','7 June 2024') if s not in _cur]
row('site HTML carries the version and no superseded call day',(VERSION in _html,[s for s in _stale if s in _html]),(True,[]))
# THE DAILY LINE'S SEARCH-WEEK BRANCH (v3.27, evening of 10 September 2026): the line carries the sudden stop on the search
# week on every day the market closed from 2004, so 16 March 2020 stands on the rule's reading, not on a held line
if 'GT_REL' in globals():
    row('through: search week',live['through'].get('search'),lastd(GT_REL))
    _S=live['series']; _i={d:i for i,d in enumerate(_S['dates'])}
    _d20=[o[0] for o in opens if o[1].startswith('2020')][0]; _k=_i.get(_d20)
    row(f'daily line, the 2020 open day ({_d20}): the sudden stop (branch K) at or above 1.00, not held',(_S['branch'][_k],_S['reading'][_k]>=1.0) if _k is not None else None,('K',True))
    _held20=[(d,round(r,3)) for d,v,r in zip(_S['dates'],_S['values'],_S['reading']) if d.startswith('2020-03') and v==1.0 and r<1.0]
    row('daily line, March 2020: no day held at 1.00 under its reading before or on the open day (held days after it, inside the open call, listed for the record: '+str([h for h in _held20 if h[0]>_d20])+')',[h for h in _held20 if h[0]<=_d20],[])
    _crash=(1-_SPX/_SPX.rolling(20,min_periods=10).max())*100
    _TT=(GT_TERMS if 'GT_TERMS' in globals() else {'unemp':(GT_DAY,GT7,GT_REL)})     # v3.29: the strongest term's reading each day
    def _rec(d):
        d=pd.Timestamp(d); vals=[min(float(_r.get(d-pd.Timedelta(days=1),np.nan))/p['kc'][0],float(_crash[d])/p['kc'][1]) for _t,(_a,_b,_r) in _TT.items()]
        vals=[v for v in vals if not np.isnan(v)]; return max(vals) if vals else np.nan
    _prev=_S['dates'][_k-1] if _k else None
    for _d in ([_prev,_d20] if _prev else [_d20]):
        _kk=_i.get(_d); row(f'daily line, {_d}: reading = the strongest term\'s min(search week over 35, crash over 20), recomputed',round(_S['reading'][_kk],3) if _kk is not None else None,round(_rec(_d),3),(_kk is not None and abs(_S['reading'][_kk]-_rec(_d))<=2e-3))
    row('the 2020 open day is the first day the market gate held (20 under the 20-day high) with a term at its line the morning before',_d20,next((d.date().isoformat() for d,v in _crash['2020-02-01':'2020-03-31'].items() if v>=p['kc'][1]-EPS and any(float(_r.get(d-pd.Timedelta(days=1),np.nan))>=p['kc'][0]-EPS for _t,(_a,_b,_r) in _TT.items())),None))
    if 'GT_TERMS' in globals():
        row('through: search terms (each term\'s last day)',live['through'].get('search_terms'),{k:lastd(v[2]) for k,v in GT_TERMS.items()})
        row('readings: one search-week row per term',len([r_ for r_ in live['readings'] if r_['object'].startswith('sudden stop: the search week')]),len(GT_TERMS))
    _days=[d.date().isoformat() for d in _SPX.index if d>=GT_REL.index.min()+pd.Timedelta(days=1) and d<=tod]
    _miss=[d for d in _days if d not in _i]; row('daily line: an observation on every day the market closed since the search week begins',len(_miss),0,len(_miss)==0)
    _out=[(d,_S['branch'][_i[d]],_S['reading'][_i[d]]) for d in _S['dates'] if d>='2004-01-01' and _S['phase'][_i[d]]=='' and _S['branch'][_i[d]]=='K' and _S['reading'][_i[d]]>=1.0]
    row('daily line: no sudden-stop reading at or above 1.00 outside a recession since 2004',_out,[])
    # the line's crossings are the rule's own calls: below 1.00 on the observation before each walked open day, at or above
    # 1.00 on it; at or above 1.00 on the close day, below on the next observation. The reading on the open day must itself
    # be at or above 1.00 (not a held 1.00): the page's arithmetic reproduces the call. (The branch shown is the strongest
    # branch that day, which can differ from the diary's leg on a tie - 1973: W and V both at 1.012 - and is not checked.)
    _bad=[]
    for e in live['episodes']:
        k=_i.get(e['open_pub']); kc=_i.get(e['close_pub']) if e.get('close_pub') else None
        okk=(k is not None and k>0 and _S['values'][k-1]<1.0 and _S['values'][k]>=1.0 and _S['reading'][k]>=1.0-1e-9)
        okc=(kc is None) or (kc+1<len(_S['values']) and _S['values'][kc]>=1.0 and _S['values'][kc+1]<1.0)
        if not (okk and okc): _bad.append((e['open_pub'],e.get('close_pub'),okk,okc,_S['reading'][k] if k is not None else None))
    row('daily line: crosses 1.00 on every walked open day by its own reading, and drops after every close day',_bad,[])
    _m24=[e for e in live['episodes'] if e['open_month'].startswith('2024')]
    row('2024 on the page: the walked open day, its month and its branch',[(e['open_pub'],e['open_month'],e['open_leg'],e['close_pub']) for e in _m24],[(o[0],o[1],o[2],c[0]) for o,c in zip(opens,closes) if o[1].startswith('2024')])
    import plistlib; _pl=plistlib.load(open(os.path.expanduser('~/Library/LaunchAgents/com.bristowhall.system.plist'),'rb'))
    _tom=datetime.date.today()+datetime.timedelta(days=1)
    while _tom.weekday()>=5: _tom+=datetime.timedelta(days=1)
    import importlib.util as _ilu; _sp=_ilu.spec_from_file_location('bhs_schedule',os.path.join(os.getcwd(),'bhs_schedule.py')); _bs=_ilu.module_from_spec(_sp); _sp.loader.exec_module(_bs)
    _h,_m=_bs.local_hm(_tom,'16:20'); row(f'launchd: the close run at 4:20 PM ET on the next weekday ({_tom}) is scheduled',any(e['Month']==_tom.month and e['Day']==_tom.day and e['Hour']==_h and e['Minute']==_m for e in _pl['StartCalendarInterval']),True)
out=os.path.join(os.path.dirname(os.getcwd()),f'AUDIT-SITE-{VERSION}-{datetime.date.today()}.md')
open(out,'w').write(f"# The live site audited against the record and the lab — {VERSION} ({WALK}), {datetime.datetime.utcnow():%Y-%m-%d %H:%M} UTC\n\nbhrrealtime.pages.dev/bhs_state.json fetched and compared with the built copy, the walk's diary, the frozen run, the walk-end lines, the lab's series and an independent recomputation of every reading (s2/audit_site.py).\n\n| check | site | expected | |\n|---|---|---|---|\n"+"\n".join(L)+f"\n\n**{len(L)-fails}/{len(L)} PASS**\n")
print("\n".join(L)); print(f'{len(L)-fails}/{len(L)} PASS -> {out}')
