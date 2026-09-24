import core, json
S=[(core.VIN[j],core.series(j)) for j in range(len(core.VIN))]
S=[(v,s) for v,s in S if s]
CACHE={}
for k in (2,3,4):
    for L in (9,12,15,18,24):
        CACHE[(k,L)]=[(v,s[-1][0],core.indicator(s,k,L)) for v,s in S]
res=[]
for (k,L),arr in CACHE.items():
    for ti in range(20,71):
        thr=ti/100
        for strict in (False,True):
            for p in (1,2):
                out=[];streak=0
                for v,m,x in arr:
                    if x is None: continue
                    hit=(x>thr) if strict else (x>=thr-1e-9)
                    streak=streak+1 if hit else 0
                    if streak>=p: out.append((v,m,x))
                l,fa=core.score(core.episodes(out))
                if len(l)<len(core.REC) or fa: continue
                lags=list(l.values())
                res.append(dict(k=k,L=L,thr=thr,strict=strict,p=p,
                    med=sorted(lags)[len(lags)//2],mx=max(lags),mn=min(lags),
                    mean=round(sum(lags)/len(lags),2),lags=lags))
res.sort(key=lambda r:(r['med'],r['mean'],r['mx']))
print("clean configs (10/10 detected, zero false alarms):",len(res))
for r in res[:20]:
    print(f"  k={r['k']} L={r['L']} thr={r['thr']:.2f} {'>' if r['strict'] else '>='} p={r['p']}  med={r['med']} mean={r['mean']} range=[{r['mn']},{r['mx']}] {r['lags']}")
json.dump(res,open('grid_results.json','w'))
