"""THE DIARY RE-CHOSEN EVERY MONTH, AND ON A WIDER GRID. Two improvements to the walk-forward test, both of which use
only past information and are therefore legitimate under Rule 22: the numbers are re-chosen EVERY MONTH rather than
every January, so the tool adapts as soon as a new fact arrives; and the grid the chooser searches is widened, with the
claims deep branch (initial claims 7.5-15 per cent needing two demand objects) added as a candidate."""
import sys
exec(open('walk3.py').read().split('CACHE6={}')[0].replace("out=open('walk3_%s.out'%sys.argv[1],'w')","out=open('walk5_%s.out'%sys.argv[1],'w')"))
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
GRID=[('sahm',[0.50,0.47,0.45,0.43,0.40]),('vl',[0.30,0.25,0.20,0.15]),('u45',[0.55,0.45,0.35]),('low',[0.30,0.25,0.20,0.15]),
      ('look',[52,78,91,130,182]),('spr',[1.6,round(LINE,3),1.1]),('ic',[60,50,45]),('deep',[15,10,7.5,5]),
      ('starts',[35,29,25]),('half',[5,4,3]),('minw',[12,18,24])]
Y0,Y1=int(sys.argv[1]),int(sys.argv[2])
LOG=[]; last=None
for Y in range(Y0,Y1+1):
    for M in range(1,13):
        cut=pd.Timestamp(Y,M,1); ks=[i for i in range(13) if ANNT[i]<cut]
        if not ks: continue
        p=dict(BASE6) if last is None else dict(last)
        for _ in range(2):
            changed=False
            for name,grid in GRID:
                cands=[]
                for gv in grid:
                    q=dict(p); q[name]=gv; r,t=ev6(q)
                    other=[o for o in r['other'] if pd.Timestamp(o[0])<cut]
                    early=[x for x in t if x['kind']=='peak' and x['published']<pd.Timestamp('1948-06-01')]
                    v=[r['lags_p'][j] for j in ks if j in r['lags_p']]
                    if len(v)==len(ks) and not other and not early: cands.append((gv,float(np.mean(v))))
                if cands:
                    nv=min(cands,key=lambda c:(c[1],grid.index(c[0])))[0]
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
import pickle; pickle.dump(LOG,open(f'cache/walk5_{Y0}.pkl','wb'))
out.close()
