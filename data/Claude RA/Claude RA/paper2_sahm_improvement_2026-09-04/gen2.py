import core, gen, itertools
print("=== ASYMMETRIC MA: current kc-month MA vs min of prior L kb-month MAs ===")
best=[]
for kc in (1,2,3):
    for kb in (3,4,6):
        for L in (9,12,15,18):
            arr=gen.build(kc,kb,L,'abs')
            for z in gen.scan(arr,0.30,0.80,0.01):
                best.append((kc,kb,L)+z)
best.sort(key=lambda z:(z[5],z[6]))
for b in best[:10]:
    print(f"  kc={b[0]} kb={b[1]} L={b[2]} thr={b[3]:.2f} p={b[4]} med={b[5]} mean={b[6]} max={b[7]} {b[8]}")
print("  clean configs:",len(best))
print()
print("=== TWO-CONDITION, SAME SERIES: S>=hi  OR  (S>=lo AND u rose >=d in each of last m prints) ===")
S=[(v,s) for v,s in ((core.VIN[j],core.series(j)) for j in range(len(core.VIN))) if s]
def run2(hi,lo,d,m):
    fires=[]
    for v,s in S:
        x=core.indicator(s,3,12)
        if x is None: continue
        rises=all(s[-i][1]-s[-i-1][1]>=d-1e-9 for i in range(1,m+1)) if len(s)>m+1 else False
        if x>=hi-1e-9 or (x>=lo-1e-9 and rises): fires.append((v,s[-1][0],x))
    return fires
out=[]
for hi in (0.50,0.55,0.60):
    for lo in (0.25,0.30,0.35,0.40,0.45):
        for d in (0.05,0.1,0.15,0.2):
            for m in (2,3):
                l,fa=core.score(core.episodes(run2(hi,lo,d,m)))
                if len(l)==len(core.REC) and not fa:
                    g=list(l.values()); out.append((hi,lo,d,m,sorted(g)[len(g)//2],round(sum(g)/len(g),2),max(g),g))
out.sort(key=lambda z:(z[4],z[5]))
for o in out[:10]: print(f"  hi={o[0]} lo={o[1]} d={o[2]} m={o[3]} med={o[4]} mean={o[5]} max={o[6]} {o[7]}")
print("  clean configs:",len(out))
