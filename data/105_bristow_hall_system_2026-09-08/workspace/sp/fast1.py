# SPEED, stage 1: (a) every proposer confirmed by any of the four demand-side confirmers; (b) the spread line below the grid's floor
BASE_R,BASE_T=build_v(p0)
BASE_PK={PK[i].strftime('%Y-%m'):(BASE_R['opens'][i]['published'],BASE_R['opens'][i]['leg']) for i in BASE_R['called']}
def report(tag,r,t):
    cells=[]
    for i in range(13):
        k=PK[i].strftime('%Y-%m')
        if i in r['lags_p']:
            d=r['opens'][i]['published']; leg=r['opens'][i]['leg']; base=BASE_PK.get(k); delta=(d-base[0]).days if base else None
            cells.append(f"{k}:{d:%Y-%m-%d}{leg}({'=' if delta==0 else ('%+d' % delta)})")
        else: cells.append(f"{k}:MISS")
    lp=[r['lags_p'][i] for i in range(4,13) if i in r['lags_p']]
    print(f"{tag:34s} called {len(r['called'])}/13 other {len(r['other'])} {r['other'][:5]} | med {np.median(lp) if lp else float('nan'):+.0f}d late(>31) {sum(1 for x in lp if x>31)} | "+' '.join(cells))
def build_x(p,conf_mode='v324',spr=None,hrs=None,nd=None,vl=None):
    q=dict(p)
    if spr is not None: q['spr']=spr
    if vl is not None: q['vl']=vl
    G=vgap2(q['vk'],q['vb']); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=q['vl'],pubs=pubs)
    Hc,MX=mkpair3(q['starts'],q['half'],3,q['minw']); Hc=dict(Hc); Hc['line']=q['hline']; Hh=mkhours(hrs if hrs else q['hrs'],nd if nd else q['nd'])
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
    C1=[Vc,Hh,SP]; C2=[Hc,SP]; ALL=[Vc,Hh,Hc,SP]
    if conf_mode=='all': C1=ALL; C2=ALL
    elif conf_mode=='C2+vac': C2=[Hc,SP,Vc]
    elif conf_mode=='C1+pair': C1=[Vc,Hh,SP,Hc]
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
report('v3.24 frozen',BASE_R,BASE_T)
for mode in ('all','C2+vac','C1+pair'):
    r,t=build_x(p0,mode); report(f"confirmers {mode}",r,t)
for spr in (0.85,0.8,0.7,0.6,0.5):
    r,t=build_x(p0,'v324',spr=spr); report(f"spread line {spr}",r,t)
for spr in (0.8,0.7):
    r,t=build_x(p0,'all',spr=spr); report(f"all + spread {spr}",r,t)
for hrs,nd in ((1.5,1.2),(1.5,0.8),(1.0,0.8),(2.0,0.8),(1.0,0.5)):
    r,t=build_x(p0,'v324',hrs=hrs,nd=nd); report(f"hours pair {hrs}/{nd}",r,t)
