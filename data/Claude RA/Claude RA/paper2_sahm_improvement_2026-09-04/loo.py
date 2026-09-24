import core, gen
ALL=core.REC[:]
def mo(s):
    y,m=map(int,s.split('-')[:2]); return y*12+m
def evaluate(a,t,p,require):
    fires=[];streak=0
    for v,m,x in a:
        if x is None: continue
        streak=streak+1 if x>=t-1e-9 else 0
        if streak>=p: fires.append((v,m,x))
    eps=core.episodes(fires)
    core.REC=ALL
    lags,fa=core.score(eps)          # false alarms always judged against ALL recessions
    ok=all(k in lags for k in require)
    return ok,lags,fa
# what sets the floor at 0.46?
a=gen.build(3,6,15,'abs')
for t in (0.40,0.42,0.44,0.45,0.46):
    ok,l,fa=evaluate(a,t,1,[r[0] for r in ALL])
    print(f"thr={t:.2f} detected={len(l)}/10 false={fa}")
print()
print("leave-one-out: config re-picked on 9 recessions, scored on the held-out one")
for i in range(len(ALL)):
    req=[r[0] for j,r in enumerate(ALL) if j!=i]
    best=None
    for kc in (1,2,3):
        for kb in (3,4,6):
            for LL in (9,12,15,18):
                aa=gen.build(kc,kb,LL,'abs')
                t=0.30
                while t<=0.80001:
                    for p in (1,2):
                        ok,l,fa=evaluate(aa,t,p,req)
                        if ok and not fa:
                            g=[l[k] for k in req]
                            key=(sum(g)/len(g),max(g))
                            if best is None or key<best[0]: best=(key,(kc,kb,LL,round(t,2),p),l)
                    t+=0.02
    if best is None: print("  ",ALL[i][0],"no clean config"); continue
    held=ALL[i][0]
    print(f"  held out {held}: picked kc={best[1][0]} kb={best[1][1]} L={best[1][2]} thr={best[1][3]} p={best[1][4]} -> held-out lag {best[2].get(held)}")
