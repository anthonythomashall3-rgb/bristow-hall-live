"""WHICH ROW IS THE TOOL? The record has always been printed twice — 'CURRENT FILE' and 'FIRST PRINTS'. The difference
between them is ONLY the vintage of the two claims series: the current file reads today's revised insured rate and
today's initial claims; the first-print row reads the Department's ADVANCE figures from October 2002 and the spliced
first prints before. Everything else — the unemployment rate, housing starts, the hours pair, the vacancy, the paper
spread — is already read at its earliest vintage in BOTH rows. So the first-print row IS the mixed/real-time tool, and
the current-file row is the one that reads numbers nobody had. Here the two are compared turn by turn, and the 2007
mechanism is opened up."""
exec(open('fast51.py').read().split("full('v3.4")[0].replace("out=open('fast51.out','w')","out=open('vint2.out','w')"))
def rows(look45=91,hubline=0.43):
    G=vgap(4,4); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=0.20,pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,0.45,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,0.45)
    F25=[x for x in leg_gap_mx2(gm,0.25,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,0.25)
    Hc,MX=mkpair3(29,4,3,18); Hh=mkhours(2.0,1.20); SP=dict(name='paper spread',gap=GSP,line=LINE,pub_lag_days=1)
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
    C1=[Vc,Hh,SP]; C2=[Hc,SP]; out_=[]
    for tag,s,ics in [('current file',s_cur,IC),('first prints',spl,ICfp)]:
        U=confirm_w(leg_gapL(s,0.45,look45,rearm='zero')+F45,C1,'month'); L=confirm_w(leg_gapL(s,0.25,52,rearm='window')+F25,C2,'month')
        X=hubv(hubline); I=confirm_w(leg_ic(ics,50),C1,'month')
        legs={'U':[(a,b) for a,b,c in U],'L':[(a,b) for a,b,c in L],'X':[(a,b) for a,b,c in X],'I':[(a,b) for a,b,c in I]}
        with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TLH)
        out_.append((tag,score13(turns),{(p,dd):c for v in [U,L,X,I] for p,dd,c in v}))
    return out_
R=rows()
P(f"{'peak':9s} {'current file':>13s} {'REAL-TIME':>11s} {'diff':>6s}   what carries the real-time call")
for i in range(13):
    a=R[0][1]['lags_p'].get(i); b=R[1][1]['lags_p'].get(i)
    t=R[1][1]['opens'].get(i); c=R[1][2].get((t['published'],t['date']),'hub') if t else ''
    P(f"{PK[i]:%Y-%m}   {str(a):>13s} {str(b):>11s} {str((b-a) if (a is not None and b is not None) else ''):>6s}   {t['published']:%Y-%m-%d}{t['leg']}({c})" if t else f"{PK[i]:%Y-%m}   {a} {b}")
av=[R[0][1]['lags_p'][i] for i in range(13)]; bv=[R[1][1]['lags_p'][i] for i in range(13)]
P(f"\n   current-file mean {np.mean(av):.1f}, within the month {sum(1 for x in av if x<=31)}/13")
P(f"   REAL-TIME  mean {np.mean(bv):.1f}, within the month {sum(1 for x in bv if x<=31)}/13")
P(f"   the whole difference is {sum(1 for i in range(13) if av[i]!=bv[i])} turn(s): {[PK[i].strftime('%Y-%m') for i in range(13) if av[i]!=bv[i]]}")
P("\nTHE 2007 MECHANISM — the insured-rate gap, revised file against the Department's advance figures")
gc=(s_cur-s_cur.rolling(52,min_periods=52).min().shift(1)).dropna(); gf=(spl-spl.rolling(52,min_periods=52).min().shift(1)).dropna()
for nm,gx in [('revised file',gc),('advance figures',gf)]:
    w=gx[(gx.index>=pd.Timestamp('2007-06-01'))&(gx.index<=pd.Timestamp('2008-09-30'))]
    hit=w[w>=0.25]
    P(f"   {nm}: the 0.25 line is first reached in the week of {hit.index[0].date() if len(hit) else 'never'}; readings Nov 2007-Feb 2008 " + ", ".join(f"{d:%Y-%m-%d} {v:.2f}" for d,v in w[(w.index>=pd.Timestamp('2007-11-01'))&(w.index<=pd.Timestamp('2008-02-29'))].items()))
P("\nWHAT A PURE REAL-TIME RULE WOULD COST: the earliest vintage of each object (verified in fast51.out) —")
P("   unemployment rate 15 Mar 1960, housing starts 21 Jul 1960, hours pair 3 Nov 1961, JOLTS 11 Aug 2010, initial")
P("   claims and the insured rate Oct 2002 (advance) with the Department's own printed weekly first prints 1949-1971.")
P("   A rule that used ONLY series with a true vintage record would start in 1961 and lose the vacancy entirely before")
P("   2010. The mixed reading is not a convenience; it is the only way a rule can cover 1948-2026 at all.")
out.close()
