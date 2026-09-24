"""The VACANCY object's own shape swept — it binds 1948, 1953, 1957, 1960, 2001 and 2020. Currently the two-month mean below the six-month
maximum. Sweep the mean length k and the maximum's back window, with the line swept at each, requiring zero other calls on both vintages.
Also the hours x nondurable pair's windows. v2.7 elsewhere."""
from mini import *
from legu_min import s_cur, spl
exec(open('fast41.py').read().split("def full(")[0].replace("out=open('fast41.out','w')","out=open('sweep7.out','w')"))
vraw=pd.read_csv(W+'/lab/vac/vacancy_rate_PNZ_JOLTS.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
P("raw vacancy rate:",vraw.index.min().date(),"->",vraw.index.max().date(),len(vraw))
chk=(vraw.rolling(2).mean().rsub(vraw.rolling(6).max())).dropna()
P("reconstruction check, (2,6) rebuilt vs the lab's vr, max |diff| over 1948-2026:",float((chk.reindex(vr.index)-vr).abs().max()))
def vgap(k,back): return (vraw.rolling(back).max()-vraw.rolling(k).mean()).dropna()
def go3(nm,k,back,line,starts=31,mean_k=3,minw=18):
    Vc=dict(name='vac',gap=vgap(k,back),line=line,pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in vgap(k,back).index}))
    F45=[x for x in leg_gap_mx2(gm,0.45,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    F25=[x for x in leg_gap_mx2(gm,0.25,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    Hc,_=mkpair2(starts,4,mean_k,minw); Hh=mkhours(2.0,1.20); G=vgap(k,back)
    def hubv(sl):
        calls=[]; armed=True
        for m,v in g.items():
            if m<pd.Timestamp('1948-06-01'): continue
            if armed and v>=sl:
                w=G[(G.index>=m-pd.DateOffset(months=6))&(G.index<=m)]; hit=w[w>=line]
                if len(hit):
                    kk=hit.index[0]; sp=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
                    pk_=relJ[kk] if kk in relJ.index else pd.Timestamp(kk.year,kk.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)
                    calls.append((max(sp,pk_),m-pd.DateOffset(months=3),'hub')); armed=False
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
    P(f"{'OK ' if ok else 'BAD'} {nm:34s} {lp} fp2007 {res[1]['lags_p'].get(10)} med73 {np.median(v73):.1f} MEAN-ALL {np.mean(allv):.1f} others {[o[1] for r in res for o in r['other']]}")
    return ok
P("\n--- vacancy (k, back) with its line swept ---")
for k,bk in [(2,6),(1,6),(2,9),(3,9),(2,12),(3,12),(1,9),(1,12)]:
    for ln in [0.60,0.50,0.45,0.40,0.35,0.30,0.25]:
        go3(f'vac k={k} back={bk} line {ln}',k,bk,ln)
out.close()
