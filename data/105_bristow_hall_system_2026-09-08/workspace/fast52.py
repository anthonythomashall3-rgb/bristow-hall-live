"""TARGET: EVERY CALL INSIDE THE MONTH, MEDIAN UNDER 30 DAYS. Real-time row. Three untested doors.
(C) THE SPREAD AS A PROPOSER, not a confirmer — the architecture has always had supply propose and demand confirm; the
    reverse has never been run. The paper spread moves early, so if a labour object confirms it the call could land
    before the labour object could have proposed.
(D) THE MODERN STATE CLAIMS PANEL as a proposer (53 states, 1971 on) — breadth was refused BEFORE 1971 on a June 1950
    call, and never tried after.
(E) A CLAIMS-ONLY DEEP BRANCH — initial claims at a much lower line requiring TWO demand objects, which is the deep
    branch of §5x narrowed to the one proposer whose dating was never the problem."""
exec(open('fast51.py').read().split("full('v3.4")[0].replace("out=open('fast51.out','w')","out=open('fast52.out','w')"))
SPR=dict(name='paper spread',gap=GSP,line=LINE,pub_lag_days=1)
def confirm_n(calls,confs,n=1,back=6,fwd=4):
    out_=[]
    for p_,dd in calls:
        lo=dd-pd.DateOffset(months=back); hi=dd+pd.DateOffset(months=fwd)+pd.offsets.MonthEnd(0); pubs_=[]
        for c in confs:
            gp=c['gap']; w=gp[(gp.index>=lo)&(gp.index<=hi)]; hit=w[w>=c['line']]
            if not len(hit): continue
            k=hit.index[0]
            if 'pubs' in c and c['pubs'] is not None and k in c['pubs'].index: pubs_.append((c['pubs'][k],c['name']))
            elif 'pub_lag_days' in c: pubs_.append((k+pd.Timedelta(days=c['pub_lag_days']),c['name']))
            else: pubs_.append((k,c['name']))
        if len(pubs_)<n: continue
        pubs_.sort(); out_.append((max(p_,pubs_[n-1][0]),dd,'+'.join(x[1] for x in pubs_[:n])))
    return out_
def leg_spread(line,pub=1,rearm=0.0):
    """the paper spread PROPOSING: it crosses, and a labour object must then confirm"""
    c=[]; armed=True
    for t,v in GSP.items():
        if armed and v>=line: c.append((t+pd.Timedelta(days=pub),pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=rearm: armed=True
    return c
def run(nm,extra_legs=None,deep=None,n_deep=2,hubline=0.43,look45=91):
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
    C1=[Vc,Hh,SPR]; C2=[Hc,SPR]; res=[]
    for s,ics in [(spl,ICfp),(s_cur,IC)]:
        U=confirm_w(leg_gapL(s,0.45,look45,rearm='zero')+F45,C1,'month'); L=confirm_w(leg_gapL(s,0.25,52,rearm='window')+F25,C2,'month')
        X=hubv(hubline); I=confirm_w(leg_ic(ics,50),C1,'month')
        legs={'U':[(a,b) for a,b,c in U],'L':[(a,b) for a,b,c in L],'X':[(a,b) for a,b,c in X],'I':[(a,b) for a,b,c in I]}
        if extra_legs is not None:
            legs['S']=[(a,b) for a,b,c in confirm_n(extra_legs,[Vc,Hh,Hc],n=1)]
        if deep is not None:
            m4=ics.rolling(4).mean(); rel_=((m4/m4.rolling(52,min_periods=52).min().shift(1)-1)*100).dropna()
            cc=[]; armed=True
            for t,v in rel_.items():
                if armed and v>=deep: cc.append((t+pd.Timedelta(days=5),pd.Timestamp(t.year,t.month,1))); armed=False
                elif not armed and v<=0: armed=True
            legs['D']=[(a,b) for a,b,c in confirm_n(cc,[Vc,Hh,Hc,SPR],n=n_deep)]
        with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TLH)
        res.append((score13(turns),turns))
    early=[t for x in res for t in x[1] if t['kind']=='peak' and t['published']<pd.Timestamp('1948-06-01')]
    ok=all(len(x[0]['other'])==0 and len(x[0]['lags_p'])==13 for x in res) and not early
    r=res[0][0]; lp=[r['lags_p'].get(i) for i in range(13)]; ep=[r['errs_p'].get(i) for i in range(13)]
    av=[x for x in lp if x is not None]
    P(f"{'OK ' if ok else 'BAD'} {nm:38s} {lp} MED {np.median(av):.0f} MEAN {np.mean(av):.1f} in31 {sum(1 for x in av if x<=31)}/13 ERR {ep} others {[o[1] for x in res for o in x[0]['other']][:3]}{' EARLY' if early else ''}")
    return ok,np.median(av),sum(1 for x in av if x<=31)
P("=== v3.5 real-time baseline ==="); run('v3.5 real-time')
P("\n=== (C) the paper spread as a PROPOSER, confirmed by a labour object ===")
qs=sorted([(float(wseg(GSP,dd).max()),dd.strftime('%Y-%m')) for dd in QP if len(wseg(GSP,dd))],reverse=True)
P(f"   its quiet maximum is {qs[0][0]:.3f}; lines tried are multiples of it")
for mult in [1.5,1.75,2.0,2.5,3.0]:
    run(f'  spread proposes at {qs[0][0]*mult:.2f}',extra_legs=leg_spread(qs[0][0]*mult))
P("\n=== (E) a claims-only deep branch: initial claims low, TWO demand objects required ===")
for dl in [10,15,20,25,30]:
    for n in [2,3]:
        run(f'  claims {dl}% needing {n} confirmers',deep=dl,n_deep=n)
out.close()
