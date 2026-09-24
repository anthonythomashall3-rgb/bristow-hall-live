"""THE TROUGH SIDE MADE CAUSAL. Until now the closers' drops were swept once, in sample, and never re-chosen. Here they
are re-chosen every month from the past alone, beside the onset lines, on the same walk-forward standard: only troughs
already dated and announced by the cut may inform the choice, no configuration that has closed an episode the committee
never ratified is admitted, and a close published before the trough month has ended is a failure of the same kind as a
false alarm. Two closers the tool has never had are in the grid: the fall in the survey-week insured rate and the fall
in weekly initial claims."""
import sys,pickle
exec(open('walk9.py').read().split('BASE9=dict(BASE)')[0].replace("out=open('walk9_%s_%s.out'%(sys.argv[3],sys.argv[1]),'w')","out=open('walk10_%s_%s.out'%(sys.argv[3],sys.argv[1]),'w')"))
ICW=ICfp.dropna(); LGW=np.log(ICW.rolling(4).mean().dropna())
def close_weekly(drop,pub=5,minw=8):
    out_=[]; hi=None
    for tt,v in LGW.items():
        if hi is None or v>hi[1]: hi=(tt,v)
        if hi is not None and (hi[1]-v)>=drop and (tt-hi[0]).days>=minw*7:
            out_.append((tt+pd.Timedelta(days=pub),pd.Timestamp(tt.year,tt.month,1))); hi=None
    return out_
def close_survey(drop,pub=12):
    out_=[]; hi=None
    for tt,v in SI.items():
        if hi is None or v>hi[1]: hi=(tt,v)
        if hi is not None and (hi[1]-v)>=drop: out_.append((SW[tt]+pd.Timedelta(days=pub),tt)); hi=None
    return out_
