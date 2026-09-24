"""CAN THE CAUSAL REPLAY BE MADE FASTER? Searching the same criterion harder does not help (causal29: coordinate
descent to convergence and a joint search over the five binding parameters give exactly the greedy answer). So the
question is whether a BETTER DECLARED CRITERION does. Two are tested, each declared here and applied identically at
every fold, neither using one observation from after the fold:
  FAST      — among values clean on the past, the one that made the past fastest. (the original)
  STABLE    — the same, but a value must be clean on the past AND on the past with its most recent recession removed,
              so a choice that rests on one episode cannot be made.
  ANNUAL    — FAST, but re-chosen every January from the record then available, which is what someone actually
              running the tool would do, instead of only at recessions."""
import sys
exec(open('causal28.py').read().split('MODE=sys.argv[2]')[0].replace("out=open('causal28_%s.out'%(sys.argv[2] if len(sys.argv)>2 else 'fast'),'w')","out=open('causal31.out','w')"))
def prior_mean(r,upto,skip=()):
    v=[r['lags_p'][j] for j in range(upto) if j in r['lags_p'] and j not in skip]
    return float(np.mean(v)) if v else 1e9
def ok_before2(r,turns,cut,upto,skip=()):
    prior=[j for j in range(upto) if j not in skip]
    called=all(j in r['lags_p'] for j in prior)
    other=[o for o in r['other'] if pd.Timestamp(o[0])<cut]
    early=[t for t in turns if t['kind']=='peak' and t['published']<pd.Timestamp('1948-06-01')]
    return called and not other and not early
def choose(cut,upto,mode,passes=3):
    p=dict(BASE); last=upto-1
    for _ in range(passes):
        changed=False
        for name,grid in ORDER:
            cands=[]
            for gv in grid:
                q=dict(p); q[name]=gv; r,t=ev(q)
                if not ok_before2(r,t,cut,upto): continue
                if mode=='stable' and upto>=2 and not ok_before2(r,t,cut,upto,skip=(last,)): continue
                cands.append((gv,prior_mean(r,upto)))
            if cands:
                nv=min(cands,key=lambda c:(c[1],grid.index(c[0])))[0]
                if nv!=p[name]: changed=True
                p[name]=nv
        if not changed: break
    return p
FROZEN=[-51,62,40,91,37,27,-7,55,-12,-2,67,26,66]
P(f"{'held out':10s} {'FAST lag':>9s} {'STABLE lag':>11s} {'frozen':>7s}   {'FAST other calls (whole record)':>34s}   STABLE other calls (whole record)")
A=[];Bb=[]
for i in FOLDS:
    cut=PK[i]-pd.DateOffset(months=6)
    pf=choose(cut,i,'fast'); rf,_=ev(pf)
    ps=choose(cut,i,'stable'); rs,_=ev(ps)
    A.append(rf['lags_p'].get(i)); Bb.append(rs['lags_p'].get(i))
    P(f"{PK[i]:%Y-%m}   {str(rf['lags_p'].get(i)):>9s} {str(rs['lags_p'].get(i)):>11s} {FROZEN[i]:>7d}   {str([o[1] for o in rf['other']]):>34s}   {[o[1] for o in rs['other']]}")
av=[x for x in A if x is not None]; bv=[x for x in Bb if x is not None]
P(f"\n   FAST   detected {len(av)}/{len(A)}, mean {np.mean(av):.1f}")
P(f"   STABLE detected {len(bv)}/{len(Bb)}, mean {np.mean(bv):.1f}")
out.close()
