"""THE CAUSAL TEST WITH THE OBJECT CHOICE INCLUDED. causal32 found the blind spot: the LINE is causal (from 1980 the
past sets 1.323, exactly the full-sample value) but the OBJECT and its SHAPE are not — on the past alone a chooser
would have picked the PRIME-over-bill spread until 2020, and a seventeen-week mean over a six-month window rather than
the thirteen over nine this memo adopted. So here the confirmer itself is re-chosen at every fold, from the past only:
eight spreads x six shapes, the line set by the same 1.5x rule, ranked by how many PRIOR recessions the object reaches
and, as a tie-break, by its margin over the worst quiet reading. Then the fourteen numbers are re-chosen as before and
the held-out recession is scored."""
import sys
exec(open('causal28.py').read().split('MODE=sys.argv[2]')[0].replace("out=open('causal28_%s.out'%(sys.argv[2] if len(sys.argv)>2 else 'fast'),'w')","out=open('causal33.out','w')"))
def sp2(a,b):
    aa=L25(a); bb=L25(b)
    if aa is None or bb is None: return None
    idx=aa.index.union(bb.index); S=(aa.reindex(idx).ffill()-bb.reindex(idx).ffill()).dropna()
    return S[S.index>=max(aa.index.min(),bb.index.min())]
FAM=[('CP1m-bill3m','H0RIFSPPFM01NWF','WTB3MS'),('CP3m-bill3m','H0RIFSPPFM03NWF','WTB3MS'),('CP6m-bill3m','H0RIFSPPFM06NWF','WTB3MS'),
     ('BA3m-bill3m','H1RIFSPABM03NWF','WTB3MS'),('prime-bill3m','WPRIME','WTB3MS'),('CD3m-bill3m','WCD3M','WTB3MS'),
     ('CP3m-funds','H0RIFSPPFM03NWF','FF'),('bill6m-bill3m','WTB6MS','WTB3MS')]
RAW={nm:sp2(a,b) for nm,a,b in FAM}
RAW={k:v for k,v in RAW.items() if v is not None and len(v)>200}
SHAPES=[(4,26),(8,26),(13,26),(13,39),(17,26),(26,39)]
def objx(S,sm,win):
    m=S.rolling(sm).mean(); return (m-m.rolling(win).min()).dropna()
OBJ={(nm,sm,win):objx(S,sm,win) for nm,S in RAW.items() for sm,win in SHAPES}
def rank_obj(cut,upto):
    """the confirmers the past would consider, best first: clears every quiet window it covers before the fold at 1.5x,
       most prior recessions reached, tie-broken by the largest margin over the worst quiet reading"""
    out_=[]
    for key,Gx in OBJ.items():
        qb=[dd for dd in QP if dd<cut and len(wseg(Gx,dd))]
        if len(qb)<5: continue
        qm=max(float(wseg(Gx,dd).max()) for dd in qb); ln=qm*1.5
        prior=[j for j in range(upto) if len(wseg(Gx,PK[j]))]
        if not prior: continue
        vals=[float(wseg(Gx,PK[j]).max()) for j in prior]
        n=sum(1 for v in vals if v>=ln); marg=(min([v for v in vals if v>=ln]) / ln) if n else 0
        out_.append(((n,marg,-list(OBJ).index(key)),key,ln,Gx))
    out_.sort(key=lambda x:x[0],reverse=True)
    return out_
FROZEN=[-51,62,40,91,37,27,-7,55,-12,-2,67,26,66]
def prior_mean(r,upto):
    v=[r['lags_p'][j] for j in range(upto) if j in r['lags_p']]
    return float(np.mean(v)) if v else 1e9
def build2(p,Gx,ln):
    global GSP,LINE
    GSP_old,LINE_old=GSP,LINE
    try:
        GSP=Gx; LINE=ln
        q=dict(p); q['spr']=ln
        return build(q)
    finally:
        GSP,LINE=GSP_old,LINE_old
P(f"{'fold':10s} {'confirmer the past would choose':34s} {'line':>7s} {'lag':>5s} {'err':>4s} {'frozen':>7s}  other calls (whole record)")
rows=[]
for i in FOLDS:
    cut=PK[i]-pd.DateOffset(months=6); cands_obj=rank_obj(cut,i)
    if not cands_obj: P(f"{PK[i]:%Y-%m}   (no spread has five quiet windows before this fold)"); continue
    chosen=None
    for (_,key,ln,Gx) in cands_obj[:12]:
        p=dict(BASE); anyclean=False
        for _ in range(3):
            changed=False
            for name,grid in ORDER:
                if name=='spr': continue
                cc=[]
                for gv in grid:
                    q=dict(p); q[name]=gv
                    r,t=build2(q,Gx,ln)
                    if ok_before(r,t,cut,i): cc.append((gv,prior_mean(r,i)))
                if cc:
                    anyclean=True
                    nv=min(cc,key=lambda c:(c[1],grid.index(c[0])))[0]
                    if nv!=p[name]: changed=True
                    p[name]=nv
            if not changed: break
        r0,t0=build2(p,Gx,ln)
        if anyclean and ok_before(r0,t0,cut,i): chosen=(key,ln,Gx,dict(p)); break
    if chosen is None: P(f"{PK[i]:%Y-%m}   (NO object gives a configuration clean on the past)"); continue
    key,ln,Gx,p=chosen
    r,t=build2(p,Gx,ln)
    P(f"{PK[i]:%Y-%m}   {str(key):34s} {ln:7.3f} {str(r['lags_p'].get(i)):>5s} {str(r['errs_p'].get(i)):>4s} {FROZEN[i]:>7d}  {[o[1] for o in r['other']]}")
    rows.append((i,r['lags_p'].get(i),r['errs_p'].get(i),str(key),[o[1] for o in r['other']]))
v=[l for _,l,_,_,_ in rows if l is not None]
if v: P(f"\n   detected {len(v)}/{len(rows)}, mean {np.mean(v):.1f}; folds whose settings make an other call somewhere: {sum(1 for _,_,_,_,o in rows if o)}")
import pickle; pickle.dump(rows,open(f'cache/causal33_{FOLDS[0]}.pkl','wb'))
out.close()
