# SPEED, stage 3: the single-week claims jump (K) confirmed ONLY by a market crash (the S&P 500 down 15% or more from its high of the prior 20 trading days, on the release day)
spx=_SPX.dropna(); crash=(1-spx/spx.rolling(20,min_periods=15).max().shift(1))*100
def leg_K(pct,look=52):
    s=ICfp.dropna(); rel_=((s/s.rolling(look,min_periods=look).min().shift(1)-1)*100).dropna(); c=[]; armed=True
    for t,v in rel_.items():
        if armed and v>=pct: c.append((rel_ic(t),pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=0: armed=True
    return c
def crash_on(day,line):
    s=crash[crash.index<=day]; return len(s)>0 and float(s.iloc[-1])>=line
def build_K(p,pct,cline):
    q=dict(p)
    G=vgap2(q['vk'],q['vb']); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=q['vl'],pubs=pubs)
    Hc,MX=mkpair3(q['starts'],q['half'],3,q['minw']); Hc=dict(Hc); Hc['line']=q['hline']; Hh=mkhours(q['hrs'],q['nd'])
    SP=dict(name='spread',gap=GSP,line=q['spr'],pubs=SP_PUBS)
    def hubv(sl,back):
        calls=[]; armed=True
        for m,v in g.items():
            if m<pd.Timestamp('1948-06-01'): continue
            if armed and v>=sl:
                w=G[(G.index>=m-pd.DateOffset(months=back))&(G.index<=m)]; hit=w[w>=q['vl']]
                sp=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
                ok=len(hit)>=2
                if ok:
                    known=pubs[(pubs.index<=m)&(pubs<=sp)]
                    ok=len(known)>0 and float(G.get(known.index.max(),np.nan))>=q['vl']
                if ok:
                    kk=hit.index[1]; calls.append((max(sp,pubs[kk]),m-pd.DateOffset(months=3),'hub')); armed=False
            elif not armed and v<sl: armed=True
        return calls
    C1=[Vc,Hh,SP]; C2=[Hc,SP]
    F45=[x for x in leg_gap_mx2(gm,q['u45'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,q['u45'])
    F25=[x for x in leg_gap_mx2(gm,q['low'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,q['low'])
    Kc=[(d,m) for d,m in leg_K(pct) if crash_on(d,cline)]
    legs={'U':[(a,b) for a,b,c in confirm_w(sorted(leg_gapL_c(spl,q['u45'],q['look'])+F45),C1,'month')],'L':[(a,b) for a,b,c in confirm_w(sorted(leg_gapL(spl,q['low'],52,rearm='window')+F25),C2,'month')],
          'X':[(a,b) for a,b,c in hubv(q['sahm'],q['hback'])],'I':[(a,b) for a,b,c in confirm_w(leg_ic_c(ICfp,q['ic']),C1,'month')],'K':Kc}
    if q.get('wline'): legs['W']=[(a,b) for a,b,c in confirm_w(leg_sv(q['wline'],rearm='zero'),C2,'month')]
    if q.get('wline2'): legs['V']=[(a,b) for a,b,c in confirm_w(leg_sv(q['wline2'],rearm='window'),C2,'month')]
    if q.get('bshare'): legs['B']=[(a,b) for a,b,c in confirm_w(leg_br(q['bshare']),C2,'month')]
    TL=dict(TLH); TL['R']=RC[q['rst']]; TL['T']=TC[q['tst']]; TL['Q']=QC[q['qst']]
    if q.get('cD') is not None: TL['C']=CMENU[(q['cD'],q['cn'],q['cs'])]
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TL)
    return score13(turns),turns,Kc
for pct in (25,30,35):
    for cline in (10,15,20):
        r,t,Kc=build_K(p0,pct,cline); report(f"K {pct}% + crash {cline}%",r,t); print('     K+crash proposals:',[(d.date().isoformat(),m.strftime('%Y-%m')) for d,m in Kc if d.year>=1962])
