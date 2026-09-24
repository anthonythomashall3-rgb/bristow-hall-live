# Q on every weekly proposer: each object's line = the q-th percentile of its own published history (expanding, causal)
def _expq_s(ser,q,minw=260):
    out=pd.Series(np.nan,index=ser.index); arr=ser.values
    for i in range(minw,len(arr)): out.iloc[i]=np.percentile(arr[:i],q)
    return out
_EQS={}
def eq(name,ser,q):
    key=(name,q)
    if key not in _EQS: _EQS[key]=_expq_s(ser,q)
    return _EQS[key]
GAPU=(spl-spl.rolling(52,min_periods=52).min().shift(1)).dropna()
GAPS=(SI-SI.rolling(52,min_periods=52).min().shift(1)).dropna()
def leg_gapQ(name,gap,q,pubfn,rearm='zero',cosigned=False,strong=STRONG_U):
    L=eq(name,gap,q); c=[]; armed=True; last=None
    for t,v in gap.items():
        line=L.get(t,np.nan)
        if np.isnan(line): continue
        if armed and v>=line:
            day=pubfn(t)
            if (not cosigned) or v>=line*strong or cosign(day): c.append((day,pd.Timestamp(t.year,t.month,1))); armed=False; last=t
        elif not armed:
            if rearm=='zero' and v<=0: armed=True
            elif rearm=='window' and v<line and t>=last+pd.DateOffset(months=4): armed=True
    return c
def build_Q(p,qI,qU,qL,qW=None):
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
    Uc=(leg_gapQ('U',GAPU,qU,rel_iu,'zero',True) if qU else leg_gapL_c(spl,p['u45'],p['look']))+F45
    Lc=(leg_gapQ('L',GAPU,qL,rel_iu,'window',False) if qL else leg_gapL(spl,p['low'],52,rearm='window'))+F25
    Ic=leg_icQ(qI) if qI else leg_ic_c(ICfp,p['ic'])
    legs={'U':[(a,b) for a,b,c in confirm_w(sorted(Uc),C1,'month')],'L':[(a,b) for a,b,c in confirm_w(sorted(Lc),C2,'month')],
          'X':[(a,b) for a,b,c in hubv(p['sahm'],p['hback'])],'I':[(a,b) for a,b,c in confirm_w(Ic,C1,'month')]}
    if qW:
        legs['W']=[(a,b) for a,b,c in confirm_w(leg_gapQ('W',GAPS,qW,lambda t:rel_iu(SW[t]),'zero'),C2,'month')]
        legs['V']=[(a,b) for a,b,c in confirm_w(leg_gapQ('V',GAPS,min(qW+2.5,99.5),lambda t:rel_iu(SW[t]),'window'),C2,'month')]
    else:
        if p.get('wline'): legs['W']=[(a,b) for a,b,c in confirm_w(leg_sv(p['wline'],rearm='zero'),C2,'month')]
        if p.get('wline2'): legs['V']=[(a,b) for a,b,c in confirm_w(leg_sv(p['wline2'],rearm='window'),C2,'month')]
    if p.get('bshare'): legs['B']=[(a,b) for a,b,c in confirm_w(leg_br(p['bshare']),C2,'month')]
    TL=dict(TLH); TL['R']=RC[p['rst']]; TL['T']=TC[p['tst']]; TL['Q']=QC[p['qst']]
    if p.get('cD') is not None: TL['C']=CMENU[(p['cD'],p['cn'],p['cs'])]
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TL)
    return score13(turns),turns
print('U point-gap expanding quantiles:',{q:{y:round(float(eq('U',GAPU,q)[str(y)].dropna().iloc[-1]),2) for y in (1980,1990,2000,2010,2020,2026)} for q in (90,95,97.5)})
print('==== Q on U and L (claims at 95)')
for qU in (90,95,97.5):
    for qL in (80,85,90):
        r,t=build_Q(p0,95,qU,qL); report(f"Q qI=95 qU={qU} qL={qL}",r,t)
print('==== Q on U only (claims 95, L fixed 0.20)')
for qU in (90,95,97.5): r,t=build_Q(p0,95,qU,None); report(f"Q qI=95 qU={qU} L=0.20",r,t)
print('==== Q on U, L and the survey week (claims 95)')
for qW in (90,95): r,t=build_Q(p0,95,95,85,qW); report(f"Q qI=95 qU=95 qL=85 qW={qW}",r,t)