CW={}; CS={}
def build10(p):
    r0,turns0=None,None
    TL=dict(TLH)
    if p.get('rdrop'):
        if p['rdrop'] not in CS: CS[p['rdrop']]=close_survey(p['rdrop'])
        TL['R']=CS[p['rdrop']]
    if p.get('qdrop'):
        if p['qdrop'] not in CW: CW[p['qdrop']]=close_weekly(p['qdrop'])
        TL['Q']=CW[p['qdrop']]
    G=vgap2(p['vk'],p['vb']); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=p['vl'],pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,p['u45'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['u45'])
    F25=[x for x in leg_gap_mx2(gm,p['low'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['low'])
    Hc,MX=mkpair3(p['starts'],p['half'],3,p['minw']); Hh=mkhours(p['hrs'],p['nd'])
    SP=dict(name='spread',gap=GSP,line=p['spr'],pub_lag_days=1); C1=[Vc,Hh,SP]; C2=[Hc,SP]
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
    legs={'U':[(a,b) for a,b,c in confirm_w(leg_gapL(spl,p['u45'],p['look'],rearm='zero')+F45,C1,'month')],
          'L':[(a,b) for a,b,c in confirm_w(leg_gapL(spl,p['low'],52,rearm='window')+F25,C2,'month')],
          'X':[(a,b) for a,b,c in hubv(p['sahm'])],'I':[(a,b) for a,b,c in confirm_w(leg_ic(ICfp,p['ic']),C1,'month')]}
    if p.get('wline'): legs['W']=[(a,b) for a,b,c in confirm_w(leg_sv(p['wline'],rearm='zero'),C2,'month')]
    if p.get('wline2'): legs['V']=[(a,b) for a,b,c in confirm_w(leg_sv(p['wline2'],rearm='window'),C2,'month')]
    if p.get('bshare'): legs['B']=[(a,b) for a,b,c in confirm_w(leg_br(p['bshare']),C2,'month')]
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TL)
    return score13(turns),turns
CACHE10={}
def ev10(p):
    k=tuple(sorted((a,str(b)) for a,b in p.items()))
    if k not in CACHE10: CACHE10[k]=build10(p)
    return CACHE10[k]
BASE10=dict(BASE); BASE10['wline']=None; BASE10['wline2']=None; BASE10['bshare']=None; BASE10['rdrop']=None; BASE10['qdrop']=None
ANN={'1948-11':'1949-06-01','1953-07':'1954-08-01','1957-08':'1958-06-01','1960-04':'1961-02-01','1969-12':'1970-08-01',
     '1973-11':'1974-11-01','1980-01':'1980-06-03','1981-07':'1982-01-06','1990-07':'1991-04-25','2001-03':'2001-11-26',
     '2007-12':'2008-12-01','2020-02':'2020-06-08','2024-04':None}
ANNT=[pd.Timestamp(ANN[PK[i].strftime('%Y-%m')]) if ANN[PK[i].strftime('%Y-%m')] else pd.Timestamp('2100-01-01') for i in range(13)]
GRID=[('sahm',[0.50,0.45,0.43,0.40]),('vl',[0.30,0.25,0.20,0.15]),('u45',[0.55,0.45,0.35]),('low',[0.30,0.25,0.20]),
      ('look',[52,78,91,130]),('spr',[1.6,round(LINE,3),1.1]),('ic',[60,50,45]),
      ('wline',[0.40,0.35,0.30,0.25,None]),('wline2',[0.60,0.50,0.45,None]),('bshare',[0.60,0.50,0.40,None]),
      ('rdrop',[1.2,1.0,0.8,0.6,0.5,None]),('qdrop',[0.20,0.15,0.12,0.10,None])]
Y0,Y1,VAR=int(sys.argv[1]),int(sys.argv[2]),sys.argv[3]
def clean(q,cut,ks):
    r,t=ev10(q)
    if [o for o in r['other'] if pd.Timestamp(o[0])<cut]: return None
    if [x for x in t if x['kind']=='peak' and x['published']<pd.Timestamp('1948-06-01')]: return None
    v=[r['lags_p'][j] for j in ks if j in r['lags_p']]
    if len(v)!=len(ks): return None
    tv=[]
    for j in ks:
        cand=[x for x in t if x['kind']=='trough' and TR[j]-pd.DateOffset(months=6)<=x['date']<=TR[j]+pd.DateOffset(months=12) and x['published']<cut]
        if not cand: return None
        lagt=(cand[0]['published']-me(TR[j])).days
        if lagt<0: return None                      # a close published before the trough month ended
        tv.append(lagt)
    for x in t:
        if x['kind']=='trough' and x['published']<cut and not any(TR[j]-pd.DateOffset(months=6)<=x['date']<=TR[j]+pd.DateOffset(months=12) for j in range(13)): return None
    return v,tv
def obj(vt):
    v,tv=vt
    return (sum(1 for x in v if x>31), float(np.median(v)), float(np.mean(v)), float(np.median(tv)), float(np.mean(tv)))
LOG=[]; last=None; CHOSEN={}
for Y in range(Y0,Y1+1):
    for M in range(1,13):
        cut=pd.Timestamp(Y,M,1); ks=[i for i in range(13) if ANNT[i]<cut]
        if not ks: continue
        p=dict(BASE10) if last is None else dict(last)
        for _ in range(2):
            changed=False
            for name,grid in GRID:
                ok={}
                for gv in grid:
                    q=dict(p); q[name]=gv; vt=clean(q,cut,ks)
                    if vt is not None: ok[gv]=obj(vt)
                if not ok: continue
                nv=min(ok,key=lambda gg:(ok[gg],grid.index(gg)))
                if nv!=p[name]: changed=True
                p[name]=nv
            if not changed: break
        last=dict(p); CHOSEN[cut]=dict(p); r,t=ev10(p)
        nxt=cut+pd.DateOffset(months=1)
        for x in t:
            if x['kind'] in ('peak','trough') and cut<=x['published']<nxt:
                LOG.append((x['published'],'OPEN' if x['kind']=='peak' else 'CLOSE',x['date'],x['leg']))
LOG.sort(key=lambda z:z[0])
for pub,kind,dt,leg in LOG: P(f"   {pub:%Y-%m-%d}  {kind:5s} dated {dt:%Y-%m}  by {leg}")
pickle.dump(LOG,open(f'cache/{VAR}_{Y0}.pkl','wb')); pickle.dump(CHOSEN,open(f'cache/{VAR}_chosen_{Y0}.pkl','wb'))
out.close()
