"""WHY THE WALK KEEPS THE SAFE RUN LENGTHS. At two cuts - January 1983 and January 2025 - the chosen configuration
is taken and the three run lengths are varied one at a time. For each value: whether it is clean on the ratified
record, and what the objective is. This says whether a faster closer was REFUSED on evidence or simply could not be
distinguished, which are different things and only one of them is a limit of the tool."""
import sys,pickle,os
sys.argv=['x','1962','2026','w26']
src=open('walk26.py').read().split('Y0,Y1,VAR=')[0].replace("out=open('walk26_%s.out'%sys.argv[1],'w')","out=open('w26diag.out','w')")
exec(src)
GRID=[(n,([x for x in g if x is not None]+[None]) if n in ('wline','wline2','bshare') else g) for n,g in GRID]
GD=dict(GRID)
CH=pickle.load(open('cache/w26_chosen_2011.pkl','rb'))
CH.update(pickle.load(open('cache/w26_chosen_1976.pkl','rb')))
for Ycut in (1983,2025):
    cut=pd.Timestamp(Ycut,1,1)
    ks=[i for i in range(13) if ANNT[i]<cut]; kt=[i for i in range(13) if TANNT[i]<cut]
    p=CH.get(cut)
    if p is None: P(f"\ncut {Ycut}: no chosen point saved"); continue
    P(f"\ncut {Ycut}-01-01   peaks ratified {len(ks)}   troughs ratified {kt} = {[TR[i].strftime('%Y-%m') for i in kt]}")
    P(f"   chosen: rst={p['rst']} tst={p['tst']} qst={p['qst']}")
    base=clean(p,cut,ks,kt)
    P(f"   objective at the chosen point: {obj(base) if base else 'NOT CLEAN'}")
    for nm in ('rst','tst','qst'):
        for gv in GD[nm]:
            q=dict(p); q[nm]=gv; v=clean(q,cut,ks,kt)
            if v is None:
                s=summary(q); why=[]
                for i in kt:
                    if i not in s['pair']: why.append(f"{TR[i]:%Y-%m} never closed")
                    else:
                        pub_,lg,er=s['pair'][i]
                        if lg<0: why.append(f"{TR[i]:%Y-%m} PREMATURE {lg}")
                        elif abs(er)>1: why.append(f"{TR[i]:%Y-%m} dated {er:+d} months out")
                if s['early']: why.append('a call before June 1948')
                if [o for o in s['fa'] if o<cut]: why.append('a false alarm')
                vv=[s['lags'][j] for j in ks if j in s['lags']]
                if len(vv)!=len(ks): why.append('a recession missed')
                P(f"   {nm}={gv}: NOT CLEAN — {'; '.join(why) if why else 'peak side'}")
            else:
                P(f"   {nm}={gv}: clean, objective {obj(v)}  trough lags {v[1]}")
out.close()
