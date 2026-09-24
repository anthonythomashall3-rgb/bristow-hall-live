# F: the claims object's base floored at alpha x its trailing five-year median (a moving base), line 40, co-signer as v3.23
def leg_icF(pct,alpha,strong=STRONG_I):
    m4=ICfp.dropna().rolling(4).mean(); low=m4.rolling(52,min_periods=52).min().shift(1); med=m4.rolling(260,min_periods=156).median().shift(1)
    base=np.maximum(low,alpha*med); rel_=((m4/base-1)*100).dropna(); c=[]; armed=True
    for t,v in rel_.items():
        if armed and v>=pct:
            day=rel_ic(t)
            if v>=pct+IC_BAND or cosign(day): c.append((day,pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=0: armed=True
    return c,rel_
def build_F(p,pct,alpha):
    G=vgap2(p['vk'],p['vb']); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=p['vl'],pubs=pubs)
    Hc,MX=mkpair3(p['starts'],p['half'],3,p['minw']); Hc=dict(Hc); Hc['line']=p['hline']; Hh=mkhours(p['hrs'],p['nd'])
    SP=dict(name='spread',gap=GSP,line=p['spr'],pubs=SP_PUBS)
    def hubv(sl,back):
        calls=[]; armed=True
        for m,v in g.items():
            if m<pd.Timestamp('1948-06-01'): continue
            if armed and v>=sl:
                w=G[(G.index>=m-pd.DateOffset(months=back))&(G.index<=m)]; hit=w[w>=p['vl']]
                sp=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
                ok=len(hit)>=2
                if ok:
                    known=pubs[(pubs.index<=m)&(pubs<=sp)]
                    ok=len(known)>0 and float(G.get(known.index.max(),np.nan))>=p['vl']
                if ok:
                    kk=hit.index[1]; calls.append((max(sp,pubs[kk]),m-pd.DateOffset(months=3),'hub')); armed=False
            elif not armed and v<sl: armed=True
        return calls
    C1=[Vc,Hh,SP]; C2=[Hc,SP]
    F45=[x for x in leg_gap_mx2(gm,p['u45'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['u45'])
    F25=[x for x in leg_gap_mx2(gm,p['low'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['low'])
    Ic,relF=leg_icF(pct,alpha)
    legs={'U':[(a,b) for a,b,c in confirm_w(leg_gapL_c(spl,p['u45'],p['look'])+F45,C1,'month')],'L':[(a,b) for a,b,c in confirm_w(leg_gapL(spl,p['low'],52,rearm='window')+F25,C2,'month')],
          'X':[(a,b) for a,b,c in hubv(p['sahm'],p['hback'])],'I':[(a,b) for a,b,c in confirm_w(Ic,C1,'month')]}
    if p.get('wline'): legs['W']=[(a,b) for a,b,c in confirm_w(leg_sv(p['wline'],rearm='zero'),C2,'month')]
    if p.get('wline2'): legs['V']=[(a,b) for a,b,c in confirm_w(leg_sv(p['wline2'],rearm='window'),C2,'month')]
    if p.get('bshare'): legs['B']=[(a,b) for a,b,c in confirm_w(leg_br(p['bshare']),C2,'month')]
    TL=dict(TLH); TL['R']=RC[p['rst']]; TL['T']=TC[p['tst']]; TL['Q']=QC[p['qst']]
    if p.get('cD') is not None: TL['C']=CMENU[(p['cD'],p['cn'],p['cs'])]
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TL)
    return score13(turns),turns,relF
for alpha in (0.75,0.8,0.85,0.9,0.95):
    for pct in (40,35):
        r,t,relF=build_F(p0,pct,alpha); report(f"F line={pct} alpha={alpha}",r,t)
    print('   2022 max of the floored object:',round(float(relF['2022-06':'2022-10'].max()),1),'| 2001 Mar 15 week:',round(float(relF.get(pd.Timestamp('2001-03-10'),np.nan)),1),'| 2020 Mar 21:',round(float(relF.get(pd.Timestamp('2020-03-21'),np.nan)),1),'| 2008 Aug max:',round(float(relF['2008-06':'2008-09'].max()),1))
print('Q95 claims line in 2022:',round(float(_EQ[95]['2022-08'].iloc[-1]),1),'; object max Aug 2022: 43.9')
