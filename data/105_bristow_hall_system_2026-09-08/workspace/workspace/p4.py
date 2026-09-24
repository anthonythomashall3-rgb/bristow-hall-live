"""THE HOUSING PAIR'S LINE, WHICH HAS NEVER BEEN SWEPT AS A CONFIRMER. The 1969 call waits for the housing pair to
reach 1.00, which it does with January 1970 data published 6 February 1970, while the proposal was ready on 10 December
1969. The pair stood at 0.968 in September 1969 - published 18 October - so a line at 0.80 confirms two months before
the proposal and the call would fall to minus twenty-one days. The line is swept here across the whole record."""
import sys
sys.argv=['x','1962','2026']
exec(open('walk9.py').read().split('BASE9=dict(BASE)')[0].replace("out=open('walk9_%s_%s.out'%(sys.argv[3],sys.argv[1]),'w')","out=open('p4.out','w')"))
def build_h(p):
    G=vgap2(p['vk'],p['vb']); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=p['vl'],pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,p['u45'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['u45'])
    F25=[x for x in leg_gap_mx2(gm,p['low'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['low'])
    Hc,MX=mkpair3(p['starts'],p['half'],3,p['minw']); Hc=dict(Hc); Hc['line']=p['hline']
    Hh=mkhours(p['hrs'],p['nd'])
    SP=dict(name='spread',gap=GSP,line=p['spr'],pub_lag_days=1)
    def hubv(sl):
        calls=[]; armed=True
        for m,v in g.items():
            if m<pd.Timestamp('1948-06-01'): continue
            if armed and v>=sl:
                w=G[(G.index>=m-pd.DateOffset(months=6))&(G.index<=m)]; hit=w[w>=p['vl']]
                if len(hit):
                    kk=hit.index[0]; sp=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
                    calls.append((max(sp,pubs[kk]),m-pd.DateOffset(months=3),'hub')); armed=False
            elif not armed and v<sl: armed=True
        return calls
    C1=[Vc,Hh,SP]; C2=[Hc,SP]
    legs={'U':[(a,b) for a,b,c in confirm_w(leg_gapL(spl,p['u45'],p['look'],rearm='zero')+F45,C1,'month')],
          'L':[(a,b) for a,b,c in confirm_w(leg_gapL(spl,p['low'],52,rearm='window')+F25,C2,'month')],
          'X':[(a,b) for a,b,c in hubv(p['sahm'])],'I':[(a,b) for a,b,c in confirm_w(leg_ic(ICfp,p['ic']),C1,'month')]}
    if p.get('wline'): legs['W']=[(a,b) for a,b,c in confirm_w(leg_sv(p['wline'],rearm='zero'),C2,'month')]
    if p.get('wline2'): legs['V']=[(a,b) for a,b,c in confirm_w(leg_sv(p['wline2'],rearm='window'),C2,'month')]
    if p.get('bshare'): legs['B']=[(a,b) for a,b,c in confirm_w(leg_br(p['bshare']),C2,'month')]
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TLH)
    return score13(turns),turns
P(f"{'hline':>6s} {'spread':>7s} {'vac':>5s}  onsets 1948..2024                                              within month  false alarms")
import itertools
for hl,sp_,vl_ in itertools.product([0.95],[1.1],[0.20]):
    p=dict(BASE); p['deep']=999; p['wline']=0.30; p['wline2']=0.60; p['bshare']=0.50; p['hline']=hl; p['spr']=sp_; p['vl']=vl_
    r,t=build_h(p); lp=[r['lags_p'].get(i) for i in range(13)]
    v=[x for x in lp if x is not None]; v9=[lp[i] for i in range(4,13) if lp[i] is not None]
    fa=[]
    for x in t:
        if x['kind']!='peak' or x['published'].strftime('%Y-%m-%d') not in [d for d,_,_ in r['other']]: continue
        if not any(pk-pd.DateOffset(months=6)<=x['date']<=tr for pk,tr in zip(PK,TR)): fa.append(f"{x['published']:%Y-%m-%d}/{x['leg']}")
    if len(v)==13 and not fa:
        P(f"{hl:6.2f} {sp_:7.3f} {vl_:5.2f}  {lp}  {sum(1 for x in v if x<=31)}/13, from1961 {sum(1 for x in v9 if x<=31)}/9  clean")

P("\nnow the hub line, under housing 0.95 and spread 1.100 - the only turn still outside the month is 2024")
for sl in [0.50,0.45,0.43,0.40,0.37,0.3667,0.35,0.33]:
    p=dict(BASE); p['deep']=999; p['wline']=0.30; p['wline2']=0.60; p['bshare']=0.50; p['hline']=0.95; p['spr']=1.1; p['sahm']=sl
    r,t=build_h(p); lp=[r['lags_p'].get(i) for i in range(13)]
    fa=[]
    for x in t:
        if x['kind']!='peak' or x['published'].strftime('%Y-%m-%d') not in [d for d,_,_ in r['other']]: continue
        if not any(pk-pd.DateOffset(months=6)<=x['date']<=tr for pk,tr in zip(PK,TR)): fa.append(f"{x['published']:%Y-%m-%d} dated {x['date']:%Y-%m} by {x['leg']}")
    v=[x for x in lp if x is not None]; v9=[lp[i] for i in range(4,13) if lp[i] is not None]
    er=[r['errs_p'].get(i) for i in range(13)]
    P(f"hub {sl:6.4f}  {lp}  within {sum(1 for x in v if x<=31)}/13, from1961 {sum(1 for x in v9 if x<=31)}/9 | dates exact {sum(1 for e in er if e==0)} w1 {sum(1 for e in er if e is not None and abs(e)<=1)} | FALSE ALARMS {len(fa)} {fa}")
out.close()
