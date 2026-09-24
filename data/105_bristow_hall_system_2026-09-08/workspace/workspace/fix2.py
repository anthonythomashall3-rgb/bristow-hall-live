"""Correction to fix1: leg H's publication is derived from the CLAIMS-PEAK month, not the dated trough month — rebuilding it from the dated
month made the calls three months too early. The right correction is to move the publication day itself: H is dated on the tenth of the month
after its claims-peak month, and the weekly release that completes a month's initial claims is public between one and five days after that
month ends (collection 45, every release since 2002). So the tenth becomes the sixth: four days, on every H call. Also: which closer binds
each of the thirteen troughs."""
from mini import *
from legu_min import s_cur, spl
exec(open('fast40.py').read().split("V26=dict(")[0].replace("out=open('fast40.out','w')","out=open('fix2.out','w')"))
V26=dict(sahm=0.50,vac=0.35,u45=0.45,low=0.25,starts=33,half=4,h1=2.0,h2=1.20)
def build(p,s,TL):
    F45=[x for x in leg_gap_mx2(gm,p['u45'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    F25=[x for x in leg_gap_mx2(gm,p['low'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    Vc=dict(name='vac',gap=vr,line=p['vac'],pubs=VJ36['pubs']); Hc,_=mkpair(p['starts'],p['half']); Hh=mkhours(p['h1'],p['h2'])
    U=confirm_w(leg_gapx(s,p['u45'],rearm='zero')+F45,[Vc,Hh],'month'); L=confirm_w(leg_gapx(s,p['low'],rearm='window')+F25,[Hc],'month'); X=hub_actual(p['sahm'],vr,p['vac'])
    pk={'U':[(a,b) for a,b,c in U],'L':[(a,b) for a,b,c in L],'X':[(a,b) for a,b,c in X]}
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(pk,TL)
    return score13(turns)
def report(nm,TL):
    rs=[build(V26,s,TL) for s in (s_cur,spl)]
    r=rs[0]; lt=[r['lags_t'].get(i) for i in range(13)]; tv=[x for x in lt if x is not None]
    P(f"\n{nm}: troughs {lt} | median {np.median(tv):.0f} mean {np.mean(tv):.1f} | closed {len(tv)}/13 | dates exact {sum(1 for e in r['errs_t'].values() if e==0)} within one {sum(1 for e in r['errs_t'].values() if abs(e)<=1)} | early closes {sum(1 for x in tv if x<0)} | onsets unchanged {[r['lags_p'].get(i) for i in range(13)]} | others {[o[1] for q in rs for o in q['other']]}")
    P("   which closer: "+" | ".join(f"{TR[i]:%Y-%m}:{[t for t in r['turns'] if t['kind']=='trough' and (t['published']-me(TR[i])).days==r['lags_t'][i]][0]['leg']}" for i in range(13) if i in r['lags_t']))
    return np.median(tv)
report('v2.6 as shipped (H on the tenth)',TLC)
for d in [4,5]:
    TL2={k:list(v) for k,v in TLC.items()}; TL2['H']=[(p-pd.Timedelta(days=d),dd) for p,dd in TLC['H']]
    report(f'H moved {d} days earlier (the tenth -> the {10-d}th)',TL2)
TL3={k:list(v) for k,v in TLC.items()}; TL3['H']=[(p-pd.Timedelta(days=4),dd) for p,dd in TLC['H']]; TL3['S']=[(p,dd) for p,dd in TLC['S']]
P("\nS (Paper 1's Bristow rule) calls:",[(p.strftime('%Y-%m-%d'),d.strftime('%Y-%m')) for p,d in TLC['S']])
P("K calls:",[(p.strftime('%Y-%m-%d'),d.strftime('%Y-%m')) for p,d in TLC['K']])
P("J calls:",[(p.strftime('%Y-%m-%d'),d.strftime('%Y-%m')) for p,d in TLC['J']])
out.close()
