"""TWO THINGS THE FIRST REPLAY GOT WRONG OR LEFT OUT (Rule Zero).
(1) causal28 reported 'no other call at any fold'. That was measured with the criterion's OWN test, which only counts
    other calls BEFORE the fold — as it must, since the criterion cannot see the future. But the settings the past
    would have chosen also have a record AFTER the fold, and that record is not clean at every fold. Both are printed
    here: other calls before the fold (what the chooser could see) and over the WHOLE record (what actually happened).
(2) A second, uniformly applied causal rule: instead of re-choosing only at recessions, re-choose EVERY JANUARY from
    the record then available — which is what a practitioner running the tool would actually do."""
import sys
exec(open('causal28.py').read().split('MODE=sys.argv[2]')[0].replace("out=open('causal28_%s.out'%(sys.argv[2] if len(sys.argv)>2 else 'fast'),'w')","out=open('causal30.out','w')"))
def prior_mean(r,upto):
    v=[r['lags_p'][j] for j in range(upto) if j in r['lags_p']]
    return float(np.mean(v)) if v else 1e9
def choose(cut,upto,passes=3):
    p=dict(BASE)
    for _ in range(passes):
        changed=False
        for name,grid in ORDER:
            cands=[]
            for gv in grid:
                q=dict(p); q[name]=gv; r,t=ev(q)
                if ok_before(r,t,cut,upto): cands.append((gv,prior_mean(r,upto)))
            if cands:
                nv=min(cands,key=lambda c:(c[1],grid.index(c[0])))[0]
                if nv!=p[name]: changed=True
                p[name]=nv
        if not changed: break
    return p
FROZEN=[-51,62,40,91,37,27,-7,55,-12,-2,67,26,66]
P("(1) THE SAME REPLAY, WITH BOTH FALSE-ALARM COUNTS")
P(f"{'held out':10s} {'lag':>5s} {'err':>4s} {'frozen':>7s}  {'other calls BEFORE the fold':>28s}  other calls over the WHOLE record")
tot=[]
for i in FOLDS:
    cut=PK[i]-pd.DateOffset(months=6); p=choose(cut,i); r,t=ev(p)
    before=[o[1] for o in r['other'] if pd.Timestamp(o[0])<cut]; whole=[o[1] for o in r['other']]
    P(f"{PK[i]:%Y-%m}   {str(r['lags_p'].get(i)):>5s} {str(r['errs_p'].get(i)):>4s} {FROZEN[i]:>7d}  {str(before):>28s}  {whole}")
    tot.append((i,r['lags_p'].get(i),len(before),len(whole)))
P(f"\n   detected {sum(1 for _,l,_,_ in tot if l is not None)}/{len(tot)}; mean lag {np.mean([l for _,l,_,_ in tot if l is not None]):.1f}")
P(f"   folds with an other call BEFORE the fold: {sum(1 for _,_,b,_ in tot if b)} of {len(tot)}")
P(f"   folds whose chosen settings make an other call SOMEWHERE on the record: {sum(1 for _,_,_,w in tot if w)} of {len(tot)}")
out.close()
