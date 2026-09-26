"""THE WALK-FORWARD DIARY WITH THE SURVEY-WEEK OBJECT AND STATE BREADTH. The eighth object is the insured unemployment rate in the week
the household survey covers, published about twelve days after that week ends and so a median twelve days ahead of the
employment report. It is the same underlying series as the low branch's proposer, so it inherits that branch's
confirmers - the housing pair and the paper spread - rather than being given a set of its own. Its two lines are
re-chosen every month from the past alone, like every other number."""
import sys,pickle
exec(open('walk3.py').read().split('CACHE6={}')[0].replace("out=open('walk3_%s.out'%sys.argv[1],'w')","out=open('walk9_%s_%s.out'%(sys.argv[3],sys.argv[1]),'w')"))
D=W+'/lab/data/fred_weekly'
own=pd.read_csv('cache/weekly_iur_prewar.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
frd=pd.read_csv(D+'/IURSA.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
# Rule 23 clause 1: where a vintage record exists it is used. This line's transcription of the printed
# weekly releases IS the as-printed record to April 1983, so it is used to its end and the Department's current
# file only afterwards.
IURW=pd.concat([own,frd[frd.index>own.index.max()]]).sort_index()
# ---- v3.76 (26 September 2026; collections 436, 440, 441 - option (a), the record on the data as printed): the survey week reads the
# ---- Department's PRINTED seasonally adjusted insured rate from 2 August 1975 (the earliest release of each week, from the merged
# ---- first-print table the build writes, E66) in place of the lab's weekly construction (preweek.py) and FRED's current file, which
# ---- stand before 1975 and wherever no print exists.
import os
_mt376=[p_ for p_ in ('cache/national_first_prints_1985_live.csv',os.path.join(W.replace('24_bristow_rule_lab/workspace',''),'105_bristow_hall_system_2026-09-08','workspace','cache','national_first_prints_1985_live.csv')) if os.path.exists(p_)]
SURVEY_WEEK_PRINTED=None
if _mt376:
    _fpw=pd.read_csv(_mt376[0]); _fpw['_w']=pd.to_datetime(_fpw['iu_week_ended'],errors='coerce'); _fpw['_r']=pd.to_datetime(_fpw['release_date'],errors='coerce'); _fpw['_v']=pd.to_numeric(_fpw['iur_sa'],errors='coerce')
    _fpw=_fpw.dropna(subset=['_w','_v']).sort_values(['_w','_r']); _fpw1=_fpw.groupby('_w')['_v'].first()
    _cw376=IURW.index.intersection(_fpw1.index); IURW.loc[_cw376]=_fpw1.loc[_cw376].values; _xw376=_fpw1.index.difference(IURW.index)
    IURW=pd.concat([IURW,_fpw1.loc[_xw376]]).sort_index(); SURVEY_WEEK_PRINTED=dict(replaced=int(len(_cw376)),added=int(len(_xw376)),first=str(_fpw1.index.min().date()),last=str(_fpw1.index.max().date()))
else: print('v3.76 WARNING: the merged first-print table is missing - the survey week reads the lab construction and the current file')
def survey(s):
    rows={}
    for t,v in s.items():
        m=pd.Timestamp(t.year,t.month,1); d=abs((t-pd.Timestamp(t.year,t.month,12)).days)
        if m not in rows or d<rows[m][0]: rows[m]=(d,v,t)
    _last=s.index.max()   # v3.76 L1' (collections 433, 438, 441): a month is not read until its week dated the 9th-15th is out or the data pass its 15th
    for _m in [m for m in rows if not (9<=rows[m][2].day<=15) and _last<=m+pd.Timedelta(days=14)]: del rows[_m]
    idx=sorted(rows); return pd.Series([rows[m][1] for m in idx],index=idx), pd.Series([rows[m][2] for m in idx],index=idx)
SI,SW=survey(IURW)
def leg_sv(line,look=52,pub=12,rearm='zero'):
    gap=(SI-SI.rolling(look,min_periods=look).min().shift(1)).dropna(); c=[]; armed=True; last=None
    for t,v in gap.items():
        if armed and v>=line: c.append((SW[t]+pd.Timedelta(days=pub),t)); armed=False; last=t
        elif not armed:
            if rearm=='zero' and v<=0: armed=True
            elif rearm=='window' and v<line and t>=last+pd.DateOffset(months=4): armed=True
    return c
import glob,os
_cols={}
for _f in sorted(glob.glob(D+'/*INSUREDUR.csv')):
    _cols[os.path.basename(_f)[:2]]=pd.read_csv(_f,index_col=0,parse_dates=True).iloc[:,0].dropna()
ST=pd.DataFrame(_cols).sort_index(); exec(open('s2/state_rates_as_printed.py').read()); STMN=ST.rolling(52,min_periods=52).min().shift(1)   # v3.76: B's states as printed
BR=(((ST-STMN)>=0.20).sum(axis=1)/ST.notna().sum(axis=1)).dropna()
def leg_br(share):
    c=[]; armed=True
    for t,v in BR.items():
        if armed and v>=share: c.append((t+pd.Timedelta(days=19),pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<share*0.5: armed=True
    return c
def build9(p):
    G=vgap2(p['vk'],p['vb']); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=p['vl'],pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,p['u45'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['u45'])
    F25=[x for x in leg_gap_mx2(gm,p['low'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['low'])
    Hc,MX=mkpair3(p['starts'],p['half'],3,p['minw']); Hh=mkhours(p['hrs'],p['nd'])
    SP=dict(name='spread',gap=GSP,line=p['spr'],pub_lag_days=1)
    def hubv(sl):
        calls=[]; armed=True
        for m,v in g.items():
            if m<pd.Timestamp('1948-06-01'): continue
            if armed and v>=sl:
                w=G[(G.index>=m-pd.DateOffset(months=6))&(G.index<=m)]; hit=w[w>=p['vl']]
                if len(hit):
                    kk=hit.index[0]; sp=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
                    calls.append((max(sp,pubs[kk]),m-pd.DateOffset(months=3),'hub')); armed=False
            elif not armed and v<sl: armed=True
        return calls
    C1=[Vc,Hh,SP]; C2=[Hc,SP]; ALL=[Vc,Hh,Hc,SP]
    U=confirm_w(leg_gapL(spl,p['u45'],p['look'],rearm='zero')+F45,C1,'month'); L=confirm_w(leg_gapL(spl,p['low'],52,rearm='window')+F25,C2,'month')
    X=hubv(p['sahm']); I=confirm_w(leg_ic(ICfp,p['ic']),C1,'month')
    m4=ICfp.rolling(4).mean(); rel_=((m4/m4.rolling(52,min_periods=52).min().shift(1)-1)*100).dropna()
    cc=[]; armed=True
    for t,v in rel_.items():
        if armed and v>=p['deep']: cc.append((t+pd.Timedelta(days=5),pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=0: armed=True
    legs={'U':[(a,b) for a,b,c in U],'L':[(a,b) for a,b,c in L],'X':[(a,b) for a,b,c in X],'I':[(a,b) for a,b,c in I],
          'D':[(a,b) for a,b,c in confirm_n(cc,ALL,n=2)]}
    if p.get('wline'): legs['W']=[(a,b) for a,b,c in confirm_w(leg_sv(p['wline'],rearm='zero'),C2,'month')]
    if p.get('wline2'): legs['V']=[(a,b) for a,b,c in confirm_w(leg_sv(p['wline2'],rearm='window'),C2,'month')]
    if p.get('bshare'): legs['B']=[(a,b) for a,b,c in confirm_w(leg_br(p['bshare']),C2,'month')]
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TLH)
    return score13(turns),turns
CACHE9={}
def ev9(p):
    k=tuple(sorted((a,str(b)) for a,b in p.items()))
    if k not in CACHE9: CACHE9[k]=build9(p)
    return CACHE9[k]
BASE9=dict(BASE); BASE9['deep']=15; BASE9['wline']=None; BASE9['wline2']=None; BASE9['bshare']=None
ANN={'1948-11':'1949-06-01','1953-07':'1954-08-01','1957-08':'1958-06-01','1960-04':'1961-02-01','1969-12':'1970-08-01',
     '1973-11':'1974-11-01','1980-01':'1980-06-03','1981-07':'1982-01-06','1990-07':'1991-04-25','2001-03':'2001-11-26',
     '2007-12':'2008-12-01','2020-02':'2020-06-08','2024-04':None}
ANNT=[pd.Timestamp(ANN[PK[i].strftime('%Y-%m')]) if ANN[PK[i].strftime('%Y-%m')] else pd.Timestamp('2100-01-01') for i in range(13)]
GRID=[('sahm',[0.50,0.45,0.43,0.40]),('vl',[0.30,0.25,0.20,0.15]),('u45',[0.55,0.45,0.35]),('low',[0.30,0.25,0.20]),
      ('look',[52,78,91,130]),('spr',[1.6,round(LINE,3),1.1]),('ic',[60,50,45]),('deep',[15,10,7.5,5]),
      ('wline',[None,0.40,0.35,0.30,0.25]),('wline2',[None,0.60,0.50,0.45]),('bshare',[None,0.60,0.50,0.40])]
Y0,Y1,VAR=int(sys.argv[1]),int(sys.argv[2]),sys.argv[3]
if 'keep' in VAR:
    # a route that costs nothing on the past record is kept: the safest line that leaves the record unchanged is
    # preferred to having no route at all, so None is moved to the END of the order for the two survey-week lines
    GRID=[(n,([x for x in g if x is not None]+[None]) if n in ('wline','wline2','bshare') else g) for n,g in GRID]
def clean(q,cut,ks):
    r,t=ev9(q)
    if [o for o in r['other'] if pd.Timestamp(o[0])<cut]: return None
    if [x for x in t if x['kind']=='peak' and x['published']<pd.Timestamp('1948-06-01')]: return None
    v=[r['lags_p'][j] for j in ks if j in r['lags_p']]
    if len(v)!=len(ks): return None
    return v
def obj(v): return (sum(1 for x in v if x>31), float(np.median(v)), float(np.mean(v)))
LOG=[]; last=None; CHOSEN={}
for Y in range(Y0,Y1+1):
    for M in range(1,13):
        cut=pd.Timestamp(Y,M,1); ks=[i for i in range(13) if ANNT[i]<cut]
        if not ks: continue
        p=dict(BASE9) if last is None else dict(last)
        for _ in range(2):
            changed=False
            for name,grid in GRID:
                ok={}
                for gv in grid:
                    q=dict(p); q[name]=gv; v=clean(q,cut,ks)
                    if v is not None: ok[gv]=obj(v)
                if not ok: continue
                nv=min(ok,key=lambda g:(ok[g],grid.index(g)))
                if nv!=p[name]: changed=True
                p[name]=nv
            if not changed: break
        last=dict(p); CHOSEN[cut]=dict(p); r,t=ev9(p)
        nxt=cut+pd.DateOffset(months=1)
        for x in t:
            if x['kind'] in ('peak','trough') and cut<=x['published']<nxt:
                LOG.append((x['published'],'OPEN' if x['kind']=='peak' else 'CLOSE',x['date'],x['leg']))
LOG.sort(key=lambda z:z[0])
for pub,kind,dt,leg in LOG: P(f"   {pub:%Y-%m-%d}  {kind:5s} dated {dt:%Y-%m}  by {leg}")
pickle.dump(LOG,open(f'cache/{VAR}_{Y0}.pkl','wb'))
pickle.dump(CHOSEN,open(f'cache/{VAR}_chosen_{Y0}.pkl','wb'))
out.close()
