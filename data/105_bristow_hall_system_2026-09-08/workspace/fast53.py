"""PUSHING TO THE TARGET: every call inside the month, median under 30. The claims deep branch at 10 per cent needing
two demand objects buys 1981 (55 -> 27) and 2007 (67 -> 4) with the dates intact. What remains outside the month is
1953, 1957, 1960, 1969 and 2024. Three doors tried here: a lower claims line; the spread proposing alongside; and a
PRE-1971-ONLY deep branch on the Department's own first prints, which is the only object that exists at 1953 and 1957."""
exec(open('fast52.py').read().split('P("=== v3.5 real-time baseline ===")')[0].replace("out=open('fast52.out','w')","out=open('fast53.out','w')"))
def run2(nm,deep=None,n_deep=2,pre=None,n_pre=2,spread_line=None,hubline=0.43):
    G=vgap(4,4); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=0.20,pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,0.45,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,0.45)
    F25=[x for x in leg_gap_mx2(gm,0.25,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,0.25)
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
    C1=[Vc,Hh,SPR]; C2=[Hc,SPR]; ALL=[Vc,Hh,Hc,SPR]; res=[]
    for s,ics in [(spl,ICfp),(s_cur,IC)]:
        U=confirm_w(leg_gapL(s,0.45,91,rearm='zero')+F45,C1,'month'); L=confirm_w(leg_gapL(s,0.25,52,rearm='window')+F25,C2,'month')
        X=hubv(hubline); I=confirm_w(leg_ic(ics,50),C1,'month')
        legs={'U':[(a,b) for a,b,c in U],'L':[(a,b) for a,b,c in L],'X':[(a,b) for a,b,c in X],'I':[(a,b) for a,b,c in I]}
        if deep is not None:
            m4=ics.rolling(4).mean(); rel_=((m4/m4.rolling(52,min_periods=52).min().shift(1)-1)*100).dropna()
            cc=[]; armed=True
            for t,v in rel_.items():
                if armed and v>=deep: cc.append((t+pd.Timedelta(days=5),pd.Timestamp(t.year,t.month,1))); armed=False
                elif not armed and v<=0: armed=True
            legs['D']=[(a,b) for a,b,c in confirm_n(cc,ALL,n=n_deep)]
        if pre is not None:
            pp=[x for x in leg_gap_mx2(gm,pre,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,pre)
            legs['P']=[(a,b) for a,b,c in confirm_n(pp,ALL,n=n_pre)]
        if spread_line is not None:
            legs['S']=[(a,b) for a,b,c in confirm_n(leg_spread(spread_line),[Vc,Hh,Hc],n=1)]
        with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TLH)
        res.append((score13(turns),turns))
    early=[t for x in res for t in x[1] if t['kind']=='peak' and t['published']<pd.Timestamp('1948-06-01')]
    ok=all(len(x[0]['other'])==0 and len(x[0]['lags_p'])==13 for x in res) and not early
    r=res[0][0]; lp=[r['lags_p'].get(i) for i in range(13)]; ep=[r['errs_p'].get(i) for i in range(13)]
    av=[x for x in lp if x is not None]
    P(f"{'OK ' if ok else 'BAD'} {nm:40s} {lp} MED {np.median(av):.0f} MEAN {np.mean(av):.1f} in31 {sum(1 for x in av if x<=31)}/13 ERR {ep} others {[o[1] for x in res for o in x[0]['other']][:3]}{' EARLY' if early else ''}")
    return ok,np.median(av),sum(1 for x in av if x<=31)
P("=== baseline and the claims deep branch found in fast52 ===")
run2('v3.5 real-time'); run2('  + claims deep 10% x2',deep=10,n_deep=2)
P("\n=== a lower claims line ===")
for dl in [3,5,7.5]:
    for n in [2,3]: run2(f'  claims {dl}% x{n}',deep=dl,n_deep=n)
P("\n=== the claims deep branch PLUS the spread proposing ===")
for sl in [1.32,1.54,1.76]: run2(f'  claims 10%x2 + spread proposes {sl}',deep=10,n_deep=2,spread_line=sl)
P("\n=== a PRE-1971-ONLY deep branch on the Department's own first prints ===")
for pl in [0.10,0.15,0.20,0.30]:
    for n in [2,3]: run2(f'  pre-1971 insured {pl} x{n} (+claims 10%x2)',deep=10,n_deep=2,pre=pl,n_pre=n)
out.close()
