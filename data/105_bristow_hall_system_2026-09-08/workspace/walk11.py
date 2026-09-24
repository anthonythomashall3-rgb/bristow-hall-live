"""THE DEEPEST POINT, TAKEN FROM THE OTHER LINE OF WORK. The route-v16 chat's collection 97 found that a walk-forward
chooser which takes the FASTEST clean configuration picks the edge of a region estimated from almost nothing, and makes
false alarms; while a chooser that takes the DEEPEST clean configuration - the one with the most clean neighbours at
grid distance one - reaches the same speed with none. That is a robustness criterion, it needs no knowledge of the
future, and it is exactly what this line's chooser was missing: today's two failures, the November 2002 call on the wide
grid and the premature closes of the fast closers, are both edge-of-region picks. Here the criterion is imported: the
coordinate descent finds a clean configuration, then the chooser walks to the clean neighbour with the most clean
neighbours of its own, ties broken by the target."""
import sys,pickle
exec(open('walk10.py').read().split('LOG=[]; last=None; CHOSEN={}')[0].replace("out=open('walk10_%s_%s.out'%(sys.argv[3],sys.argv[1]),'w')","out=open('walk11_%s_%s.out'%(sys.argv[3],sys.argv[1]),'w')"))
NAMES=[n for n,_ in GRID]; GD=dict(GRID)
def neighbours(p):
    for n in NAMES:
        gr=GD[n]; i=gr.index(p[n])
        for j in (i-1,i+1):
            if 0<=j<len(gr):
                q=dict(p); q[n]=gr[j]; yield q
def depth(p,cut,ks,memo):
    k=tuple(p[n] for n in NAMES)
    if k in memo: return memo[k]
    d=sum(1 for q in neighbours(p) if clean(q,cut,ks) is not None)
    memo[k]=d; return d
LOG=[]; last=None; CHOSEN={}
for Y in range(Y0,Y1+1):
    for M in range(1,13):
        cut=pd.Timestamp(Y,M,1); ks=[i for i in range(13) if ANNT[i]<cut]
        if not ks: continue
        memo={}
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
        # walk to the deepest clean neighbour: most clean neighbours of its own, ties to the target
        for _ in range(4):
            here=(depth(p,cut,ks,memo),)
            best=None
            for q in neighbours(p):
                vt=clean(q,cut,ks)
                if vt is None: continue
                sc=(-depth(q,cut,ks,memo),obj(vt))
                if best is None or sc<best[0]: best=(sc,q)
            if best is None: break
            if -best[0][0]<=here[0]: break
            p=best[1]
        last=dict(p); CHOSEN[cut]=dict(p); r,t=ev10(p)
        nxt=cut+pd.DateOffset(months=1)
        for x in t:
            if x['kind'] in ('peak','trough') and cut<=x['published']<nxt:
                LOG.append((x['published'],'OPEN' if x['kind']=='peak' else 'CLOSE',x['date'],x['leg']))
LOG.sort(key=lambda z:z[0])
for pub,kind,dt,leg in LOG: P(f"   {pub:%Y-%m-%d}  {kind:5s} dated {dt:%Y-%m}  by {leg}")
pickle.dump(LOG,open(f'cache/{VAR}_{Y0}.pkl','wb')); pickle.dump(CHOSEN,open(f'cache/{VAR}_chosen_{Y0}.pkl','wb'))
out.close()
