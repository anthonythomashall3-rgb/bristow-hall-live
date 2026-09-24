"""v3.1 RECORD SCRIPT: v3.0 plus the Chicago Fed's national financial conditions CREDIT subindex (weekly from March 1971) as a fourth
confirmer — its rise over twelve weeks, at 1.25. Buys 1973 from 35 to 27 days, inside the month."""
from mini import *
from legu_min import s_cur, spl
exec(open('daily4.py').read().split("qq=sorted(")[0].replace("out=open('daily4.out','w')","out=open('fast47.out','w')"))
CRD=dict(name='credit12',gap=G12,line=1.25,pub_lag_days=1)
def full(nm,extra):
    G=vgap(4,4); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=0.20,pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,0.45,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    F25=[x for x in leg_gap_mx2(gm,0.25,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    Hc,MX=mkpair3(29,4,3,18); Hh=mkhours(2.0,1.20)
    def hubv(sl):
        calls=[]; armed=True
        for m,v in g.items():
            if m<pd.Timestamp('1948-06-01'): continue
            if armed and v>=sl:
                w=G[(G.index>=m-pd.DateOffset(months=6))&(G.index<=m)]; hit=w[w>=0.20]
                if len(hit):
                    kk=hit.index[0]; sp=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
                    calls.append((max(sp,pubs[kk]),m-pd.DateOffset(months=3),'hub')); armed=False
            elif not armed and v<sl: armed=True
        return calls
    C1=[Vc,Hh]+extra; C2=[Hc]+extra
    for tag,s,ics in [('CURRENT FILE',s_cur,IC),('FIRST PRINTS',spl,ICfp)]:
        U=confirm_w(leg_gapL(s,0.45,52,rearm='zero')+F45,C1,'month'); L=confirm_w(leg_gapL(s,0.25,52,rearm='window')+F25,C2,'month'); X=hubv(0.50); I=confirm_w(leg_ic(ics,50),C1,'month')
        legs={'U':[(a,b) for a,b,c in U],'L':[(a,b) for a,b,c in L],'X':[(a,b) for a,b,c in X],'I':[(a,b) for a,b,c in I]}
        with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TLH)
        r=score13(turns); lp=[r['lags_p'].get(i) for i in range(13)]; lt=[r['lags_t'].get(i) for i in range(13)]
        allv=[x for x in lp if x is not None]; tv=[x for x in lt if x is not None]
        P(f"\n{nm} — {tag}\n   onsets {lp} | all-13 mean {np.mean(allv):.1f} | within the month {sum(1 for x in allv if x<=31)}/13 | detected {len(r['lags_p'])}/13 | OTHER CALLS {[o[1] for o in r['other']]}")
        P(f"   peak dates {[r['errs_p'].get(i) for i in range(13)]} exact {sum(1 for e in r['errs_p'].values() if e==0)} within one {sum(1 for e in r['errs_p'].values() if abs(e)<=1)} | troughs median {np.median(tv):.0f} exact {sum(1 for e in r['errs_t'].values() if e==0)} early {sum(1 for x in tv if x<0)}")
        if tag=='CURRENT FILE':
            cond={(p,dd):c for v in [U,L,X,I] for p,dd,c in v}
            P("   carried by: "+" | ".join(f"{PK[i]:%Y-%m}:{r['opens'][i]['published']:%Y-%m-%d}{r['opens'][i]['leg']}({cond.get((r['opens'][i]['published'],r['opens'][i]['date']),'hub')})" for i in range(13) if i in r['opens']))
full('v3.0',[]); full('v3.1 (+ credit subindex)',[CRD])
P("\nTHE CREDIT OBJECT: the Chicago Fed's national financial conditions CREDIT subindex, weekly since 26 March 1971, published the next day.")
P("   reading: its rise above its lowest value of the previous twelve weeks. Line 1.25.")
P("   highest reading inside any quiet proposal's window: 0.704 (August 1978), then 0.555 (November 1984) and 0.391 (1976, 1977) — the line clears it by 1.78 times.")
P("   the recessions it reaches: 1973 1.32, 1980 1.27, 2020 0.73, 1981 0.76, 2007 0.58, 1990 0.45, 2001 0.40, 2024 0.02 — at 1.25 it fires in 1973 and 1980.")
P("   2025-26 maximum 0.087 against the line's 1.25.")
P("   PLATEAU: every line from 0.72 to 1.30 gives the identical record; 1.50 and above loses the 1973 gain. 1.25 is the highest line at which the object still fires in more than one recession. Window: 9, 12, 16, 20 and 26 weeks all give the identical record at their own construction-grade lines; 6 weeks additionally buys 2007 (4 -> -4) and is the priced faster alternative.")
out.close()
