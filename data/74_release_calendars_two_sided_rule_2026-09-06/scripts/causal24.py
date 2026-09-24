"""IS v2.4 FITTED — the causal replay. At each recession from 1973 every line the rule chooses is re-chosen using ONLY the record
before it, in the order the rule was built (hub Sahm line; vacancy line; U45 line; low line; the pair's starts and rate-half lines),
and the held-out recession is then scored. Two criteria: SAFE (all prior called, fewest other calls, then the tightest line = Rule 21's
corner) and FAST (all prior called, at most one other, fastest median). Sahm's 0.50 is NOT inherited — it is re-chosen too.
Everything on first prints where they exist; windows on data months; actual release dates."""
from mini import *
from legu_min import s_cur, spl
import itertools
exec(open('fast37.py').read().split("RES={}")[0].replace("out=open('fast37.out','w')","out=open('causal24.out','w')"))
GRID=dict(sahm=[0.35,0.40,0.43,0.50,0.60,0.70], vac=[0.24,0.30,0.36,0.42], u45=[0.35,0.45,0.55,0.70], low=[0.15,0.25,0.35], starts=[25,30,35,40,45], half=[2,3,4,5])
def build(p,s):
    rate=(((UR-UR.rolling(12).min())*10).round()/p['half']); hh=(lh.rolling(12).max()-lh.rolling(2).mean())/p['starts']
    Hc,_=mk_pair2(hh,rate)
    V=dict(name='vac',gap=vr,line=p['vac'],pubs=VJ36['pubs'])
    U=confirm_w(leg_gapx(s,p['u45'],rearm='zero')+[x for x in leg_gap_mx(gm,p['u45'],rearm='window') if x[1]<pd.Timestamp('1971-01-01')],[V,Ppx],'month')
    L=confirm_w(leg_gapx(s,p['low'],rearm='window')+[x for x in leg_gap_mx(gm,p['low'],rearm='window') if x[1]<pd.Timestamp('1971-01-01')],[Hc],'month')
    X=hub_actual(p['sahm'],vr,p['vac'])
    pk={'U':[(a,b) for a,b,c in U],'L':[(a,b) for a,b,c in L],'X':[(a,b) for a,b,c in X]}
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(pk,TLC)
    return score13(turns)
def mk_pair2(dem_h,rate_h):
    ev=[(relH[m],'D',m) for m in dem_h.index if m in relH.index]+[(relU[m],'U',m) for m in rate_h.index if m in relU.index and m>=pd.Timestamp('1960-01-01')]
    ev.sort(key=lambda x:(x[0],x[1])); lastD=None; lastU=None; fires={}; mx={}
    for d,kind,m in ev:
        if kind=='D': lastD=m if (lastD is None or m>lastD) else lastD
        else: lastU=m if (lastU is None or m>lastU) else lastU
        if lastD is None or lastU is None: continue
        v=min(dem_h.get(lastD,np.nan),rate_h.get(lastU,np.nan))
        if np.isnan(v): continue
        key=max(lastD,lastU); mx[key]=max(mx.get(key,-9),v)
        if v>=1.0 and key not in fires: fires[key]=d
    G=pd.Series({m:(1.0 if m in fires else mx[m]) for m in mx}).sort_index(); PB=pd.Series({m:fires.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=2)) for m in mx}).sort_index()
    return dict(name='pair',gap=G,line=1.0,pubs=PB), pd.Series(mx).sort_index()
CACHE={}
def sc(p,s,tag):
    k=(tuple(sorted(p.items())),tag)
    if k not in CACHE: CACHE[k]=build(p,s)
    return CACHE[k]
FROZEN=dict(sahm=0.43,vac=0.36,u45=0.45,low=0.25,starts=35,half=4)
ORDER=['sahm','vac','u45','low','starts','half']
for tag,s in [('CURRENT FILE',s_cur),('FIRST PRINTS',spl)]:
    P(f"\n########## {tag} ##########")
    for crit in ['safe','fast']:
        P(f"\n--- {crit.upper()} criterion ---")
        held={}
        for fold in range(5,13):                      # 1973 onward
            prior=list(range(0,fold)); p=dict(FROZEN)
            for key in ORDER:
                best=None
                for v in GRID[key]:
                    q=dict(p); q[key]=v; r=sc(q,s,tag)
                    called=[i for i in prior if i in r['lags_p']]
                    if len(called)<len(prior): continue
                    others=len([o for o in r['other'] if pd.Timestamp(o[1]+'-01')<PK[fold]])
                    med=np.median([r['lags_p'][i] for i in called]) if called else 9e9
                    if crit=='safe': sk=(others, -GRID[key].index(v) if key in ('sahm','vac','u45','low') else GRID[key].index(v))
                    else:
                        if others>1: continue
                        sk=(med,others)
                    if best is None or sk<best[0]: best=(sk,v)
                if best: p[key]=best[1]
            r=sc(p,s,tag)
            held[fold]=(dict(p), r['lags_p'].get(fold), len([o for o in r['other'] if pd.Timestamp(o[1]+'-01')<=PK[fold]]))
            P(f"   fold {PK[fold]:%Y-%m}: lines {p} -> held-out lag {held[fold][1]}, other calls up to it {held[fold][2]}")
        lags=[v[1] for v in held.values() if v[1] is not None]
        P(f"   {crit}: detected {len(lags)}/8, median {np.median(lags):.0f}, worst {max(lags)}, other calls at the last fold {list(held.values())[-1][2]}")
    r=sc(FROZEN,s,tag); P(f"\n   FROZEN v2.4 in sample: {[r['lags_p'].get(i) for i in range(13)]}, other {[o[1] for o in r['other']]}, 1973-on median {np.median([r['lags_p'][i] for i in range(5,13) if i in r['lags_p']]):.1f}")
out.close()
