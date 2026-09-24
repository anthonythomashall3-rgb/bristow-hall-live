"""THE MONEY-MARKET SPREAD AS THE CREDIT OBJECT'S OWN PREDECESSOR. The Chicago Fed's credit subindex begins in 1971;
the one-month commercial paper rate over the three-month Treasury bill is weekly from April 1956 and the bankers'
acceptance spread from January 1954, and both are published the next day and never revised. Read as a THIRTEEN-WEEK
MEAN standing above its lowest value of the previous six months, the paper spread clears every quiet proposal window
on the whole record by fifty per cent. Here: the plateau in the line, the smoothing and the window; the date errors;
the live reading; and whether it replaces the credit subindex or sits beside it."""
exec(open('daily13.py').read().split('P("SPREADS BUILT AND SCREENED')[0].replace("out=open('daily13.out','w')","out=open('daily16.out','w')"))
def spread(a,b):
    aa=L25(a); bb=L25(b); idx=aa.index.union(bb.index)
    S=(aa.reindex(idx).ffill()-bb.reindex(idx).ffill()).dropna(); return S[S.index>=max(aa.index.min(),bb.index.min())]
CPB=spread('H0RIFSPPFM01NWF','WTB3MS'); BAB=spread('H1RIFSPABM03NWF','WTB3MS')
def obj(S,sm,wmon):
    per=max(1,int(round(float(np.median(np.diff(S.index.values).astype('timedelta64[D]').astype(int))))))
    Sm=S.rolling(sm).mean().dropna() if sm>1 else S
    return (Sm-Sm.rolling(max(4,int(wmon*30/per))).min()).dropna()
def go9e(nm,extra,hubline=0.50,rt=False,pct=50,vk=4,vb=4,vl=0.20,starts=29):
    G=vgap(vk,vb); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=vl,pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,0.45,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    F25=[x for x in leg_gap_mx2(gm,0.25,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    if rt: F45=F45+leg_rt(RT,0.45); F25=F25+leg_rt(RT,0.25)
    Hc,MX=mkpair3(starts,4,3,18); Hh=mkhours(2.0,1.20)
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
    P(f"{'OK ' if ok else 'BAD'} {nm:40s} {lp} MEAN {np.mean(av):.1f} (fp {np.mean(av2):.1f}) in31 {sum(1 for x in av if x<=31)}/13 ERR {ep} exact {sum(1 for e in ep if e==0)} others {[o[1] for r in res for o in r['other']][:4]}")
    return ok
D59=W.replace('24_bristow_rule_lab/workspace','59_dol_weekly_state_claims_1945-1983_2026-09')
RT=pd.read_csv(os.path.join(D59,'national_iur_realtime_sa_first_prints_1948_1983.csv'),index_col=0,parse_dates=True).iloc[:,0].dropna()
def leg_rt(s,pct,look=52,pub=12,stop='1971-01-01'):
    m=s.rolling(look,min_periods=look).min().shift(1); rel_=s-m; c=[]; armed=True
    for t,v in rel_.dropna().items():
        if armed and v>=pct: c.append((t+pd.Timedelta(days=pub),pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=0: armed=True
    return [x for x in c if x[1]<pd.Timestamp(stop)]
G=obj(CPB,13,6)
qs=sorted([(float(wseg(G,dd).max()),dd.strftime('%Y-%m')) for dd in QP if len(wseg(G,dd))],reverse=True)
P("THE PAPER SPREAD (one-month commercial paper less the three-month bill), thirteen-week mean, six-month rise")
P(f"   span {CPB.index.min().date()} -> {CPB.index.max().date()}, weekly, published the next day, never revised")
P(f"   quiet readings, highest first: {[(round(a,2),b) for a,b in qs[:8]]} ({len(qs)} of {len(QP)} quiet windows covered)")
P(f"   recession-window maxima: {[(PK[i].strftime('%Y-%m'),round(float(wseg(G,PK[i]).max()),2) if len(wseg(G,PK[i])) else None) for i in range(13)]}")
P(f"   2025-26 maximum {float(G[G.index>=pd.Timestamp('2025-01-01')].max()):.3f}; latest reading {float(G.iloc[-1]):.3f} on {G.index[-1].date()}")
P("\n=== v3.2 baseline, then the line swept ===")
go9e('v3.2 (credit subindex only)',[CRED],rt=True)
for ln in [0.70,0.80,0.90,0.95,1.00,1.05,1.10,1.20,1.30,1.45,1.60]: go9e(f'  paper spread >= {ln}',[CRED,dict(name='cpb',gap=G,line=ln,pub_lag_days=1)],rt=True)
P("\n=== the smoothing and the window, each at 1.5x its own quiet maximum ===")
for sm in [4,8,13,17,26]:
    for wmon in [3,6,9,12]:
        Gx=obj(CPB,sm,wmon); qm_=max([float(wseg(Gx,dd).max()) for dd in QP if len(wseg(Gx,dd))])
        go9e(f'  sm{sm} {wmon}m >= {qm_*1.5:.3f} (1.5x {qm_:.2f})',[CRED,dict(name='cpb',gap=Gx,line=qm_*1.5,pub_lag_days=1)],rt=True)
P("\n=== does it replace the credit subindex, or sit beside it? ===")
go9e('  paper spread ALONE (no credit subindex)',[dict(name='cpb',gap=G,line=0.953,pub_lag_days=1)],rt=True)
go9e('  both',[CRED,dict(name='cpb',gap=G,line=0.953,pub_lag_days=1)],rt=True)
P("\n=== the acceptance spread (from 1954, so it reaches 1957 and 1960) ===")
GB=obj(BAB,13,6); qb=sorted([(float(wseg(GB,dd).max()),dd.strftime('%Y-%m')) for dd in QP if len(wseg(GB,dd))],reverse=True)
P(f"   quiet readings: {[(round(a,2),b) for a,b in qb[:6]]}; recession maxima {[(PK[i].strftime('%Y-%m'),round(float(wseg(GB,PK[i]).max()),2) if len(wseg(GB,PK[i])) else None) for i in range(13)]}")
for ln in [1.01,1.10,1.21,1.35,1.50]: go9e(f'  acceptance spread >= {ln}',[CRED,dict(name='bab',gap=GB,line=ln,pub_lag_days=1)],rt=True)
go9e('  both spreads',[CRED,dict(name='cpb',gap=G,line=0.953,pub_lag_days=1),dict(name='bab',gap=GB,line=1.21,pub_lag_days=1)],rt=True)
P("\n=== and with the 2024 dating relaxed (hub 0.43) ===")
go9e('  v3.3 = v3.2 + paper spread, hub 0.43',[CRED,dict(name='cpb',gap=G,line=0.953,pub_lag_days=1)],rt=True,hubline=0.43)
out.close()
