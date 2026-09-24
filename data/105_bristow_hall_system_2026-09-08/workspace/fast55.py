"""THE TWO DOORS THE DIAGNOSTIC OPENED. In the 2024 window the low branch reaches 1.20 times its line and the claims
object 2.57 times its 7.5 line, and the VACANCY stands at 2.28 times its own — but the architecture does not let the
vacancy confirm the low branch, so none of that can be used. That restriction was imposed long ago against a different
object set. And the claims deep branch requires TWO demand objects; in 1969 only two exist and the later of them is the
binding one. Both are re-tested here at the current settings."""
exec(open('fast53.py').read().split('P("=== baseline and the claims deep branch found in fast52 ===")')[0].replace("out=open('fast53.out','w')","out=open('fast55.out','w')"))
def run3(nm,deep=7.5,n_deep=2,vac_confirms_low=False,hours_confirms_low=False,hubline=0.43):
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
    C1=[Vc,Hh,SPR]; C2=[Hc,SPR]+([Vc] if vac_confirms_low else [])+([Hh] if hours_confirms_low else [])
    ALL=[Vc,Hh,Hc,SPR]; res=[]
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
        with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TLH)
        res.append((score13(turns),turns))
    early=[t for x in res for t in x[1] if t['kind']=='peak' and t['published']<pd.Timestamp('1948-06-01')]
    ok=all(len(x[0]['other'])==0 and len(x[0]['lags_p'])==13 for x in res) and not early
    r=res[0][0]; lp=[r['lags_p'].get(i) for i in range(13)]; ep=[r['errs_p'].get(i) for i in range(13)]
    av=[x for x in lp if x is not None]
    P(f"{'OK ' if ok else 'BAD'} {nm:44s} {lp} MED {np.median(av):.0f} MEAN {np.mean(av):.1f} in31 {sum(1 for x in av if x<=31)}/13 ERR {ep} others {[o[1] for x in res for o in x[0]['other']][:3]}{' EARLY' if early else ''}")
run3('v3.5 + claims deep 7.5% x2 (best so far)')
P("\n=== the vacancy allowed to confirm the LOW branch ===")
run3('  vacancy confirms low',vac_confirms_low=True)
run3('  hours pair confirms low',hours_confirms_low=True)
run3('  both confirm low',vac_confirms_low=True,hours_confirms_low=True)
P("\n=== the claims deep branch needing only ONE demand object ===")
for dl in [7.5,10,15,20,25,30,40]: run3(f'  claims {dl}% x1',deep=dl,n_deep=1)
P("\n=== and the two together ===")
for dl in [7.5,10,15,20]: run3(f'  claims {dl}% x1 + vacancy confirms low',deep=dl,n_deep=1,vac_confirms_low=True)
out.close()
