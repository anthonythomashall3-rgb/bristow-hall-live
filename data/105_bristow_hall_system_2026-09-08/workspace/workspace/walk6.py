"""THE CHOOSER AIMED AT THE TARGET, AND MADE TO STAND ON THE INTERIOR OF THE PLATEAU. Two further changes to the
walk-forward test, both causal. First, the chooser no longer minimises the mean lag: it minimises, in order, the number
of past recessions called more than a month after the peak month ended, then the median lag, then the mean. That is the
target stated for the tool. Second, a candidate is admitted only if its neighbours one grid step either way are also
clean on the past, so the chooser stands on the interior of a clean plateau rather than its edge."""
import sys,pickle
exec(open('walk3.py').read().split('CACHE6={}')[0].replace("out=open('walk3_%s.out'%sys.argv[1],'w')","out=open('walk6_%s_%s.out'%(sys.argv[3],sys.argv[1]),'w')"))
CACHE6={}
def ev6(p):
    k=tuple(sorted(p.items()))
    if k not in CACHE6: CACHE6[k]=build6(p)
    return CACHE6[k]
BASE6=dict(BASE); BASE6['deep']=7.5
ANN={'1948-11':'1949-06-01','1953-07':'1954-08-01','1957-08':'1958-06-01','1960-04':'1961-02-01','1969-12':'1970-08-01',
     '1973-11':'1974-11-01','1980-01':'1980-06-03','1981-07':'1982-01-06','1990-07':'1991-04-25','2001-03':'2001-11-26',
     '2007-12':'2008-12-01','2020-02':'2020-06-08','2024-04':None}
ANNT=[pd.Timestamp(ANN[PK[i].strftime('%Y-%m')]) if ANN[PK[i].strftime('%Y-%m')] else pd.Timestamp('2100-01-01') for i in range(13)]
WIDE=[('sahm',[0.50,0.47,0.45,0.43,0.40]),('vl',[0.30,0.25,0.20,0.15]),('u45',[0.55,0.45,0.35]),('low',[0.30,0.25,0.20,0.15]),
      ('look',[52,78,91,130,182]),('spr',[1.6,round(LINE,3),1.1]),('ic',[60,50,45]),('deep',[15,10,7.5,5]),
      ('starts',[35,29,25]),('half',[5,4,3]),('minw',[12,18,24])]
NARROW=[('sahm',[0.50,0.45,0.43,0.40]),('vl',[0.30,0.25,0.20,0.15]),('u45',[0.55,0.45,0.35]),('low',[0.30,0.25,0.20]),
        ('look',[52,78,91,130]),('spr',[1.6,round(LINE,3),1.1]),('ic',[60,50,45])]
Y0,Y1,VAR=int(sys.argv[1]),int(sys.argv[2]),sys.argv[3]
GRID=NARROW if 'narrow' in VAR else WIDE
if 'mid' in VAR: GRID=[g for g in GRID if g[0] not in ('starts','half','minw')]
if 'nodeep' in VAR: GRID=[g for g in GRID if g[0]!='deep']
if 'plusdeep' in VAR and not [g for g in GRID if g[0]=='deep']: GRID=GRID+[('deep',[15,10,7.5,5])]
DROP={'lownarrow':('low',0.15),'sahmnarrow':('sahm',0.47),'looknarrow':('look',182)}
for tok,(nm,val) in DROP.items():
    if tok in VAR: GRID=[(n,[x for x in g if x!=val]) if n==nm else (n,g) for n,g in GRID]
TARGET='target' in VAR
PLAT='plateau' in VAR
def clean(q,cut,ks):
    """is this configuration clean on everything published before the cut, and does it call every announced recession?"""
    r,t=ev6(q)
    if [o for o in r['other'] if pd.Timestamp(o[0])<cut]: return None
    if [x for x in t if x['kind']=='peak' and x['published']<pd.Timestamp('1948-06-01')]: return None
    v=[r['lags_p'][j] for j in ks if j in r['lags_p']]
    if len(v)!=len(ks): return None
    return v
def obj(v):
    if TARGET: return (sum(1 for x in v if x>31), float(np.median(v)), float(np.mean(v)))
    return (float(np.mean(v)),)
LOG=[]; last=None
for Y in range(Y0,Y1+1):
    for M in range(1,13):
        cut=pd.Timestamp(Y,M,1); ks=[i for i in range(13) if ANNT[i]<cut]
        if not ks: continue
        p=dict(BASE6) if last is None else dict(last)
        for _ in range(2):
            changed=False
            for name,grid in GRID:
                ok={}
                for gv in grid:
                    q=dict(p); q[name]=gv; v=clean(q,cut,ks)
                    if v is not None: ok[gv]=obj(v)
                if not ok: continue
                cands=list(ok)
                if PLAT:
                    interior=[]
                    for gv in cands:
                        i=grid.index(gv); nb=[grid[j] for j in (i-1,i+1) if 0<=j<len(grid)]
                        if all(x in ok for x in nb): interior.append(gv)
                    if interior: cands=interior
                nv=min(cands,key=lambda g:(ok[g],grid.index(g)))
                if nv!=p[name]: changed=True
                p[name]=nv
            if not changed: break
        last=dict(p); r,t=ev6(p)
        nxt=cut+pd.DateOffset(months=1)
        for x in t:
            if x['kind'] in ('peak','trough') and cut<=x['published']<nxt:
                LOG.append((x['published'],'OPEN' if x['kind']=='peak' else 'CLOSE',x['date'],x['leg']))
LOG.sort(key=lambda z:z[0])
for pub,kind,dt,leg in LOG: P(f"   {pub:%Y-%m-%d}  {kind:5s} dated {dt:%Y-%m}  by {leg}")
pickle.dump(LOG,open(f'cache/{VAR}_{Y0}.pkl','wb'))
out.close()
