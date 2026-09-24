"""A SCORING DEFECT, FOUND AND LOGGED (Rule Zero), AND THE FIRST-PRINT CLAIMS LEG RE-EXAMINED UNDER AN HONEST SCORER.
score13 ignores every peak turn published before 1 June 1948, so an object that opens a recession in 1947 is scored as
if it had said nothing. The shipped rule makes no such call, but the first-print initial-claims proposer at 30 per cent
does — 18 December 1947, dated December 1947 — and that is why 1948 "disappears" rather than being called late. Every
configuration below is therefore printed with EVERY peak turn it produces from 1946 on."""
exec(open('daily19.py').read().split('P("=== what the 30 per cent leg does to 1948 ===")')[0].replace("out=open('daily19.out','w')","out=open('daily20.out','w')"))
def full_score(x45,x25,hubline=0.50,extra=None):
    G_=vgap(4,4); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G_.index})
    Vc=dict(name='vac',gap=G_,line=0.20,pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,0.45,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,0.45)+x45
    F25=[x for x in leg_gap_mx2(gm,0.25,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,0.25)+x25
    Hc,MX=mkpair3(29,4,3,18); Hh=mkhours(2.0,1.20)
    def hubv(sl):
        calls=[]; armed=True
        for m,v in g.items():
            if m<pd.Timestamp('1948-06-01'): continue
            if armed and v>=sl:
                w=G_[(G_.index>=m-pd.DateOffset(months=6))&(G_.index<=m)]; hit=w[w>=0.20]
                if len(hit):
                    kk=hit.index[0]; sp=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
                    calls.append((max(sp,pubs[kk]),m-pd.DateOffset(months=3),'hub')); armed=False
            elif not armed and v<sl: armed=True
        return calls
    out_=[]
    for s,ics in [(s_cur,IC),(spl,ICfp)]:
        C1=[Vc,Hh]+(extra or []); C2=[Hc]+(extra or [])
        U=confirm_w(leg_gapL(s,0.45,52,rearm='zero')+F45,C1,'month'); L=confirm_w(leg_gapL(s,0.25,52,rearm='window')+F25,C2,'month')
        X=hubv(hubline); I=confirm_w(leg_ic(ics,50),C1,'month')
        legs={'U':[(a,b) for a,b,c in U],'L':[(a,b) for a,b,c in L],'X':[(a,b) for a,b,c in X],'I':[(a,b) for a,b,c in I]}
        with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TLH)
        out_.append((score13(turns),turns))
    return out_
def report(nm,x45,x25,hubline=0.50,extra=None):
    res=full_score(x45,x25,hubline,extra); r,turns=res[0]
    early=[t for t in turns if t['kind']=='peak' and t['published']<pd.Timestamp('1948-06-01')]
    early2=[t for t in res[1][1] if t['kind']=='peak' and t['published']<pd.Timestamp('1948-06-01')]
    lp=[r['lags_p'].get(i) for i in range(13)]; ep=[r['errs_p'].get(i) for i in range(13)]
    av=[x for x in lp if x is not None]
    ok=all(len(x[0]['other'])==0 and len(x[0]['lags_p'])==13 for x in res) and not early and not early2
    P(f"{'OK ' if ok else 'BAD'} {nm:36s} {lp} MEAN {np.mean(av):.1f} in31 {sum(1 for x in av if x<=31)}/13 ERR {ep} others {[o[1] for x in res for o in x[0]['other']][:3]} PRE-1948-06 CALLS {[(t['published'].strftime('%Y-%m-%d'),t['date'].strftime('%Y-%m')) for t in early+early2]}")
    return ok
G=obj(CPB,13,6); SPR=dict(name='cpb',gap=G,line=1.20,pub_lag_days=1)
P("=== the shipped rule, checked for the defect ===")
report('v3.2',[],[],extra=[CRED]); report('v3.2 + paper spread 1.20',[],[],extra=[CRED,SPR])
P("\n=== the first-print claims proposer, every configuration, honestly scored ===")
for look in [52,65,78,91,104]:
    for pctv in [25,30,35,40,50,60]:
        report(f'  IC-fp {pctv}% over {look}w',leg_icrt(pctv,look=look),leg_icrt(pctv,look=look),extra=[CRED,SPR])
out.close()
