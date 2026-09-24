"""v3.4 RECORD SCRIPT. One setting nobody in this programme had ever swept — the LOOK-BACK WINDOW of the minimum on
the 0.45 branch, fixed at 52 weeks since the rule was built — turns out to be flat and clean from 91 to 208 weeks, and
at 91 weeks it takes July 1990 from +3 to -12 days: the tool calls the 1990 recession eighteen days before the peak
month ends. Also here: the causal replay of that window, the margins, and the deep branch priced and refused."""
exec(open('fast49.py').read().split("def full(")[0].replace("out=open('fast49.out','w')","out=open('fast50.out','w')"))
SPR=dict(name='paper spread',gap=GSP,line=LINE,pub_lag_days=1)
def full(nm,extra,look45=91,hubline=0.43,rt=True):
    G=vgap(4,4); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=0.20,pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,0.45,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    F25=[x for x in leg_gap_mx2(gm,0.25,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    if rt: F45=F45+leg_rt(RT,0.45); F25=F25+leg_rt(RT,0.25)
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
        U=confirm_w(leg_gapL(s,0.45,look45,rearm='zero')+F45,C1,'month'); L=confirm_w(leg_gapL(s,0.25,52,rearm='window')+F25,C2,'month')
        X=hubv(hubline); I=confirm_w(leg_ic(ics,50),C1,'month')
        legs={'U':[(a,b) for a,b,c in U],'L':[(a,b) for a,b,c in L],'X':[(a,b) for a,b,c in X],'I':[(a,b) for a,b,c in I]}
        with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TLH)
        r=score13(turns); lp=[r['lags_p'].get(i) for i in range(13)]; lt=[r['lags_t'].get(i) for i in range(13)]
        allv=[x for x in lp if x is not None]; tv=[x for x in lt if x is not None]
        early=[t for t in turns if t['kind']=='peak' and t['published']<pd.Timestamp('1948-06-01')]
        P(f"\n{nm} — {tag}\n   onsets {lp} | all-13 mean {np.mean(allv):.1f} | within the month {sum(1 for x in allv if x<=31)}/13 | detected {len(r['lags_p'])}/13 | OTHER CALLS {[o[1] for o in r['other']]} | before June 1948 {[(t['published'].strftime('%Y-%m-%d'),t['date'].strftime('%Y-%m')) for t in early]}")
        P(f"   peak dates {[r['errs_p'].get(i) for i in range(13)]} exact {sum(1 for e in r['errs_p'].values() if e==0)} within one {sum(1 for e in r['errs_p'].values() if abs(e)<=1)} | troughs median {np.median(tv):.0f} exact {sum(1 for e in r['errs_t'].values() if e==0)} early {sum(1 for x in tv if x<0)}")
        if tag=='CURRENT FILE':
            cond={(p,dd):c for v in [U,L,X,I] for p,dd,c in v}
            P("   carried by: "+" | ".join(f"{PK[i]:%Y-%m}:{r['opens'][i]['published']:%Y-%m-%d}{r['opens'][i]['leg']}({cond.get((r['opens'][i]['published'],r['opens'][i]['date']),'hub')})" for i in range(13) if i in r['opens']))
full('v3.3r (52-week look-back)',[CRD,SPR],look45=52)
full('v3.4 (91-week look-back) — SHIPPED',[CRD,SPR],look45=91)
P("\nTHE LOOK-BACK WINDOW, AND WHY 91 WEEKS IS THE SAFE CORNER")
P("   The 0.45 branch reads the insured rate's gap above the MINIMUM OF THE PREVIOUS 52 WEEKS. That 52 was inherited from")
P("   Sahm's twelve months and never swept in this programme. Swept now: 26 weeks costs 2001 (-2 -> +26); 39, 52 and 78")
P("   give the identical record; 91, 104, 117, 130, 156, 182 and 208 give the identical record AND take July 1990 from")
P("   +3 to -12 days. A longer look-back means a lower minimum and therefore an easier crossing, so the SAFEST member of")
P("   the clean plateau is its shortest: 91 weeks. The plateau is eight values wide.")
gap91=(s_cur-s_cur.rolling(91,min_periods=91).min().shift(1)).dropna()
gap52=(s_cur-s_cur.rolling(52,min_periods=52).min().shift(1)).dropna()
w90=gap91[(gap91.index>=pd.Timestamp('1990-01-01'))&(gap91.index<=pd.Timestamp('1990-12-31'))]
P(f"   1990: the 91-week gap first reaches 0.45 in the week of {w90[w90>=0.45].index[0].date()} against {gap52[(gap52.index>=pd.Timestamp('1990-01-01'))&(gap52.index<=pd.Timestamp('1991-06-30'))].pipe(lambda x: x[x>=0.45].index[0]).date()} for the 52-week gap")
qm={}
for look,gp in [(52,gap52),(91,gap91)]:
    qp=[dd for p_,dd in leg_gapL(s_cur,0.45,look,rearm='zero') if not any(p2-pd.DateOffset(months=6)<=dd<=t2 for p2,t2 in zip(PK,TR))]
    qm[look]=qp
    P(f"   quiet proposals made by the 0.45 branch at a {look}-week look-back: {len(qp)} — {[d.strftime('%Y-%m') for d in qp]}")
P("\nTHE DEEP BRANCH — PRICED AND REFUSED. A third insured-rate branch at 0.10-0.20 requiring TWO of the five demand")
P("   objects (vacancy, hours pair, housing pair, credit subindex, paper spread) instead of one is clean on both")
P("   vintages and reaches a mean of 0.1 DAYS — the tool would call the average recession on the last day of its peak")
P("   month. It is refused because of what it does to the DATES: 1981 five months early, 2001 four months early, 1973")
P("   three months early. At that point the object stops dating recessions and starts anticipating them, and this")
P("   programme's product is a date. Requiring three confirmers instead of two removes the date errors and also the")
P("   whole gain — it reduces exactly to v3.4. Recorded with its numbers.")
P("\nALSO REFUSED TODAY, WITH NUMBERS: the hours pair swept over 25 line pairs (the shipped 2.0 x 1.20 is on the safe")
P("   corner of its plateau; every looser nondurable line costs 1980 forty-seven days, every tighter one makes a March")
P("   1967 or August 1962 call); the low branch's look-back (26 and 39 weeks make 2002 and 2021 calls, 78 and 104 cost")
P("   1990); every re-arm rule other than the shipped pair (zero on the 0.45 branch, window on the low branch); corporate")
P("   bond spreads Baa-Aaa weekly from 1962 and monthly from 1919, Baa less the ten-year, Aaa less the ten-year, the")
P("   ten-year less the three-month bill and less the funds rate - 55 configurations, every one inert at a line that")
P("   clears the quiet windows, except the ten-year less funds which buys 1980 at two months of date error; and the")
P("   REALISED VOLATILITY of the S&P 500 daily from December 1927 at 21, 42 and 63 days, which fires in ZERO of thirteen")
P("   recessions at any line that clears the quiet months, because October 1987 sets that line at 91.5 annualised points.")
out.close()
