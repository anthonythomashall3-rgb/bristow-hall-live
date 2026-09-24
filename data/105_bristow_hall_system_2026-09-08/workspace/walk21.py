"""THE THREE SLOW EARLY TURNS. 1953 at +62, 1957 at +122 and 1960 at +91. First, which side binds each of them under
v3.8. Second, the 1957 regression: it was +5 at a vacancy line of 0.20 and +122 at 0.25, and the only reason the line
was raised was to remove a single call in December 2025 that fires on a vacancy reading of exactly 0.200 in May 2025 -
six months before the Sahm month it confirms. A shorter confirmation window kills that call without touching the line."""
import sys,pickle,os
exec(open('walk9.py').read().split('BASE9=dict(BASE)')[0].replace("out=open('walk9_%s_%s.out'%(sys.argv[3],sys.argv[1]),'w')","out=open('walk21_%s.out'%sys.argv[1],'w')"))
def build_v(p):
    G=vgap2(p['vk'],p['vb']); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=p['vl'],pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,p['u45'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['u45'])
    F25=[x for x in leg_gap_mx2(gm,p['low'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['low'])
    Hc,MX=mkpair3(p['starts'],p['half'],3,p['minw']); Hc=dict(Hc); Hc['line']=p['hline']; Hh=mkhours(p['hrs'],p['nd'])
    SP=dict(name='spread',gap=GSP,line=p['spr'],pub_lag_days=1)
    def hubv(sl,back):
        calls=[]; armed=True
        for m,v in g.items():
            if m<pd.Timestamp('1948-06-01'): continue
            if armed and v>=sl:
                w=G[(G.index>=m-pd.DateOffset(months=back))&(G.index<=m)]; hit=w[w>=p['vl']]
                # a line touched in one month is not a confirmation: the vacancy must hold its line for two months
                if len(hit)>=2:
                    kk=hit.index[1]; sp=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
                    calls.append((max(sp,pubs[kk]),m-pd.DateOffset(months=3),'hub')); armed=False
            elif not armed and v<sl: armed=True
        return calls
    C1=[Vc,Hh,SP]; C2=[Hc,SP]
    legs={'U':[(a,b) for a,b,c in confirm_w(leg_gapL(spl,p['u45'],p['look'],rearm='zero')+F45,C1,'month')],
          'L':[(a,b) for a,b,c in confirm_w(leg_gapL(spl,p['low'],52,rearm='window')+F25,C2,'month')],
          'X':[(a,b) for a,b,c in hubv(p['sahm'],p['hback'])],'I':[(a,b) for a,b,c in confirm_w(leg_ic(ICfp,p['ic']),C1,'month')]}
    if p.get('wline'): legs['W']=[(a,b) for a,b,c in confirm_w(leg_sv(p['wline'],rearm='zero'),C2,'month')]
    if p.get('wline2'): legs['V']=[(a,b) for a,b,c in confirm_w(leg_sv(p['wline2'],rearm='window'),C2,'month')]
    if p.get('bshare'): legs['B']=[(a,b) for a,b,c in confirm_w(leg_br(p['bshare']),C2,'month')]
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TLH)
    return score13(turns),turns

# ---- S REBUILT: Paper 1's closer proposes, two objects confirm the labour market has turned ----
sys.path.insert(0,W+'/lab/slack')
_CL=ICfp.dropna().rolling(4).mean().dropna(); _LCL=np.log(_CL); _BELOW=(_LCL.rolling(52,min_periods=26).max()-_LCL).dropna()
_LH=lh.dropna(); _AW=AWH.dropna()
def _rl(ser,look=12): return ((ser/ser.rolling(look,min_periods=look).min()-1)*100).dropna()
_RS=_rl(_LH); _RH=_rl(_AW)
def _confirm_close(calls,cdrop=0.15,rise=2.0,need=2,fwd=6):
    out_=[]
    for pp,dd in calls:
        hits=[]
        seg=_BELOW[(_BELOW.index>=dd)&(_BELOW.index<=dd+pd.DateOffset(months=fwd))]
        h=seg[seg>=cdrop]
        if len(h): hits.append(h.index[0]+pd.Timedelta(days=5))
        for rl_,pdy in [(_RS,18),(_RH,5)]:
            s2=rl_[(rl_.index>=dd)&(rl_.index<=dd+pd.DateOffset(months=fwd))]; h2=s2[s2>=rise]
            if len(h2): hits.append(pd.Timestamp(h2.index[0].year,h2.index[0].month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=pdy-1))
        if len(hits)>=need:
            hits.sort(); out_.append((max(pp,hits[need-1]),dd))
    return out_
TLH=dict(TLH); TLH['S']=_confirm_close(TLH['S'])
BASE15=dict(BASE); BASE15.update(deep=999,wline=None,wline2=None,bshare=None,hline=1.00,spr=round(LINE,3),sahm=0.43,vl=0.20,hback=6)
GRID=[('sahm',[0.55,0.50,0.45,0.43,0.40,0.3667,0.35]),('vl',[0.36,0.30,0.25,0.20,0.15,0.12]),('hline',[1.10,1.00,0.95,0.90,0.85,0.80]),
      ('spr',[1.9,1.6,round(LINE,3),1.1,0.9]),('hback',[12,9,6,5,4,3]),('u45',[0.70,0.55,0.45,0.35,0.30]),('low',[0.35,0.30,0.25,0.20,0.15]),
      ('look',[52,78,91,130]),('ic',[60,50,45]),
      ('wline',[0.40,0.35,0.30,0.25,None]),('wline2',[0.60,0.50,0.45,None]),('bshare',[0.60,0.50,0.40,None])]
NAMES=[n for n,_ in GRID]; GD=dict(GRID)
ANN={'1948-11':'1949-06-01','1953-07':'1954-08-01','1957-08':'1958-06-01','1960-04':'1961-02-01','1969-12':'1970-08-01',
     '1973-11':'1974-11-01','1980-01':'1980-06-03','1981-07':'1982-01-06','1990-07':'1991-04-25','2001-03':'2001-11-26',
     '2007-12':'2008-12-01','2020-02':'2020-06-08','2024-04':None}
ANNT=[pd.Timestamp(ANN[PK[i].strftime('%Y-%m')]) if ANN[PK[i].strftime('%Y-%m')] else pd.Timestamp('2100-01-01') for i in range(13)]
SUMF='cache/w21_sum.pkl'; SUM=pickle.load(open(SUMF,'rb')) if os.path.exists(SUMF) else {}
def summary(p):
    k=tuple(p[n] for n in NAMES)
    if k in SUM: return SUM[k]
    r,t=build_v(p)
    s={'lags':dict(r['lags_p']),'early':bool([x for x in t if x['kind']=='peak' and x['published']<pd.Timestamp('1948-06-01')]),
       'fa':[x['published'] for x in t if x['kind']=='peak' and x['published'].strftime('%Y-%m-%d') in [d for d,_,_ in r['other']]
             and not any(pk-pd.DateOffset(months=6)<=x['date']<=tr for pk,tr in zip(PK,TR))],
       'tro':{},'opens':{i:r['opens'][i]['published'] for i in r['opens']}}
    for i in range(13):
        c=[x for x in t if x['kind']=='trough' and TR[i]-pd.DateOffset(months=6)<=x['date']<=TR[i]+pd.DateOffset(months=12)]
        if c: s['tro'][i]=(c[0]['published'],(c[0]['published']-me(TR[i])).days)
    SUM[k]=s
    if len(SUM)%100==0: pickle.dump(SUM,open(SUMF,'wb'))
    return s
def clean(q,cut,ks):
    s=summary(q)
    if s['early'] or [o for o in s['fa'] if o<cut]: return None
    v=[s['lags'][j] for j in ks if j in s['lags']]
    if len(v)!=len(ks): return None
    return v
def obj(v): return (sum(1 for x in v if x>31), float(np.median(v)), float(np.mean(v)))
def neighbours(p):
    for n in NAMES:
        gr=GD[n]; i=gr.index(p[n])
        for j in (i-1,i+1):
            if 0<=j<len(gr): q=dict(p); q[n]=gr[j]; yield q
Y0,Y1,VAR=int(sys.argv[1]),int(sys.argv[2]),sys.argv[3]
GRID=[(n,([x for x in g if x is not None]+[None]) if n in ('wline','wline2','bshare') else g) for n,g in GRID]
GD=dict(GRID)
CF=f'cache/{VAR}_carry.pkl'; last=pickle.load(open(CF,'rb')) if os.path.exists(CF) else None
LOG=[]; CHOSEN={}
for Y in range(Y0,Y1+1):
    cut=pd.Timestamp(Y,1,1); ks=[i for i in range(13) if ANNT[i]<cut]
    if not ks: continue
    memo={}
    def depth(p):
        k=tuple(p[n] for n in NAMES)
        if k in memo: return memo[k]
        d=sum(1 for q in neighbours(p) if clean(q,cut,ks) is not None); memo[k]=d; return d
    p=dict(BASE15) if last is None else dict(last)
    for _ in range(2):
        ch=False
        for name,grid in GRID:
            ok={}
            for gv in grid:
                q=dict(p); q[name]=gv; v=clean(q,cut,ks)
                if v is not None: ok[gv]=obj(v)
            if not ok: continue
            # A CONFIRMER CANNOT CAUSE A CALL BY ITSELF. It only speeds a call a proposer has already made, so where
            # two lines leave the past record identical the LOOSER one is taken for a confirmer and the SAFER one for
            # a proposer. Declared before the run.
            best=min(ok.values())
            tied=[gg for gg in ok if ok[gg]==best]
            if name in ('hline','spr','vl'): nv=max(tied,key=lambda gg:grid.index(gg))
            else: nv=min(tied,key=lambda gg:grid.index(gg))
            if nv!=p[name]: ch=True
            p[name]=nv
        if not ch: break
    if clean(p,cut,ks) is None: continue
    here=depth(p); best=None
    for q in neighbours(p):
        v=clean(q,cut,ks)
        if v is None: continue
        sc=(-depth(q),obj(v))
        if best is None or sc<best[0]: best=(sc,q)
    if best is not None and -best[0][0]>here: p=best[1]
    last=dict(p); CHOSEN[cut]=dict(p); r,t=build_v(p)
    for x in t:
        if x['kind'] in ('peak','trough') and cut<=x['published']<pd.Timestamp(Y+1,1,1):
            LOG.append((x['published'],'OPEN' if x['kind']=='peak' else 'CLOSE',x['date'],x['leg']))
LOG.sort(key=lambda z:z[0])
for pub,kind,dt,leg in LOG: P(f"   {pub:%Y-%m-%d}  {kind:5s} dated {dt:%Y-%m}  by {leg}")
pickle.dump(SUM,open(SUMF,'wb')); pickle.dump(LOG,open(f'cache/{VAR}_{Y0}.pkl','wb'))
pickle.dump(CHOSEN,open(f'cache/{VAR}_chosen_{Y0}.pkl','wb'))
if last is not None: pickle.dump(last,open(CF,'wb'))
P(f"   summaries {len(SUM)}")
out.close()
