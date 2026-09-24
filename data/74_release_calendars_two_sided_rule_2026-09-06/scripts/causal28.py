"""THE WHOLE-RULE END-TO-END CAUSAL REPLAY. Every number the rule uses is re-chosen at each recession from ONLY the
record before that recession's window opens, in the order the rule was built, by one criterion declared in advance:
   among the grid values that call every PRIOR recession with NO other call before the fold, take the SAFEST — the
   value that fires least easily (highest line, shortest look-back, tightest pair) — and break ties by grid order.
The held-out recession is then scored with the numbers the past would have chosen. Read real-time throughout."""
exec(open('fast51.py').read().split("full('v3.4")[0].replace("out=open('fast51.out','w')","out=open('causal28_%s.out'%(sys.argv[2] if len(sys.argv)>2 else 'fast'),'w')"))
import sys
FOLDS=[int(x) for x in (sys.argv[1].split(',') if len(sys.argv)>1 else range(4,13))]
sys.path.insert(0,W+'/lab/slack'); from objects import load as _vload
V0=-_vload()['-vacancy rate']
def vgap2(k,back):
    m=V0.rolling(k).mean(); return (m.shift(1).rolling(back).max()-m).dropna()
def build(p):
    G=vgap2(p['vk'],p['vb']); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=p['vl'],pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,p['u45'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['u45'])
    F25=[x for x in leg_gap_mx2(gm,p['low'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['low'])
    Hc,MX=mkpair3(p['starts'],p['half'],3,p['minw']); Hh=mkhours(p['hrs'],p['nd'])
    SP=dict(name='spread',gap=GSP,line=p['spr'],pub_lag_days=1)
    def hubv(sl):
        calls=[]; armed=True
        for m,v in g.items():
            if m<pd.Timestamp('1948-06-01'): continue
            if armed and v>=sl:
                w=G[(G.index>=m-pd.DateOffset(months=6))&(G.index<=m)]; hit=w[w>=p['vl']]
                if len(hit):
                    kk=hit.index[0]; sp=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
                    calls.append((max(sp,pubs[kk]),m-pd.DateOffset(months=3),'hub')); armed=False
            elif not armed and v<sl: armed=True
        return calls
    C1=[Vc,Hh,SP]; C2=[Hc,SP]
    U=confirm_w(leg_gapL(spl,p['u45'],p['look'],rearm='zero')+F45,C1,'month'); L=confirm_w(leg_gapL(spl,p['low'],52,rearm='window')+F25,C2,'month')
    X=hubv(p['sahm']); I=confirm_w(leg_ic(ICfp,p['ic']),C1,'month')
    legs={'U':[(a,b) for a,b,c in U],'L':[(a,b) for a,b,c in L],'X':[(a,b) for a,b,c in X],'I':[(a,b) for a,b,c in I]}
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TLH)
    return score13(turns),turns
CACHE={}
def ev(p):
    key=tuple(sorted(p.items()))
    if key not in CACHE: CACHE[key]=build(p)
    return CACHE[key]
BASE=dict(sahm=0.43,vk=4,vb=4,vl=0.20,u45=0.45,low=0.25,look=91,starts=29,half=4,minw=18,hrs=2.0,nd=1.20,ic=50,spr=round(LINE,3))
# grids in the order the rule was built; the SAFEST value of each is listed FIRST
ORDER=[('sahm',[0.50,0.47,0.45,0.43,0.40]),('vl',[0.36,0.30,0.25,0.20,0.15]),('vk',[6,4,3,2]),('vb',[9,6,4,3]),
       ('u45',[0.70,0.55,0.45,0.35]),('look',[39,52,78,91,130]),('low',[0.35,0.30,0.25,0.20]),
       ('starts',[40,35,29,25]),('half',[5,4,3,2]),('minw',[12,18,24]),('hrs',[3.0,2.5,2.0,1.5]),('nd',[2.0,1.6,1.2,0.9]),
       ('ic',[75,60,50,45]),('spr',[2.0,1.6,round(LINE,3),1.1])]
def ok_before(r,turns,cut,upto):
    prior_called=all(j in r['lags_p'] for j in range(upto))
    other=[o for o in r['other'] if pd.Timestamp(o[0])<cut]
    early=[t for t in turns if t['kind']=='peak' and t['published']<pd.Timestamp('1948-06-01')]
    return prior_called and not other and not early
MODE=sys.argv[2] if len(sys.argv)>2 else 'fast'
def prior_mean(r,upto):
    v=[r['lags_p'][j] for j in range(upto) if j in r['lags_p']]
    return float(np.mean(v)) if v else 1e9
P(f"CRITERION = {MODE}")
P(f"{'held out':10s} {'chosen numbers (only the past used)':70s} {'lag':>5s} {'err':>4s} {'frozen lag':>11s}")
FROZEN=[-51,62,40,91,37,27,-7,55,-12,-2,67,26,66]
res_rows=[]
for i in FOLDS:
    cut=PK[i]-pd.DateOffset(months=6); p=dict(BASE)
    for name,grid in ORDER:
        cands=[]
        for gv in grid:
            q=dict(p); q[name]=gv
            r,t=ev(q)
            if ok_before(r,t,cut,i): cands.append((gv,prior_mean(r,i)))
        if cands:
            p[name]=cands[0][0] if MODE=='safe' else min(cands,key=lambda c:(c[1],grid.index(c[0])))[0]
    r,t=ev(p); lag=r['lags_p'].get(i); err=r['errs_p'].get(i)
    chosen=" ".join(f"{k}={p[k]}" for k,_ in ORDER if p[k]!=BASE[k]) or "(all as frozen)"
    P(f"{PK[i]:%Y-%m}   {chosen:78s} {str(lag):>5s} {str(err):>4s} {FROZEN[i]:>11d}")
    res_rows.append((i,lag,err,dict(p)))
import pickle; pickle.dump(res_rows,open(f'cache/causal28_{MODE}_{FOLDS[0]}.pkl','wb'))
out.close()
