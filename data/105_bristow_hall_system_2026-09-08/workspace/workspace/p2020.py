"""THE HOUSING PAIR'S LINE, WHICH HAS NEVER BEEN SWEPT AS A CONFIRMER. The 1969 call waits for the housing pair to
reach 1.00, which it does with January 1970 data published 6 February 1970, while the proposal was ready on 10 December
1969. The pair stood at 0.968 in September 1969 - published 18 October - so a line at 0.80 confirms two months before
the proposal and the call would fall to minus twenty-one days. The line is swept here across the whole record."""
import sys
sys.argv=['x','1962','2026']
exec(open('walk9.py').read().split('BASE9=dict(BASE)')[0].replace("out=open('walk9_%s_%s.out'%(sys.argv[3],sys.argv[1]),'w')","out=open('p2020.out','w')"))
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
P("the 2020 turn: which leg calls it, and what each leg had ready")
for hl in [1.00,0.95]:
    p=dict(BASE); p['deep']=999; p['wline']=0.30; p['wline2']=0.60; p['bshare']=0.50; p['hline']=hl
    r,t=build_h(p)
    P(f"\n   housing line {hl}: 2020 called {r['opens'][11]['published']:%Y-%m-%d} dated {r['opens'][11]['date']:%Y-%m} by {r['opens'][11]['leg']} (lag {r['lags_p'][11]:+d})")
    for x in t:
        if x['kind']=='peak' and pd.Timestamp('2020-01-01')<=x['published']<=pd.Timestamp('2020-09-01'):
            P(f"      call {x['published']:%Y-%m-%d} dated {x['date']:%Y-%m} by {x['leg']}")
P("\nthe claims leg on its own through the 2020 turn (line ic=50 per cent above the 52-week minimum)")
ic=leg_ic(ICfp,50)
for pp,dd in [(a,b) for a,b in [(x[0],x[1]) for x in ic] if pd.Timestamp('2020-01-01')<=a<=pd.Timestamp('2020-08-01')]:
    P(f"   proposal {pp:%Y-%m-%d} dated {dd:%Y-%m}")
P("\nthe survey-week and breadth objects through the 2020 turn")
sv=leg_sv(0.30,rearm='zero'); br=leg_br(0.50)
P("   survey week: "+", ".join(f"{a:%Y-%m-%d}/{b:%Y-%m}" for a,b in sv if pd.Timestamp('2020-01-01')<=a<=pd.Timestamp('2020-09-01')))
P("   breadth: "+", ".join(f"{a:%Y-%m-%d}/{b:%Y-%m}" for a,b in br if pd.Timestamp('2020-01-01')<=a<=pd.Timestamp('2020-09-01')))
out.close()
