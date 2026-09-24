"""v2.9 RECORD SCRIPT. The vacancy object's own SHAPE swept through the lab's own vacancy_gap_rt (identity check against the shipped series: 0.0),
which the earlier rebuild from the raw file had failed to reproduce. Winner: the FOUR-month mean of the vacancy rate against the maximum of that
same mean over the previous FOUR months, at 0.20 points (was the two-month mean against a six-month maximum at 0.35). It buys 1960: 122 -> 91.
Everything else as v2.8."""
from mini import *
from legu_min import s_cur, spl
exec(open('sweep11.py').read().split('P("\\nbaseline v2.8")')[0].replace("out=open('sweep11.out','w')","out=open('fast43.out','w')"))
def quiet(idx):
    q=pd.Series(True,index=idx)
    for p_,t in zip(PK,TR): q[(idx>=p_-pd.DateOffset(months=9))&(idx<=t+pd.DateOffset(months=18))]=False
    return q
def hits(o,line): o=o.dropna(); return (o>=line).reindex(pd.date_range('1949-01-01','2026-07-01',freq='MS')).fillna(False)
def wexp(hl,back=7,fwd=5,start='1960-01-01'):
    idx=pd.date_range(start,'2026-07-01',freq='MS'); h=np.zeros(len(idx),bool)
    for x in hl: h|=x.reindex(idx).fillna(False).values.astype(bool)
    s=pd.Series(h,index=idx); q=quiet(idx)
    return ((s[::-1].rolling(fwd,min_periods=1).max()[::-1].astype(bool))|(s.rolling(back,min_periods=1).max().astype(bool)))[q].mean()*100
def detail(nm,vk,vb,vl):
    G=vgap(vk,vb); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=vl,pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,0.45,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    F25=[x for x in leg_gap_mx2(gm,0.25,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    Hc,MX=mkpair3(29,4,3,18); Hh=mkhours(2.0,1.20)
    def hubv(sl):
        calls=[]; armed=True
        for m,v in g.items():
            if m<pd.Timestamp('1948-06-01'): continue
            if armed and v>=sl:
                w=G[(G.index>=m-pd.DateOffset(months=6))&(G.index<=m)]; hit=w[w>=vl]
                if len(hit):
                    kk=hit.index[0]; sp=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
                    calls.append((max(sp,pubs[kk]),m-pd.DateOffset(months=3),'hub')); armed=False
            elif not armed and v<sl: armed=True
        return calls
    for tag,s in [('CURRENT FILE',s_cur),('FIRST PRINTS',spl)]:
        U=confirm_w(leg_gapL(s,0.45,52,rearm='zero')+F45,[Vc,Hh],'month'); L=confirm_w(leg_gapL(s,0.25,52,rearm='window')+F25,[Hc],'month'); X=hubv(0.50)
        pk={'U':[(a,b) for a,b,c in U],'L':[(a,b) for a,b,c in L],'X':[(a,b) for a,b,c in X]}
        with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(pk,TLH)
        r=score13(turns); lp=[r['lags_p'].get(i) for i in range(13)]; lt=[r['lags_t'].get(i) for i in range(13)]
        v73=[r['lags_p'][i] for i in range(5,13) if i in r['lags_p']]; tv=[x for x in lt if x is not None]; allv=[x for x in lp if x is not None]
        P(f"\n{nm} — {tag}\n   onsets {lp} | 1973-on median {np.median(v73):.1f} | ALL-13 mean {np.mean(allv):.1f} | detected {len(r['lags_p'])}/13 | OTHER CALLS {[o[1] for o in r['other']]}")
        P(f"   peak dates {[r['errs_p'].get(i) for i in range(13)]} exact {sum(1 for e in r['errs_p'].values() if e==0)} within one {sum(1 for e in r['errs_p'].values() if abs(e)<=1)} | troughs median {np.median(tv):.0f} exact {sum(1 for e in r['errs_t'].values() if e==0)} early {sum(1 for x in tv if x<0)}")
        if tag=='CURRENT FILE': P("   carried by: "+" | ".join(f"{PK[i]:%Y-%m}:{r['opens'][i]['published']:%Y-%m-%d}{r['opens'][i]['leg']}" for i in range(13) if i in r['opens']))
    P(f"   vacancy exposure: confirmer window {wexp([hits(G,vl)]):.2f}%, hub six-back {wexp([hits(G,vl)],back=7,fwd=1,start='1949-01-01'):.2f}% -> hub hazard {2/((quiet(pd.date_range('1949-01-01','2026-07-01',freq='MS')).sum())/12)*wexp([hits(G,vl)],back=7,fwd=1,start='1949-01-01'):.3f}%/yr, one in {1/(2/((quiet(pd.date_range('1949-01-01','2026-07-01',freq='MS')).sum())/12)*wexp([hits(G,vl)],back=7,fwd=1,start='1949-01-01')/100):.0f}")
detail('v2.8 (vacancy: two-month mean vs six-month maximum, 0.35)',2,6,0.35)
detail('v2.9 (vacancy: FOUR-month mean vs FOUR-month maximum, 0.20)',4,4,0.20)
P("\nMARGINS. shipped (2,6) at 0.35: highest quiet reading 0.282 (the 2003 Sahm window) and 0.238 (the 1967 claims proposal) -> the line is 1.24 times the highest quiet reading; the thirteen recessions' lowest maximum is 0.486 (1960), 1.39 times the line.")
P("candidate (4,4) at 0.20: highest quiet reading 0.170 (1967) and 0.136 (2003) -> the line is 1.18 times the highest quiet reading; the thirteen recessions' lowest maximum is 0.264 (2020), 1.32 times the line. Tighter on both sides in ratio, and the whole series is scaled down by the longer mean.")
P("PLATEAU: at (4,4) the lines 0.20 and 0.18 give the identical record and 0.20 is the safer corner; 0.22 gives 1960 back at 122. The shape (4,5) at 0.20 gives the same record with a worse quiet margin (0.188 against 0.170), so (4,4) is the safer of the two. (3,4), (4,3), (5,4), (5,5) and (4,6) are all slower.")
P("REFUSED: the housing half with its maximum taken over the smoothed series rather than the raw (the lab's own shape for the vacancy) — slower at every line and the margin collapses to 0.043.")
out.close()
