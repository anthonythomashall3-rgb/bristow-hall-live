# SPEED, stage 2: housing starts ALONE as a demand-side confirmer (three-month mean below the twelve-month high, log points)
HS_GAP=(lh.rolling(12).max()-lh.rolling(3).mean()).dropna()
HS_PUBS=pd.Series({m:relH[m] for m in HS_GAP.index if m in relH.index})
HS_GAP=HS_GAP[HS_GAP.index.isin(HS_PUBS.index)]
print('starts-only object: months at >=30:',{y:int((HS_GAP[str(y)]>=30).sum()) for y in (1966,1969,1973,1974,1979,1980,1981,1982,1989,1990,1991,2006,2007,2008,2009,2022,2023,2024)})
def build_hs(p,line,where='C2'):
    q=dict(p)
    G=vgap2(q['vk'],q['vb']); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=q['vl'],pubs=pubs)
    Hc,MX=mkpair3(q['starts'],q['half'],3,q['minw']); Hc=dict(Hc); Hc['line']=q['hline']; Hh=mkhours(q['hrs'],q['nd'])
    SP=dict(name='spread',gap=GSP,line=q['spr'],pubs=SP_PUBS); HS=dict(name='starts',gap=HS_GAP,line=line,pubs=HS_PUBS)
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
    if where in ('C2','both'): C2=C2+[HS]
    if where in ('C1','both'): C1=C1+[HS]
    F45=[x for x in leg_gap_mx2(gm,q['u45'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,q['u45'])
    F25=[x for x in leg_gap_mx2(gm,q['low'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,q['low'])
    legs={'U':[(a,b) for a,b,c in confirm_w(sorted(leg_gapL_c(spl,q['u45'],q['look'])+F45),C1,'month')],'L':[(a,b) for a,b,c in confirm_w(sorted(leg_gapL(spl,q['low'],52,rearm='window')+F25),C2,'month')],
          'X':[(a,b) for a,b,c in hubv(q['sahm'],q['hback'])],'I':[(a,b) for a,b,c in confirm_w(leg_ic_c(ICfp,q['ic']),C1,'month')]}
    if q.get('wline'): legs['W']=[(a,b) for a,b,c in confirm_w(leg_sv(q['wline'],rearm='zero'),C2,'month')]
    if q.get('wline2'): legs['V']=[(a,b) for a,b,c in confirm_w(leg_sv(q['wline2'],rearm='window'),C2,'month')]
    if q.get('bshare'): legs['B']=[(a,b) for a,b,c in confirm_w(leg_br(q['bshare']),C2,'month')]
    TL=dict(TLH); TL['R']=RC[q['rst']]; TL['T']=TC[q['tst']]; TL['Q']=QC[q['qst']]
    if q.get('cD') is not None: TL['C']=CMENU[(q['cD'],q['cn'],q['cs'])]
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TL)
    return score13(turns),turns
for line in (26,28,30,32,34,36):
    for where in ('C2','both'):
        r,t=build_hs(p0,line,where); report(f"starts-only {line} in {where}",r,t)
