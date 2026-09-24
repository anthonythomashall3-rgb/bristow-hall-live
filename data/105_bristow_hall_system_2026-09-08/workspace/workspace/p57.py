"""THE THREE SLOW EARLY TURNS. 1953 at +62, 1957 at +122 and 1960 at +91. First, which side binds each of them under
v3.8. Second, the 1957 regression: it was +5 at a vacancy line of 0.20 and +122 at 0.25, and the only reason the line
was raised was to remove a single call in December 2025 that fires on a vacancy reading of exactly 0.200 in May 2025 -
six months before the Sahm month it confirms. A shorter confirmation window kills that call without touching the line."""
import sys
sys.argv=['x','1962','2026']
exec(open('walk9.py').read().split('BASE9=dict(BASE)')[0].replace("out=open('walk9_%s_%s.out'%(sys.argv[3],sys.argv[1]),'w')","out=open('p57.out','w')"))
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
    if p.get('sline'):
        mm=lh.rolling(3).mean(); mx12=lh.rolling(12).max()
        ss=(((mx12-mm)/mx12)*100).dropna()
        St=dict(name='starts alone',gap=ss,line=p['sline'],pub_day=18)
        C1=C1+[St]; C2=C2+[St]
    legs={'U':[(a,b) for a,b,c in confirm_w(leg_gapL(spl,p['u45'],p['look'],rearm='zero')+F45,C1,'month')],
          'L':[(a,b) for a,b,c in confirm_w(leg_gapL(spl,p['low'],52,rearm='window')+F25,C2,'month')],
          'X':[(a,b) for a,b,c in hubv(p['sahm'],p['hback'])],'I':[(a,b) for a,b,c in confirm_w(leg_ic(ICfp,p['ic']),C1,'month')]}
    if p.get('wline'): legs['W']=[(a,b) for a,b,c in confirm_w(leg_sv(p['wline'],rearm='zero'),C2,'month')]
    if p.get('wline2'): legs['V']=[(a,b) for a,b,c in confirm_w(leg_sv(p['wline2'],rearm='window'),C2,'month')]
    if p.get('bshare'): legs['B']=[(a,b) for a,b,c in confirm_w(leg_br(p['bshare']),C2,'month')]
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TLH)
    return score13(turns),turns
BASE38=dict(BASE); BASE38.update(deep=999,wline=0.30,wline2=0.60,bshare=0.50,hline=0.95,spr=1.1,sahm=0.3667,vl=0.20,hback=5)
def show(nm,p):
    r,t=build_v(p); lp=[r['lags_p'].get(i) for i in range(13)]
    fa=[]
    for x in t:
        if x['kind']!='peak' or x['published'].strftime('%Y-%m-%d') not in [d for d,_,_ in r['other']]: continue
        if not any(pk-pd.DateOffset(months=6)<=x['date']<=tr for pk,tr in zip(PK,TR)): fa.append(f"{x['published']:%Y-%m-%d}/{x['leg']}")
    v=[x for x in lp if x is not None]; v9=[lp[i] for i in range(4,13) if lp[i] is not None]
    er=[r['errs_p'].get(i) for i in range(13)]
    P(f"{nm:46s} {lp}  within {sum(1 for x in v if x<=31)}/13, from1961 {sum(1 for x in v9 if x<=31)}/9 | exact {sum(1 for e in er if e==0)} w1 {sum(1 for e in er if e is not None and abs(e)<=1)} | {'CLEAN' if (len(v)==13 and not fa) else 'FA '+str(fa)}")
P("housing STARTS on their own as a confirmer. The pair does not exist until 1961; starts do, and 1960 waits on the vacancy")
mm=lh.rolling(3).mean(); mx12=lh.rolling(12).max(); ss=(((mx12-mm)/mx12)*100).dropna()
P(f"   starts-below-max series from {ss.index.min():%Y-%m}; readings 1959-06..1960-08: "+", ".join(f"{m:%Y-%m}:{ss.get(m,float('nan')):.1f}" for m in pd.date_range('1959-06-01','1960-08-01',freq='MS')))
show('  v3.9 for reference',BASE38)
for sl_ in [35,30,25,20,17,15,12,10]:
    p=dict(BASE38); p['sline']=sl_
    show(f'  starts alone {sl_}% below their 12-month max',p)
out.close()
