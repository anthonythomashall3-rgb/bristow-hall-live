"""THE THREE SLOW EARLY TURNS. 1953 at +62, 1957 at +122 and 1960 at +91. First, which side binds each of them under
v3.8. Second, the 1957 regression: it was +5 at a vacancy line of 0.20 and +122 at 0.25, and the only reason the line
was raised was to remove a single call in December 2025 that fires on a vacancy reading of exactly 0.200 in May 2025 -
six months before the Sahm month it confirms. A shorter confirmation window kills that call without touching the line."""
import sys
sys.argv=['x','1962','2026']
exec(open('walk9.py').read().split('BASE9=dict(BASE)')[0].replace("out=open('walk9_%s_%s.out'%(sys.argv[3],sys.argv[1]),'w')","out=open('p54.out','w')"))
def build_v(p):
    G=vgap2(p['vk'],p['vb']); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=p['vl'],pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,p['u45'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['u45'])
    F25=[x for x in leg_gap_mx2(gm,p['low'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['low'])
    Hc,MX=mkpair3(p['starts'],p['half'],3,p['minw']); Hc=dict(Hc); Hc['line']=p['hline']; Hh=mkhours(p['hrs'],p['nd'])
    SP=dict(name='spread',gap=GSP,line=p['spr'],pub_lag_days=1)
    def hubv(sl,back):
        calls=[]; armed=True
        for m,v in g.items():
            if m<pd.Timestamp('1948-06-01'): continue
            if armed and v>=sl:
                w=G[(G.index>=m-pd.DateOffset(months=back))&(G.index<=m)]; hit=w[w>=p['vl']]
                if len(hit):
                    kk=hit.index[0]; sp=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
                    calls.append((max(sp,pubs[kk]),m-pd.DateOffset(months=3),'hub')); armed=False
            elif not armed and v<sl: armed=True
        return calls
    C1=[Vc,Hh,SP]; C2=[Hc,SP]
    legs={'U':[(a,b) for a,b,c in confirm_w(leg_gapL(spl,p['u45'],p['look'],rearm='zero')+F45,C1,'month')],
          'L':[(a,b) for a,b,c in confirm_w(leg_gapL(spl,p['low'],52,rearm='window')+F25,C2,'month')],
          'X':[(a,b) for a,b,c in hubv(p['sahm'],p['hback'])],'I':[(a,b) for a,b,c in confirm_w(leg_ic(ICfp,p['ic']),C1,'month')]}
    if p.get('wline'): legs['W']=[(a,b) for a,b,c in confirm_w(leg_sv(p['wline'],rearm='zero'),C2,'month')]
    if p.get('wline2'): legs['V']=[(a,b) for a,b,c in confirm_w(leg_sv(p['wline2'],rearm='window'),C2,'month')]
    if p.get('bshare'): legs['B']=[(a,b) for a,b,c in confirm_w(leg_br(p['bshare']),C2,'month')]
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TLH)
    return score13(turns),turns
BASE38=dict(BASE); BASE38.update(deep=999,wline=0.30,wline2=0.60,bshare=0.50,hline=0.95,spr=1.1,sahm=0.3667,vl=0.25,hback=6)
def show(nm,p):
    r,t=build_v(p); lp=[r['lags_p'].get(i) for i in range(13)]
    fa=[]
    for x in t:
        if x['kind']!='peak' or x['published'].strftime('%Y-%m-%d') not in [d for d,_,_ in r['other']]: continue
        if not any(pk-pd.DateOffset(months=6)<=x['date']<=tr for pk,tr in zip(PK,TR)): fa.append(f"{x['published']:%Y-%m-%d}/{x['leg']}")
    v=[x for x in lp if x is not None]; v9=[lp[i] for i in range(4,13) if lp[i] is not None]
    er=[r['errs_p'].get(i) for i in range(13)]
    P(f"{nm:44s} {lp}  within {sum(1 for x in v if x<=31)}/13, from1961 {sum(1 for x in v9 if x<=31)}/9 | exact {sum(1 for e in er if e==0)} w1 {sum(1 for e in er if e is not None and abs(e)<=1)} | {'CLEAN' if (len(v)==13 and not fa) else 'FA '+str(fa)}")
    return r,t
BASE39=dict(BASE38); BASE39['hback']=5; BASE39['vl']=0.20
P("v3.9 = v3.8 with the hub window at five months and the vacancy line back at 0.20")
show('  v3.9',BASE39)
P("\n1960: the vacancy confirmation binds at 1960-08-30. What the paper spread was doing")
P("   spread max by month 1959-06..1960-09: "+", ".join(f"{m:%Y-%m}:{GSP[(GSP.index>=m)&(GSP.index<m+pd.DateOffset(months=1))].max():.3f}" for m in pd.date_range('1959-06-01','1960-09-01',freq='MS')))
P("\n1953: the proposal binds at 1953-10-10. Sweeping the two insured-rate lines and the look-back")
import itertools
for u45_,low_,look_ in itertools.product([0.55,0.45,0.35,0.30],[0.30,0.25,0.20,0.15],[52,78,91,130]):
    p=dict(BASE39); p['u45']=u45_; p['low']=low_; p['look']=look_
    r,t=build_v(p); lp=[r['lags_p'].get(i) for i in range(13)]
    fa=[]
    for x in t:
        if x['kind']!='peak' or x['published'].strftime('%Y-%m-%d') not in [d for d,_,_ in r['other']]: continue
        if not any(pk-pd.DateOffset(months=6)<=x['date']<=tr for pk,tr in zip(PK,TR)): fa.append(f"{x['published']:%Y-%m-%d}/{x['leg']}")
    v=[x for x in lp if x is not None]; v9=[lp[i] for i in range(4,13) if lp[i] is not None]
    if len(v)==13 and not fa and (lp[1]<62 or lp[3]<91):
        P(f"   u45 {u45_} low {low_} look {look_}: {lp}  within {sum(1 for x in v if x<=31)}/13, from1961 {sum(1 for x in v9 if x<=31)}/9  CLEAN")
P("\nand the spread line, which is what 1960 waits on")
for sp_ in [1.323,1.1,0.9,0.8,0.7,0.6,0.5]:
    p=dict(BASE39); p['spr']=sp_
    r,t=build_v(p); lp=[r['lags_p'].get(i) for i in range(13)]
    fa=[]
    for x in t:
        if x['kind']!='peak' or x['published'].strftime('%Y-%m-%d') not in [d for d,_,_ in r['other']]: continue
        if not any(pk-pd.DateOffset(months=6)<=x['date']<=tr for pk,tr in zip(PK,TR)): fa.append(f"{x['published']:%Y-%m-%d}/{x['leg']}")
    v=[x for x in lp if x is not None]; v9=[lp[i] for i in range(4,13) if lp[i] is not None]
    P(f"   spread {sp_:5.3f}: {lp}  within {sum(1 for x in v if x<=31)}/13, from1961 {sum(1 for x in v9 if x<=31)}/9 | {'CLEAN' if (len(v)==13 and not fa) else 'FA '+str(fa)}")
out.close()
