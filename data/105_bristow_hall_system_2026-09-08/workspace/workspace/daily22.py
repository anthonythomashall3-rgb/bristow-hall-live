"""THINGS THAT ARE NOT SERIES: the tool's own SETTINGS that have never been swept in this line of work.
(a) THE HOURS PAIR's two lines (2.0 per cent off the twelve-month maximum, nondurable employment down 1.20 per cent
    over three months). It carries 1980 and 2001 and has never been swept here — it is the only demand object with
    data before 1959, so it is the only candidate that can reach 1957 and 1960 on the confirming side.
(b) THE PROPOSAL LOOK-BACK. Both insured-rate branches read the gap above a 52-WEEK minimum. Never swept.
(c) THE RE-ARM RULE. The 0.45 branch re-arms at zero; the low branch re-arms when an unconfirmed proposal's window
    closes. A leg that is disarmed cannot propose, and that is a candidate for the 1981 wait."""
exec(open('fast49.py').read().split("def full(")[0].replace("out=open('fast49.out','w')","out=open('daily22.out','w')"))
def sc(nm,extra,hubline=0.43,look45=52,look25=52,rearm45='zero',rearm25='window',hh=None):
    G=vgap(4,4); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=0.20,pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,0.45,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,0.45)
    F25=[x for x in leg_gap_mx2(gm,0.25,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,0.25)
    Hc,MX=mkpair3(29,4,3,18); Hh=hh if hh is not None else mkhours(2.0,1.20)
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
    C1=[Vc,Hh]+extra; C2=[Hc]+extra; res=[]
    for s,ics in [(s_cur,IC),(spl,ICfp)]:
        U=confirm_w(leg_gapL(s,0.45,look45,rearm=rearm45)+F45,C1,'month'); L=confirm_w(leg_gapL(s,0.25,look25,rearm=rearm25)+F25,C2,'month')
        X=hubv(hubline); I=confirm_w(leg_ic(ics,50),C1,'month')
        legs={'U':[(a,b) for a,b,c in U],'L':[(a,b) for a,b,c in L],'X':[(a,b) for a,b,c in X],'I':[(a,b) for a,b,c in I]}
        with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TLH)
        res.append((score13(turns),turns))
    early=[t for x in res for t in x[1] if t['kind']=='peak' and t['published']<pd.Timestamp('1948-06-01')]
    ok=all(len(x[0]['other'])==0 and len(x[0]['lags_p'])==13 for x in res) and not early
    r=res[0][0]; lp=[r['lags_p'].get(i) for i in range(13)]; ep=[r['errs_p'].get(i) for i in range(13)]
    av=[x for x in lp if x is not None]
    P(f"{'OK ' if ok else 'BAD'} {nm:40s} {lp} MEAN {np.mean(av):.1f} in31 {sum(1 for x in av if x<=31)}/13 ERR {ep} others {[o[1] for x in res for o in x[0]['other']][:3]}{' EARLY' if early else ''}")
    return ok,np.mean(av)
SPR=dict(name='paper spread',gap=GSP,line=LINE,pub_lag_days=1)
P("=== v3.3r baseline ==="); sc('v3.3r',[CRD,SPR])
P("\n=== (a) the hours pair's two lines, swept ===")
for a in [1.0,1.5,2.0,2.5,3.0]:
    for b in [0.60,0.90,1.20,1.60,2.00]:
        sc(f'  hours {a}% x nondurable {b}%',[CRD,SPR],hh=mkhours(a,b))
P("\n=== (b) the proposal look-back on each branch ===")
for l45 in [26,39,52,78,104]:
    sc(f'  0.45 branch look-back {l45}w',[CRD,SPR],look45=l45)
for l25 in [26,39,52,78,104]:
    sc(f'  low branch look-back {l25}w',[CRD,SPR],look25=l25)
P("\n=== (c) the re-arm rule on each branch ===")
for r45 in ['zero','window','line']:
    for r25 in ['zero','window','line']:
        sc(f'  re-arm 0.45={r45} low={r25}',[CRD,SPR],rearm45=r45,rearm25=r25)
out.close()
