"""THE VACANCY OBJECT'S SHAPE, swept on the lab's own construction (found in american_chronology.vacancy_gap):
   the k-month mean of the vacancy rate, subtracted from the maximum of that same mean over the previous back months
The maximum is taken over the SMOOTHED series and shifted one month — which is why the earlier rebuild from the raw file did not reproduce it.
Sweep k and back with the line swept at each; zero other calls on both vintages required. v2.8 elsewhere."""
from mini import *
from legu_min import s_cur, spl
exec(open('fast41.py').read().split("def full(")[0].replace("out=open('fast41.out','w')","out=open('sweep9.out','w')"))
sys.path.insert(0,W+'/lab/slack'); from objects import load
V0=-load()['-vacancy rate']
def vgap(k,back):
    m=V0.rolling(k).mean(); return (m.shift(1).rolling(back).max()-m).dropna()
chk=vgap(2,6).reindex(vr.index)
P("reconstruction check on the lab's own form, (2,6): max |diff| vs the lab's vr =",float((chk-vr).abs().max()))
def go5(nm,k,back,line,starts=29):
    G=vgap(k,back); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=line,pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,0.45,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    F25=[x for x in leg_gap_mx2(gm,0.25,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    Hc,_=mkpair2(starts,4,3,18); Hh=mkhours(2.0,1.20)
    def hubv(sl):
        calls=[]; armed=True
        for m,v in g.items():
            if m<pd.Timestamp('1948-06-01'): continue
            if armed and v>=sl:
                w=G[(G.index>=m-pd.DateOffset(months=6))&(G.index<=m)]; hit=w[w>=line]
                if len(hit):
                    kk=hit.index[0]; sp=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
                    calls.append((max(sp,pubs[kk]),m-pd.DateOffset(months=3),'hub')); armed=False
            elif not armed and v<sl: armed=True
        return calls
    res=[]
    for s in (s_cur,spl):
        U=confirm_w(leg_gapL(s,0.45,52,rearm='zero')+F45,[Vc,Hh],'month'); L=confirm_w(leg_gapL(s,0.25,52,rearm='window')+F25,[Hc],'month'); X=hubv(0.50)
        pk={'U':[(a,b) for a,b,c in U],'L':[(a,b) for a,b,c in L],'X':[(a,b) for a,b,c in X]}
        with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(pk,TLH)
        res.append(score13(turns))
    ok=all(len(r['other'])==0 and len(r['lags_p'])==13 for r in res)
    lp=[res[0]['lags_p'].get(i) for i in range(13)]; v73=[res[0]['lags_p'][i] for i in range(5,13) if i in res[0]['lags_p']]
    allv=[x for x in lp if x is not None]
    if ok: P(f"OK  {nm:30s} {lp} fp2007 {res[1]['lags_p'].get(10)} med73 {np.median(v73):.1f} MEAN-ALL {np.mean(allv):.1f} w1 {sum(1 for e in res[0]['errs_p'].values() if abs(e)<=1)}")
    return ok,(np.mean(allv) if ok else 9e9),lp
best=[]
for k in [1,2,3,4]:
    for bk in [4,6,9,12,18]:
        for ln in [0.60,0.50,0.45,0.40,0.36,0.35,0.30,0.25,0.20]:
            ok,mn,lp=go5(f'k={k} back={bk} line {ln}',k,bk,ln)
            if ok: best.append((mn,k,bk,ln,lp))
best.sort()
P("\nBEST BY MEAN LAG OVER ALL THIRTEEN:")
for mn,k,bk,ln,lp in best[:12]: P(f"   mean {mn:6.1f}  k={k} back={bk} line {ln}   {lp}")
out.close()
