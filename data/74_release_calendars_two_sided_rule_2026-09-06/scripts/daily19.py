"""The first-print national initial-claims proposer, chased down. At 30 per cent it takes 1957 from 40 to 19 days and
1953 from 62 to 61, but the scorer loses 1948 — so the question is which of its own proposals costs 1948, and whether
the object survives once that is understood. Nothing here is allowed to be a fix by exclusion: if the leg has to be
switched off in a particular year to work, it is refused."""
exec(open('daily18.py').read().split('P("=== baselines ===")')[0].replace("out=open('daily18.out','w')","out=open('daily19.out','w')"))
NP=pd.read_csv(os.path.join(D59,'national_weekly_first_prints_1945_1983.csv'),parse_dates=['week']).set_index('week').sort_index()
lgc=np.log(NP['ic'].dropna()); tr=lgc.rolling(53,center=True,min_periods=40).mean(); dev=(lgc-tr).dropna()
fac={}
for t in lgc.index:
    wk=t.isocalendar()[1]
    hist=dev[(dev.index<pd.Timestamp(t.year,1,1))&(dev.index>=pd.Timestamp(t.year-7,1,1))]
    hw=hist[[x.isocalendar()[1]==wk for x in hist.index]]
    fac[t]=float(hw.median()) if len(hw)>=3 else 0.0
sa=np.exp(lgc-pd.Series(fac)).dropna()
def leg_icrt(pctv,pub=5,look=52,start=None,stop='1971-01-01'):
    m4=sa.rolling(4).mean(); rel_=(m4/m4.rolling(look,min_periods=look).min().shift(1)-1)*100
    c=[]; armed=True
    for t,v in rel_.dropna().items():
        if armed and v>=pctv: c.append((t+pd.Timedelta(days=pub),pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=0: armed=True
    return [x for x in c if x[1]<pd.Timestamp(stop) and (start is None or x[1]>=pd.Timestamp(start))]
G=obj(CPB,13,6); SPR=dict(name='cpb',gap=G,line=1.20,pub_lag_days=1)
def carry(nm,x45,x25,hubline=0.50):
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
    C1=[Vc,Hh,CRED,SPR]; C2=[Hc,CRED,SPR]
    U=confirm_w(leg_gapL(s_cur,0.45,52,rearm='zero')+F45,C1,'month'); L=confirm_w(leg_gapL(s_cur,0.25,52,rearm='window')+F25,C2,'month')
    X=hubv(hubline); I=confirm_w(leg_ic(IC,50),C1,'month')
    legs={'U':[(a,b) for a,b,c in U],'L':[(a,b) for a,b,c in L],'X':[(a,b) for a,b,c in X],'I':[(a,b) for a,b,c in I]}
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TLH)
    r=score13(turns); cond={(p,dd):c for v in [U,L,X,I] for p,dd,c in v}
    P(f"{nm}: lags {[r['lags_p'].get(i) for i in range(13)]} others {[o[:2] for o in r['other']]}")
    P("   all peak turns produced: "+" | ".join(f"{t['published']:%Y-%m-%d}{t['leg']} dated {t['date']:%Y-%m}" for t in turns if t['kind']=='peak' and t['published']<pd.Timestamp('1955-01-01')))
P("=== what the 30 per cent leg does to 1948 ===")
carry('v3.2+spread (no IC first prints)',[],[])
carry('with IC first prints 30%',leg_icrt(30),leg_icrt(30))
P("\n=== the leg's own proposals and the confirmers available to them ===")
for pctv in [20,25,30,35]:
    P(f"   {pctv}%: {[(p.strftime('%Y-%m-%d'),d.strftime('%Y-%m')) for p,d in leg_icrt(pctv)]}")
P("\n=== the leg on the 0.45 branch only, and on the low branch only ===")
for pctv in [25,30,35,40]:
    go9x(f'  IC-fp {pctv}% on the 0.45 branch only',[CRED,SPR],x45=leg_icrt(pctv),x25=[])
    go9x(f'  IC-fp {pctv}% on the low branch only',[CRED,SPR],x45=[],x25=leg_icrt(pctv))
P("\n=== window of the minimum, and the publication lag ===")
for look in [26,52,78,104]:
    for pctv in [30,40]:
        go9x(f'  IC-fp {pctv}% over {look} weeks',[CRED,SPR],x45=leg_icrt(pctv,look=look),x25=leg_icrt(pctv,look=look))
out.close()
