"""THE TRUE WALK-FORWARD TEST — Anthony's standard, exactly. Start in 1949 knowing only 1949. Every January, re-choose
the rule's numbers using ONLY what had been published by then and only recessions the committee had DATED AND ANNOUNCED
by then. Freeze them for the year. Run the tool through that year on data as published. Record every call it makes, in
the order it made them. Move to the next January. Never look forward, ever, for any reason. What comes out is not a
score of the rule — it is the diary the tool would have written."""
import sys
exec(open('causal28.py').read().split('MODE=sys.argv[2]')[0].replace("out=open('causal28_%s.out'%(sys.argv[2] if len(sys.argv)>2 else 'fast'),'w')","out=open('walk1_%s.out'%sys.argv[1],'w')"))
Y0,Y1=int(sys.argv[1]),int(sys.argv[2])
ANN={'1948-11':'1949-06-01','1953-07':'1954-08-01','1957-08':'1958-06-01','1960-04':'1961-02-01','1969-12':'1970-08-01',
     '1973-11':'1974-11-01','1980-01':'1980-06-03','1981-07':'1982-01-06','1990-07':'1991-04-25','2001-03':'2001-11-26',
     '2007-12':'2008-12-01','2020-02':'2020-06-08','2024-04':None}
ANNT=[pd.Timestamp(ANN[PK[i].strftime('%Y-%m')]) if ANN[PK[i].strftime('%Y-%m')] else pd.Timestamp('2100-01-01') for i in range(13)]
def known(cut): return [i for i in range(13) if ANNT[i]<cut]
def score_known(r,ks):
    """mean lag over the recessions ALREADY ANNOUNCED at the cut, and whether every one of them was called"""
    v=[r['lags_p'][j] for j in ks if j in r['lags_p']]
    return (len(v)==len(ks), float(np.mean(v)) if v else 1e9)
GRID=[('sahm',[0.50,0.45,0.43,0.40]),('vl',[0.30,0.25,0.20,0.15]),('u45',[0.55,0.45,0.35]),('low',[0.30,0.25,0.20]),
      ('look',[52,78,91,130]),('spr',[1.6,round(LINE,3),1.1]),('ic',[60,50,45])]
CH={}
def choose_year(cut):
    ks=known(cut)
    if not ks: return None
    key=(len(ks),cut.year//1)
    p=dict(BASE)
    for _ in range(2):
        changed=False
        for name,grid in GRID:
            cands=[]
            for gv in grid:
                q=dict(p); q[name]=gv; r,t=ev(q)
                other=[o for o in r['other'] if pd.Timestamp(o[0])<cut]
                early=[x for x in t if x['kind']=='peak' and x['published']<pd.Timestamp('1948-06-01')]
                allc,pm=score_known(r,ks)
                if allc and not other and not early: cands.append((gv,pm))
            if cands:
                nv=min(cands,key=lambda c:(c[1],grid.index(c[0])))[0]
                if nv!=p[name]: changed=True
                p[name]=nv
        if not changed: break
    return p
LOG=[]
for Y in range(Y0,Y1+1):
    cut=pd.Timestamp(Y,1,1); p=choose_year(cut)
    if p is None: continue
    r,t=ev(p)
    calls=[x for x in t if x['kind']=='peak' and cut<=x['published']<pd.Timestamp(Y+1,1,1)]
    ends=[x for x in t if x['kind']=='trough' and cut<=x['published']<pd.Timestamp(Y+1,1,1)]
    for c in calls: LOG.append((c['published'],'OPEN',c['date'],c['leg'],dict(p)))
    for c in ends: LOG.append((c['published'],'CLOSE',c['date'],c['leg'],dict(p)))
LOG.sort(key=lambda x:x[0])
P(f"THE DIARY, {Y0}-{Y1} — every call the tool would have made, in the order it made them")
for pub,kind,dt,leg,p in LOG:
    P(f"   {pub:%Y-%m-%d}  {kind:5s} dated {dt:%Y-%m}  by {leg}")
import pickle; pickle.dump(LOG,open(f'cache/walk1_{Y0}.pkl','wb'))
P(f"\n   {len(LOG)} entries")
out.close()
