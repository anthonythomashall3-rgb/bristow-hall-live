"""Last levers. (a) the hours pair admitted as a SECOND confirmer of the low branch (refused by the route chat at their settings — retest at
v2.7's); (b) the vacancy as a second confirmer of the low branch (same); (c) the starts line at 29, the priced faster alternative, fully
scored; (d) the confirmation window's back reach. Zero other calls on both vintages required throughout."""
from mini import *
from legu_min import s_cur, spl
exec(open('fast41.py').read().split("def full(")[0].replace("out=open('fast41.out','w')","out=open('sweep8.out','w')"))
def go4(nm,starts=31,lowconf=('pair',),back=6):
    F45=[x for x in leg_gap_mx2(gm,0.45,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    F25=[x for x in leg_gap_mx2(gm,0.25,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    Vc=dict(name='vac',gap=vr,line=0.35,pubs=VJ36['pubs']); Hc,MX=mkpair2(starts,4,3,18); Hh=mkhours(2.0,1.20)
    cf=[]; 
    for c in lowconf: cf.append({'pair':Hc,'hours':Hh,'vac':Vc}[c])
    res=[]
    for s in (s_cur,spl):
        U=confirm_w(leg_gapL(s,0.45,52,rearm='zero')+F45,[Vc,Hh],'month',back=back); L=confirm_w(leg_gapL(s,0.25,52,rearm='window')+F25,cf,'month',back=back); X=hub_actual(0.50,vr,0.35)
        pk={'U':[(a,b) for a,b,c in U],'L':[(a,b) for a,b,c in L],'X':[(a,b) for a,b,c in X]}
        with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(pk,TLH)
        res.append(score13(turns))
    ok=all(len(r['other'])==0 and len(r['lags_p'])==13 for r in res)
    lp=[res[0]['lags_p'].get(i) for i in range(13)]; v73=[res[0]['lags_p'][i] for i in range(5,13) if i in res[0]['lags_p']]
    P(f"{'OK ' if ok else 'BAD'} {nm:46s} {lp} fp2007 {res[1]['lags_p'].get(10)} med73 {np.median(v73):.1f} mean {np.mean(v73):.1f} dates_w1 {sum(1 for e in res[0]['errs_p'].values() if abs(e)<=1)} others {[o[1] for r in res for o in r['other']]}")
    return ok
P("--- (a)(b) second confirmers for the low branch ---")
go4('v2.7 baseline (pair only)')
go4('low branch confirmable by pair OR hours pair',lowconf=('pair','hours'))
go4('low branch confirmable by pair OR vacancy',lowconf=('pair','vac'))
P("\n--- (c) the priced faster starts line ---")
for st in [31,30,29]: go4(f'starts {st}',starts=st)
P("\n--- (d) confirmation window back reach ---")
for bk in [6,7,8,9]: go4(f'back reach {bk} months',back=bk)
out.close()
