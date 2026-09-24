"""EXPERIMENT (9 September 2026): what bounds the rule's speed on 2020, and would a single-week initial-claims
proposer move it - frozen at the walk-end lines, every other object unchanged. Reports every call outside a recession.
Run: /opt/homebrew/bin/python3 exp2020.py"""
import sys,pickle,io,contextlib
sys.argv=['exp2020.py','1962','2026','wexp']
src=open('walk40.py').read().split('# ---- the walk itself')[0]
exec(src)
p=pickle.load(open('cache/w40_carry.pkl','rb'))
print('lines',p)
def leg_ic1(s,pct,look=52):
    """single week of initial claims (first prints) pct above the 52-week low of the four-week mean; rearm at zero"""
    m4=s.rolling(4).mean(); rel_=(s/m4.rolling(look,min_periods=look).min().shift(1)-1)*100
    c=[]; armed=True
    for t,v in rel_.dropna().items():
        if armed and v>=pct: c.append((rel_ic(t),pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=0: armed=True
    return c
def build_x(p,pct):
    G=vgap2(p['vk'],p['vb']); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=p['vl'],pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,p['u45'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['u45'])
    F25=[x for x in leg_gap_mx2(gm,p['low'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['low'])
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
                    kk=hit.index[1]
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
    if pct is not None: legs['K']=[(a,b) for a,b,c in confirm_w(leg_ic1(ICfp,pct),C1,'month')]
    TL=dict(TLH); TL['R']=RC[p['rst']]; TL['T']=TC[p['tst']]; TL['Q']=QC[p['qst']]
    if p.get('cD') is not None: TL['C']=CMENU[(p['cD'],p['cn'],p['cs'])]
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TL)
    return turns
def report(turns,tag):
    pk=[x for x in turns if x['kind']=='peak']; fa=[]; opens={}
    for x in pk:
        hit=[i for i in range(len(PK)) if PK[i]-pd.DateOffset(months=6)<=x['date']<=TR[i]]
        if not hit: fa.append((x['published'].strftime('%Y-%m-%d'),x['leg']))
        else:
            i=hit[0]
            if i not in opens: opens[i]=(x['published'].strftime('%Y-%m-%d'),x['leg'])
    print(tag,'| false alarms:',fa)
    print('   opens:',[ (PK[i].strftime('%Y-%m'),opens.get(i)) for i in range(len(PK)) if PK[i].year>=1969])
base=build_x(p,None); report(base,'baseline (walk-end lines)')
print('single-week claims: first prints around March 2020:'); print(ICfp['2020-02-15':'2020-04-11'])
m4=ICfp.rolling(4).mean(); print('52-week low of the four-week mean before 14 March 2020:', float(m4.rolling(52,min_periods=52).min().shift(1)['2020-03-14']))
for pct in (25,30,33,35,38,40,45):
    raw=leg_ic1(ICfp,pct); print('pct',pct,'raw proposals since 1990:',[(a.strftime('%Y-%m-%d')) for a,b in raw if a.year>=1990])
    report(build_x(p,pct),'with K at %d%%'%pct)
