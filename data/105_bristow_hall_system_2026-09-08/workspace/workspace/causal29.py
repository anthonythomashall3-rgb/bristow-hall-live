"""THE CAUSAL REPLAY, SEARCHED PROPERLY. The CRITERION is unchanged and was declared before any of this: among the grid
values that call every prior recession with no other call before the fold, take the one that made THE PAST fastest.
What changes is only how hard that criterion is searched. causal28 took ONE greedy pass through the parameters in build
order; that lands wherever the order happens to put it. Here the same criterion is (a) iterated to convergence, and
(b) followed by a JOINT search over the five parameters that actually bind. Nothing here uses a single observation from
after the fold — the search is harder, not later."""
import sys
exec(open('causal28.py').read().split('MODE=sys.argv[2]')[0].replace("out=open('causal28_%s.out'%(sys.argv[2] if len(sys.argv)>2 else 'fast'),'w')","out=open('causal29_%s.out'%(sys.argv[2] if len(sys.argv)>2 else 'fast'),'w')"))
MODE=sys.argv[2] if len(sys.argv)>2 else 'fast'
def prior_mean(r,upto):
    v=[r['lags_p'][j] for j in range(upto) if j in r['lags_p']]
    return float(np.mean(v)) if v else 1e9
import itertools
KEY=[('sahm',[0.50,0.45,0.43]),('look',[52,91,130]),('low',[0.30,0.25,0.20]),('spr',[1.6,round(LINE,3),1.1]),('ic',[60,50,45])]
FROZEN=[-51,62,40,91,37,27,-7,55,-12,-2,67,26,66]
P(f"CRITERION = {MODE} (unchanged); SEARCH = coordinate descent to convergence, then a joint search over {len(KEY)} binding parameters")
P(f"{'held out':10s} {'passes':>7s} {'lag (1 pass)':>13s} {'lag (converged)':>16s} {'lag (joint)':>12s} {'err':>4s} {'frozen':>7s}")
res_rows=[]
for i in FOLDS:
    cut=PK[i]-pd.DateOffset(months=6); p=dict(BASE); lag1=None; npass=0
    for _pass in range(6):
        changed=False; npass=_pass+1
        for name,grid in ORDER:
            cands=[]
            for gv in grid:
                q=dict(p); q[name]=gv; r,t=ev(q)
                if ok_before(r,t,cut,i): cands.append((gv,prior_mean(r,i)))
            if cands:
                nv=cands[0][0] if MODE=='safe' else min(cands,key=lambda c:(c[1],grid.index(c[0])))[0]
                if nv!=p[name]: changed=True
                p[name]=nv
        if _pass==0: lag1=ev(dict(p))[0]['lags_p'].get(i)
        if not changed: break
    conv=dict(p); lagc=ev(conv)[0]['lags_p'].get(i); pmc=prior_mean(ev(conv)[0],i)
    best=(pmc,dict(conv))
    for combo in itertools.product(*[gv for _,gv in KEY]):
        q=dict(conv)
        for (nm2,_),val in zip(KEY,combo): q[nm2]=val
        r,t=ev(q)
        if not ok_before(r,t,cut,i): continue
        pm=prior_mean(r,i)
        if pm<best[0]: best=(pm,dict(q))
    p=best[1]; r,t=ev(p); lag=r['lags_p'].get(i); err=r['errs_p'].get(i)
    P(f"{PK[i]:%Y-%m}   {npass:7d} {str(lag1):>13s} {str(lagc):>16s} {str(lag):>12s} {str(err):>4s} {FROZEN[i]:>7d}")
    res_rows.append((i,lag,err,dict(p),[o[1] for o in r['other']]))
import pickle; pickle.dump(res_rows,open(f'cache/causal29_{MODE}_{FOLDS[0]}.pkl','wb'))
for i,lag,err,p,oth in res_rows:
    P(f"   {PK[i]:%Y-%m} chose: " + " ".join(f"{k}={p[k]}" for k,_ in ORDER if p[k]!=BASE[k]) + f"   other calls at this fold: {oth}")
out.close()
