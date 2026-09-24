"""THE DEEPEST POINT, WITH A DISK-BACKED SUMMARY CACHE. Same criterion as walk11; the only difference is that each
configuration's record is reduced once to a compact summary - peak lags and publication dates, other calls, trough
matches - and kept on disk, so the neighbour counting the deepest criterion needs can be done at all."""
import sys,pickle,os
exec(open('walk10.py').read().split('LOG=[]; last=None; CHOSEN={}')[0].replace("out=open('walk10_%s_%s.out'%(sys.argv[3],sys.argv[1]),'w')","out=open('walk12_%s_%s.out'%(sys.argv[3],sys.argv[1]),'w')"))
NAMES=[n for n,_ in GRID]; GD=dict(GRID)
SUMF='cache/w12_summaries.pkl'
SUM=pickle.load(open(SUMF,'rb')) if os.path.exists(SUMF) else {}
def summary(p):
    k=tuple(p[n] for n in NAMES)
    if k in SUM: return SUM[k]
    r,t=build10(p)
    s={'lags':dict(r['lags_p']),'pubs':{i:r['opens'][i]['published'] for i in r['opens']},
       'other':[pd.Timestamp(o[0]) for o in r['other']],
       'early':[x['published'] for x in t if x['kind']=='peak' and x['published']<pd.Timestamp('1948-06-01')],
       'tro':{},'tother':[]}
    for i in range(13):
        c=[x for x in t if x['kind']=='trough' and TR[i]-pd.DateOffset(months=6)<=x['date']<=TR[i]+pd.DateOffset(months=12)]
        if c: s['tro'][i]=(c[0]['published'],(c[0]['published']-me(TR[i])).days)
    for x in t:
        if x['kind']=='trough' and not any(TR[i]-pd.DateOffset(months=6)<=x['date']<=TR[i]+pd.DateOffset(months=12) for i in range(13)):
            s['tother'].append(x['published'])
    SUM[k]=s
    if len(SUM)%50==0: pickle.dump(SUM,open(SUMF,'wb'))
    return s
def clean(q,cut,ks):
    s=summary(q)
    if [o for o in s['other'] if o<cut]: return None
    if s['early']: return None
    v=[s['lags'][j] for j in ks if j in s['lags']]
    if len(v)!=len(ks): return None
    tv=[]
    for j in ks:
        if j not in s['tro']: return None
        pub,lagt=s['tro'][j]
        if pub>=cut: return None
        if lagt<0: return None
        tv.append(lagt)
    if [o for o in s['tother'] if o<cut]: return None
    return v,tv
def obj(vt):
    v,tv=vt
    return (sum(1 for x in v if x>31), float(np.median(v)), float(np.mean(v)), float(np.median(tv)), float(np.mean(tv)))
def neighbours(p):
    for n in NAMES:
        gr=GD[n]; i=gr.index(p[n])
        for j in (i-1,i+1):
            if 0<=j<len(gr):
                q=dict(p); q[n]=gr[j]; yield q
LOG=[]; last=None; CHOSEN={}
CH=pickle.load(open(f'cache/{sys.argv[3]}_carry.pkl','rb')) if os.path.exists(f'cache/{sys.argv[3]}_carry.pkl') else None
last=CH
for Y in range(Y0,Y1+1):
    for M in range(1,13):
        cut=pd.Timestamp(Y,M,1); ks=[i for i in range(13) if ANNT[i]<cut]
        if not ks: continue
        memo={}
        def depth(p):
            k=tuple(p[n] for n in NAMES)
            if k in memo: return memo[k]
            d=sum(1 for q in neighbours(p) if clean(q,cut,ks) is not None); memo[k]=d; return d
        p=dict(BASE10) if last is None else dict(last)
        if clean(p,cut,ks) is None:
            for _ in range(2):
                ch=False
                for name,grid in GRID:
                    ok={}
                    for gv in grid:
                        q=dict(p); q[name]=gv; vt=clean(q,cut,ks)
                        if vt is not None: ok[gv]=obj(vt)
                    if not ok: continue
                    nv=min(ok,key=lambda gg:(ok[gg],grid.index(gg)))
                    if nv!=p[name]: ch=True
                    p[name]=nv
                if not ch: break
        if clean(p,cut,ks) is None: continue
        for _ in range(4):
            here=depth(p); best=None
            for q in neighbours(p):
                vt=clean(q,cut,ks)
                if vt is None: continue
                sc=(-depth(q),obj(vt))
                if best is None or sc<best[0]: best=(sc,q)
            if best is None or -best[0][0]<=here: break
            p=best[1]
        last=dict(p); CHOSEN[cut]=dict(p); s=summary(p)
        nxt=cut+pd.DateOffset(months=1)
        r,t=build10(p)
        for x in t:
            if x['kind'] in ('peak','trough') and cut<=x['published']<nxt:
                LOG.append((x['published'],'OPEN' if x['kind']=='peak' else 'CLOSE',x['date'],x['leg']))
LOG.sort(key=lambda z:z[0])
for pub,kind,dt,leg in LOG: P(f"   {pub:%Y-%m-%d}  {kind:5s} dated {dt:%Y-%m}  by {leg}")
pickle.dump(SUM,open(SUMF,'wb'))
pickle.dump(LOG,open(f'cache/{VAR}_{Y0}.pkl','wb')); pickle.dump(CHOSEN,open(f'cache/{VAR}_chosen_{Y0}.pkl','wb'))
if last is not None: pickle.dump(last,open(f'cache/{VAR}_carry.pkl','wb'))
P(f"   summaries cached: {len(SUM)}")
out.close()
