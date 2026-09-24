"""WHERE EACH CALL IS BOUND: for every one of the thirteen, the proposal's publication date and the confirmer's, so the binding side is visible.
Speed can only be bought on the binding side."""
from mini import *
from legu_min import s_cur, spl
exec(open('fast40.py').read().split("V26=dict(")[0].replace("out=open('fast40.out','w')","out=open('bind1.out','w')"))
V26=dict(sahm=0.50,vac=0.35,u45=0.45,low=0.25,starts=33,half=4,h1=2.0,h2=1.20)
def parts(p,s):
    F45=[x for x in leg_gap_mx2(gm,p['u45'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    F25=[x for x in leg_gap_mx2(gm,p['low'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    Vc=dict(name='vac',gap=vr,line=p['vac'],pubs=VJ36['pubs']); Hc,_=mkpair(p['starts'],p['half']); Hh=mkhours(p['h1'],p['h2'])
    props={'U':leg_gapx(s,p['u45'],rearm='zero')+F45,'L':leg_gapx(s,p['low'],rearm='window')+F25}
    U=confirm_w(props['U'],[Vc,Hh],'month'); L=confirm_w(props['L'],[Hc],'month'); X=hub_actual(p['sahm'],vr,p['vac'])
    pk={'U':[(a,b) for a,b,c in U],'L':[(a,b) for a,b,c in L],'X':[(a,b) for a,b,c in X]}
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(pk,TLC)
    r=score13(turns)
    pmap={}
    for k,v in props.items():
        for pp,dd in v: pmap[(k,dd)]=pp
    P(f"\n{'peak':9s} {'call':11s} lag  leg  {'proposal pub':12s} {'confirmer pub':13s} binding")
    for i in range(13):
        if i not in r['opens']: continue
        t=r['opens'][i]; leg=t['leg']
        if leg=='X': P(f"{PK[i]:%Y-%m}   {t['published']:%Y-%m-%d} {r['lags_p'][i]:4d}  hub   (Sahm release)  (vacancy release)  max of the two"); continue
        pp=pmap.get((leg,t['date'])); cf=[c for src in [U,L] for a,b,c in src if a==t['published'] and b==t['date']]
        P(f"{PK[i]:%Y-%m}   {t['published']:%Y-%m-%d} {r['lags_p'][i]:4d}  {leg}    {pp:%Y-%m-%d}   {cf[0] if cf else '?':13s} {'PROPOSAL' if pp==t['published'] else 'CONFIRMER'}")
    return r
for tag,s in [('CURRENT FILE',s_cur),('FIRST PRINTS',spl)]:
    P(f"\n######## {tag} ########"); parts(V26,s)
P("\nTROUGH CLOCK: leg H is dated on the 10th of the following month (pub10). Collection 45 shows the weekly release covering a month's last week is public about five days after the month ends.")
P("H calls as shipped:",[(p.strftime('%Y-%m-%d'),d.strftime('%Y-%m')) for p,d in TLC['H']])
P("K calls:",[(p.strftime('%Y-%m-%d'),d.strftime('%Y-%m')) for p,d in TLC['K']])
out.close()
