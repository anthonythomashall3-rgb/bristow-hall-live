"""THE DEEPEST POINT, BOTH SIDES, WITH THE TROUGH CONJUNCTION IN THE GRID. The closer built today - weekly claims
falling proposes the close, TWO demand objects each five per cent above their own twelve-month low confirm it - is put
in the grid beside the onset lines and left to the deepest-point chooser. A close published before its trough month
ended, or outside every trough window, is a hard veto, as a false alarm is on the onset side.

THE DEEPEST POINT ON THE ONSET SIDE, ANNUAL RE-CHOICE. The closers are held at the set the other line of work has
already walked forward successfully (H, K, S), because this line's own test today showed the two fast closers close
before the trough. The onset lines are re-chosen every January from the past alone, first by coordinate descent to a
clean configuration and then by one move to the clean neighbour with the most clean neighbours of its own - the
deepest-point criterion imported from the route-v16 line."""
import sys,pickle,os
exec(open('walk9.py').read().split('BASE9=dict(BASE)')[0].replace("out=open('walk9_%s_%s.out'%(sys.argv[3],sys.argv[1]),'w')","out=open('walk14_%s_%s.out'%(sys.argv[3],sys.argv[1]),'w')"))
sys.path.insert(0,W+'/lab/slack')
LH=lh.dropna(); AW=AWH.dropna(); VR=(-_vload()['-vacancy rate']).dropna()
VPUB=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in VR.index})
def _rel(ser,look=12): return ((ser/ser.rolling(look,min_periods=look).min()-1)*100).dropna()
RECOV=[('housing starts',_rel(LH),lambda m: pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=17)),
       ('weekly hours',_rel(AW),lambda m: pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4)),
       ('vacancy rate',_rel(VR),lambda m: VPUB[m] if m in VPUB.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=2))]
LGW=np.log(ICfp.dropna().rolling(4).mean().dropna())
QC={}
def closer_Q(drop,pct=5.0,nmin=2,pub=5,minw=8,fwd=6):
    if drop in QC: return QC[drop]
    prop=[]; hi=None
    for tt,v in LGW.items():
        if hi is None or v>hi[1]: hi=(tt,v)
        if hi is not None and (hi[1]-v)>=drop and (tt-hi[0]).days>=minw*7:
            seg=LGW[(LGW.index>=hi[0])&(LGW.index<=tt)]; lo=seg.idxmin()
            prop.append((tt+pd.Timedelta(days=pub),pd.Timestamp(lo.year,lo.month,1))); hi=None
    outc=[]
    for pp,dd in prop:
        hits=[]
        for nm,rl,pf in RECOV:
            seg=rl[(rl.index>=dd)&(rl.index<=dd+pd.DateOffset(months=fwd))]; h=seg[seg>=pct]
            if len(h): hits.append(pf(h.index[0]))
        if len(hits)>=nmin:
            hits.sort(); outc.append((max(pp,hits[nmin-1]),dd))
    QC[drop]=outc; return outc
BASE13=dict(BASE); BASE13['deep']=15; BASE13['wline']=None; BASE13['wline2']=None; BASE13['bshare']=None; BASE13['qdrop']=None
GRID=[('sahm',[0.50,0.45,0.43,0.40]),('vl',[0.30,0.25,0.20,0.15]),('u45',[0.55,0.45,0.35]),('low',[0.30,0.25,0.20]),
      ('look',[52,78,91,130]),('spr',[1.6,round(LINE,3),1.1]),('ic',[60,50,45]),
      ('wline',[0.40,0.35,0.30,0.25,None]),('wline2',[0.60,0.50,0.45,None]),('bshare',[0.60,0.50,0.40,None]),
      ('qdrop',[0.15,0.12,0.10,None])]
NAMES=[n for n,_ in GRID]; GD=dict(GRID)
ANN={'1948-11':'1949-06-01','1953-07':'1954-08-01','1957-08':'1958-06-01','1960-04':'1961-02-01','1969-12':'1970-08-01',
     '1973-11':'1974-11-01','1980-01':'1980-06-03','1981-07':'1982-01-06','1990-07':'1991-04-25','2001-03':'2001-11-26',
     '2007-12':'2008-12-01','2020-02':'2020-06-08','2024-04':None}
ANNT=[pd.Timestamp(ANN[PK[i].strftime('%Y-%m')]) if ANN[PK[i].strftime('%Y-%m')] else pd.Timestamp('2100-01-01') for i in range(13)]
SUMF='cache/w14_sum.pkl'; SUM=pickle.load(open(SUMF,'rb')) if os.path.exists(SUMF) else {}
_B9=build9
def build9x(p,TL):
    import types
    global TLH
    old=TLH; TLH=TL
    try: return _B9(p)
    finally: TLH=old
def summary(p):
    k=tuple(p[n] for n in NAMES)
    if k in SUM: return SUM[k]
    TLx=dict(TLH)
    if p.get('qdrop'): TLx['Q']=closer_Q(p['qdrop'])
    r,t=build9x(p,TLx)
    s={'lags':dict(r['lags_p']),'other':[pd.Timestamp(o[0]) for o in r['other']],
       'early':bool([x for x in t if x['kind']=='peak' and x['published']<pd.Timestamp('1948-06-01')]),
       'tro':{},'tother':[]}
    for i in range(13):
        c=[x for x in t if x['kind']=='trough' and TR[i]-pd.DateOffset(months=6)<=x['date']<=TR[i]+pd.DateOffset(months=12)]
        if c: s['tro'][i]=(c[0]['published'],(c[0]['published']-me(TR[i])).days,(c[0]['date'].year-TR[i].year)*12+c[0]['date'].month-TR[i].month,c[0]['leg'])
    s['tother']=[x['published'] for x in t if x['kind']=='trough' and not any(TR[i]-pd.DateOffset(months=6)<=x['date']<=TR[i]+pd.DateOffset(months=12) for i in range(13))]
    SUM[k]=s
    if len(SUM)%100==0: pickle.dump(SUM,open(SUMF,'wb'))
    return s
def clean(q,cut,ks):
    s=summary(q)
    if s['early'] or [o for o in s['other'] if o<cut]: return None
    v=[s['lags'][j] for j in ks if j in s['lags']]
    if len(v)!=len(ks): return None
    if [o for o in s.get('tother',[]) if o<cut]: return None
    tv=[]
    for j in ks:
        if j not in s['tro']: return None
        pub,lagt,errt,leg=s['tro'][j]
        if pub>=cut: return None
        if lagt<0: return None
        tv.append(lagt)
    return (v,tv)
def obj(vt):
    v,tv=vt
    return (sum(1 for x in v if x>31), float(np.median(v)), float(np.mean(v)), float(np.median(tv)), float(np.mean(tv)))
def neighbours(p):
    for n in NAMES:
        gr=GD[n]; i=gr.index(p[n])
        for j in (i-1,i+1):
            if 0<=j<len(gr): q=dict(p); q[n]=gr[j]; yield q
Y0,Y1,VAR=int(sys.argv[1]),int(sys.argv[2]),sys.argv[3]
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
    p=dict(BASE13) if last is None else dict(last)
    for _ in range(2):
        ch=False
        for name,grid in GRID:
            ok={}
            for gv in grid:
                q=dict(p); q[name]=gv; v=clean(q,cut,ks)
                if v is not None: ok[gv]=obj(v)
            if not ok: continue
            nv=min(ok,key=lambda gg:(ok[gg],grid.index(gg)))
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
    last=dict(p); CHOSEN[cut]=dict(p); r,t=build9(p)
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
