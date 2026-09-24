"""v3.2 RECORD SCRIPT. Anthony's vintage rule applied to the pre-1971 supply side: use what was known AT THE TIME.
The Department's own national weekly first prints (collection 59) give an insured rate from January 1949, seasonally
adjusted in real time and published twelve days after its week; the tool had been proposing before 1971 off the
Fieldhouse monthly reconstruction, published the tenth of the following month, which is the binding side at 1953 and
1957. The first-print rate is added as a proposal at the rule's own line (0.45 on the 0.45 branch, 0.25 on the low
branch) and at a second, higher line (1.00 / 0.60), the safe corner of the clean plateau. Also priced here: the hub on
0.43 instead of Sahm's published 0.50, which buys 2024 from 94 to 66 days at the cost of dating it March instead of
April."""
from mini import *
from legu_min import s_cur, spl
exec(open('daily4.py').read().split("qq=sorted(")[0].replace("out=open('daily4.out','w')","out=open('fast48.out','w')"))
CRD=dict(name='credit12',gap=G12,line=1.25,pub_lag_days=1)
D59=W.replace('24_bristow_rule_lab/workspace','59_dol_weekly_state_claims_1945-1983_2026-09')
RT=pd.read_csv(os.path.join(D59,'national_iur_realtime_sa_first_prints_1948_1983.csv'),index_col=0,parse_dates=True).iloc[:,0].dropna()
P(f"the Department's own weekly insured rate as FIRST PUBLISHED, real-time seasonal adjustment: {RT.index.min().date()} -> {RT.index.max().date()}, {len(RT)} weeks")
def leg_rt(s,pct,look=52,pub=12,stop='1971-01-01'):
    m=s.rolling(look,min_periods=look).min().shift(1); rel_=s-m; c=[]; armed=True
    for t,v in rel_.dropna().items():
        if armed and v>=pct: c.append((t+pd.Timedelta(days=pub),pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=0: armed=True
    return [x for x in c if x[1]<pd.Timestamp(stop)]
def full(nm,extra,rt=False,hubline=0.50,ret=False):
    G=vgap(4,4); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=0.20,pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,0.45,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    F25=[x for x in leg_gap_mx2(gm,0.25,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    if rt: F45=F45+leg_rt(RT,0.45)+([leg_rt(RT,1.00)] and leg_rt(RT,1.00) if rt=='two' else []); F25=F25+leg_rt(RT,0.25)+(leg_rt(RT,0.60) if rt=='two' else [])
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
    C1=[Vc,Hh]+extra; C2=[Hc]+extra; keep=None
    for tag,s,ics in [('CURRENT FILE',s_cur,IC),('FIRST PRINTS',spl,ICfp)]:
        U=confirm_w(leg_gapL(s,0.45,52,rearm='zero')+F45,C1,'month'); L=confirm_w(leg_gapL(s,0.25,52,rearm='window')+F25,C2,'month'); X=hubv(hubline); I=confirm_w(leg_ic(ics,50),C1,'month')
        legs={'U':[(a,b) for a,b,c in U],'L':[(a,b) for a,b,c in L],'X':[(a,b) for a,b,c in X],'I':[(a,b) for a,b,c in I]}
        with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TLH)
        r=score13(turns); lp=[r['lags_p'].get(i) for i in range(13)]; lt=[r['lags_t'].get(i) for i in range(13)]
        allv=[x for x in lp if x is not None]; tv=[x for x in lt if x is not None]
        P(f"\n{nm} — {tag}\n   onsets {lp} | all-13 mean {np.mean(allv):.1f} | within the month {sum(1 for x in allv if x<=31)}/13 | detected {len(r['lags_p'])}/13 | OTHER CALLS {[o[1] for o in r['other']]}")
        P(f"   peak dates {[r['errs_p'].get(i) for i in range(13)]} exact {sum(1 for e in r['errs_p'].values() if e==0)} within one {sum(1 for e in r['errs_p'].values() if abs(e)<=1)} | troughs median {np.median(tv):.0f} exact {sum(1 for e in r['errs_t'].values() if e==0)} early {sum(1 for x in tv if x<0)}")
        if tag=='CURRENT FILE':
            cond={(p,dd):c for v in [U,L,X,I] for p,dd,c in v}
            P("   carried by: "+" | ".join(f"{PK[i]:%Y-%m}:{r['opens'][i]['published']:%Y-%m-%d}{r['opens'][i]['leg']}({cond.get((r['opens'][i]['published'],r['opens'][i]['date']),'hub')})" for i in range(13) if i in r['opens']))
            keep=(U,L,X,I)
    return keep
full('v3.1 (the 6 September record)',[CRD])
K=full("v3.2 (+ the Department's own pre-1971 first prints, at the rule's OWN lines 0.45/0.25 — no new number)",[CRD],rt=True)
full('v3.2 PRICED VARIANT (a second, higher line 1.00/0.60 on the same leg — refused by the causal replay, see below)',[CRD],rt='two')
full('v3.2r (v3.2 with the hub on 0.43 — 2024 called 5 July, dated March, one month early)',[CRD],rt=True,hubline=0.43)
P("\nTHE PRE-1971 PROPOSAL, RE-READ ON WHAT WAS PUBLISHED AT THE TIME")
P("   The reconstruction the tool had been using before 1971 (Fieldhouse's monthly insured rate) is a current-vintage series: it prints on the")
P("   tenth of the following month and nobody in 1953 had it. Collection 59's national weekly first prints are the Department's own releases,")
P("   read from the printed issues, seasonally adjusted with factors fitted only on data already published, and available twelve days after the")
P("   week. Both are kept: the first prints where they reach (from January 1949) and the reconstruction where they do not (1948, and every week")
P("   the OCR could not recover). A call fires when either crosses.")
for ln in [0.45,1.00]:
    c=leg_rt(RT,ln); P(f"   first-print proposals at {ln}: {len(c)} before 1971 — {[d.strftime('%Y-%m') for _,d in c]}")
P("   PLATEAU: the line is identical anywhere in 0.40-0.50 and breaks at 0.55 (a January 1957 call). 0.45 is the rule's OWN line, already in")
P("   use on the modern file, so v3.2 introduces no new number at all. Carried past 1971 the same object makes a December 1975 call, so it")
P("   stops where the modern IURSA file begins.")
P("   THE SECOND LINE, PRICED AND REFUSED. A higher line (0.75-1.00) on the same leg buys 1957 from 40 to 33 days. The causal replay")
P("   (causal26.py) re-chooses that line at every turn using only the record before it, by the rule's own safest-end criterion: the past would")
P("   choose 1.50 at every fold, and at 1.50 the 1953 gain survives (62) while the 1957 gain does not (40). Seven days at 1957 are therefore")
P("   available only to someone who already knows 1957 is a recession. Refused. The nine days at 1953 need no new number and are causal.")
out.close()
