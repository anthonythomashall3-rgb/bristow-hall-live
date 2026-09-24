"""EXTRA PROPOSERS, PROPERLY RUN. The state-claims breadth object and the real-time-adjusted first-print national
initial claims, both from collection 59, added as pre-1971 proposals; and building permits as a demand confirmer."""
exec(open('daily16.py').read().split('G=obj(CPB,13,6)')[0].replace("out=open('daily16.out','w')","out=open('daily18.out','w')"))
G=obj(CPB,13,6); SPR=dict(name='cpb',gap=G,line=1.20,pub_lag_days=1)
D59=W.replace('24_bristow_rule_lab/workspace','59_dol_weekly_state_claims_1945-1983_2026-09')
def go9x(nm,extra,x45=None,x25=None,hubline=0.50,rt=True,pct=50,starts=29):
    G_=vgap(4,4); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G_.index})
    Vc=dict(name='vac',gap=G_,line=0.20,pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,0.45,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    F25=[x for x in leg_gap_mx2(gm,0.25,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    if rt: F45=F45+leg_rt(RT,0.45); F25=F25+leg_rt(RT,0.25)
    F45=F45+(x45 or []); F25=F25+(x25 or [])
    Hc,MX=mkpair3(starts,4,3,18); Hh=mkhours(2.0,1.20)
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
    C1=[Vc,Hh]+extra; C2=[Hc]+extra; res=[]
    for s,ics in [(s_cur,IC),(spl,ICfp)]:
        U=confirm_w(leg_gapL(s,0.45,52,rearm='zero')+F45,C1,'month'); L=confirm_w(leg_gapL(s,0.25,52,rearm='window')+F25,C2,'month'); X=hubv(hubline)
        I=confirm_w(leg_ic(ics,pct),C1,'month')
        legs={'U':[(a,b) for a,b,c in U],'L':[(a,b) for a,b,c in L],'X':[(a,b) for a,b,c in X],'I':[(a,b) for a,b,c in I]}
        with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TLH)
        res.append(score13(turns))
    ok=all(len(r['other'])==0 and len(r['lags_p'])==13 for r in res)
    lp=[res[0]['lags_p'].get(i) for i in range(13)]; ep=[res[0]['errs_p'].get(i) for i in range(13)]
    lp2=[res[1]['lags_p'].get(i) for i in range(13)]
    av=[x for x in lp if x is not None]; av2=[x for x in lp2 if x is not None]
    P(f"{'OK ' if ok else 'BAD'} {nm:38s} {lp} MEAN {np.mean(av):.1f} (fp {np.mean(av2):.1f}) in31 {sum(1 for x in av if x<=31)}/13 ERR {ep} exact {sum(1 for e in ep if e==0)} others {[o[1] for r in res for o in r['other']][:4]}")
    return ok
D=os.path.join(D59,'')
RT=pd.read_csv(os.path.join(D59,'national_iur_realtime_sa_first_prints_1948_1983.csv'),index_col=0,parse_dates=True).iloc[:,0].dropna()
def leg_rt(s,pct,look=52,pub=12,stop='1971-01-01'):
    m=s.rolling(look,min_periods=look).min().shift(1); rel_=s-m; c=[]; armed=True
    for t,v in rel_.dropna().items():
        if armed and v>=pct: c.append((t+pd.Timedelta(days=pub),pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=0: armed=True
    return [x for x in c if x[1]<pd.Timestamp(stop)]
P("=== baselines ==="); go9x('v3.2',[CRED]); go9x('v3.2 + paper spread 1.20',[CRED,SPR])
SW=pd.read_csv(os.path.join(D59,'ic_weekly_state_1945_1983_wide.csv'),index_col=0,parse_dates=True)
SW=SW.drop(columns=[c for c in SW.columns if c in ('PR','VI')])
r4=SW.rolling(4,min_periods=3).mean(); cov=(r4.notna()&r4.shift(52).notna()).sum(axis=1)
P("\n=== (b) state-claims breadth as an extra pre-1971 proposer ===")
for thr in [0.20,0.35,0.50]:
    yy=(r4/r4.shift(52)-1); br=((yy>thr).sum(axis=1)/cov.replace(0,np.nan))*100; br=br[cov>=25].dropna()
    def leg_br(pctb,pub=14,stop='1971-01-01'):
        c=[]; armed=True
        for t,v in br.items():
            if armed and v>=pctb: c.append((t+pd.Timedelta(days=pub),pd.Timestamp(t.year,t.month,1))); armed=False
            elif not armed and v<=pctb*0.5: armed=True
        return [x for x in c if x[1]<pd.Timestamp(stop)]
    for pctb in [50,60,70,80,90]:
        go9x(f'  breadth({int(thr*100)}%) >= {pctb}%',[CRED,SPR],x45=leg_br(pctb),x25=leg_br(pctb))
P("\n=== (c) first-print national initial claims, real-time adjusted, as a pre-1971 proposer ===")
NP=pd.read_csv(os.path.join(D59,'national_weekly_first_prints_1945_1983.csv'),parse_dates=['week']).set_index('week').sort_index()
lgc=np.log(NP['ic'].dropna()); tr=lgc.rolling(53,center=True,min_periods=40).mean(); dev=(lgc-tr).dropna()
fac={}
for t in lgc.index:
    wk=t.isocalendar()[1]
    hist=dev[(dev.index<pd.Timestamp(t.year,1,1))&(dev.index>=pd.Timestamp(t.year-7,1,1))]
    hw=hist[[x.isocalendar()[1]==wk for x in hist.index]]
    fac[t]=float(hw.median()) if len(hw)>=3 else 0.0
sa=np.exp(lgc-pd.Series(fac)).dropna()
P(f"   real-time adjusted first-print initial claims: {sa.index.min().date()} -> {sa.index.max().date()}, {len(sa)} weeks")
def leg_icrt(pctv,pub=5,look=52,stop='1971-01-01'):
    m4=sa.rolling(4).mean(); rel_=(m4/m4.rolling(look,min_periods=look).min().shift(1)-1)*100
    c=[]; armed=True
    for t,v in rel_.dropna().items():
        if armed and v>=pctv: c.append((t+pd.Timedelta(days=pub),pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=0: armed=True
    return [x for x in c if x[1]<pd.Timestamp(stop)]
for pctv in [30,40,50,60,75,100]:
    cl=leg_icrt(pctv); P(f"   IC first prints >= {pctv}%: {len(cl)} proposals — {[d.strftime('%Y-%m') for _,d in cl]}")
    go9x(f'  IC first prints >= {pctv}%',[CRED,SPR],x45=cl,x25=cl)
P("\n=== building permits as a demand confirmer ===")
PMf=W.replace('24_bristow_rule_lab/workspace','27_fred_monthly_early/unpacked/fred_monthly_early/PERMIT.csv')
if os.path.exists(PMf):
    x=pd.read_csv(PMf).iloc[:,:2]; x.columns=['d','v']; x['d']=pd.to_datetime(x['d'])
    PM=pd.to_numeric(x.set_index('d')['v'],errors='coerce').dropna()
    P(f"   PERMIT: {PM.index.min().date()} -> {PM.index.max().date()}, {len(PM)} months")
    lp_=np.log(PM); gpp=((lp_.rolling(12).max()-lp_.rolling(3).mean())*100).dropna()
    pubs=pd.Series({mm:(relH[mm] if mm in relH.index else pd.Timestamp(mm.year,mm.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=16)) for mm in gpp.index})
    for ln in [25,30,35,40,45,50]:
        go9x(f'  permits alone >= {ln} log points',[CRED,SPR,dict(name='perm',gap=gpp,line=ln,pubs=pubs)])
else: P("   PERMIT not found at "+PMf)
out.close()
