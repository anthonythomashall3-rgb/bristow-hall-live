exec(open('minimise.py').read().split('print("PEAK-LEG SUBSETS')[0])
import itertools, numpy as np
PLbest={k:PL[k] for k in ('A','C','M')}
def sumt(r):
    lt,et=r['lags_t'],r['errs_t']; lp,ep=r['lags_p'],r['errs_p']
    return dict(pk=len(lp),other=r['other'],tr=len(lt),tmed=float(np.median(lt)),tworst=max(lt),
                t31=sum(1 for l in lt if l<=31),texact=sum(1 for e in et if e==0),
                tmae=round(float(np.mean(np.abs(et))),2),pmed=float(np.median(lp)))
keys=list(TLG.keys())
print("TROUGH-LEG SUBSETS (peak legs A,C,M; second condition fixed)")
print(f"  {'legs':10} {'pk':>3} {'oth':>3} {'tr':>3} {'tmed':>5} {'tworst':>6} {'<=31':>5} {'exact':>5} {'tmae':>5} {'pmed':>5}")
best=[]
for n in range(2,5):
    for c in itertools.combinations(keys,n):
        if n>4: continue
        try: s=sumt(run(PLbest,{k:TLG[k] for k in c}))
        except Exception: continue
        if s['pk']==len(PK) and s['tr']==len(TR) and s['other']<=1:
            best.append((c,s))
best.sort(key=lambda z:(len(z[0]), z[1]['tmed'], z[1]['tmae']))
for c,s in best[:14]:
    print(f"  {''.join(c):10} {s['pk']:>3} {s['other']:>3} {s['tr']:>3} {s['tmed']:>5.0f} {s['tworst']:>6} {s['t31']:>5} {s['texact']:>5} {s['tmae']:>5} {s['pmed']:>5.0f}")
print("  complete subsets:",len(best))
