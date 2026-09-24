"""EXPERIMENT 3 (9 September 2026): THE CO-SIGNER. A near-line proposal from an administrative object (the claims
object within a band above its line; the 91-week insured rate within a band above its line) must be co-signed by the
household survey: the three-month average of the unemployment rate at least THR above its low of the prior twelve
months, as last published on the proposal day (first prints). A strong proposal (above the band) needs no co-signer.
Frozen at the walk-end lines, then with the two lines lowered. Reports calls outside a recession and the openings.
Run: /opt/homebrew/bin/python3 exp_cosign.py"""
import sys
sys.argv=['exp_cosign.py','1962','2026','m41']
exec(open('exp2020.py').read().split("base=build_x(p,None)")[0])
gpub=pd.Series({rel[m]:float(g[m]) for m in g.index if m in rel}).sort_index()
def cosign(day,thr):
    s=gpub[gpub.index<=day]; return len(s)>0 and float(s.iloc[-1])>=thr
def leg_ic_c(s,pct,band,thr,look=52):
    m4=s.rolling(4).mean(); rel_=(m4/m4.rolling(look,min_periods=look).min().shift(1)-1)*100
    c=[]; armed=True
    for t,v in rel_.dropna().items():
        if armed and v>=pct:
            day=rel_ic(t)
            if v>=pct+band or cosign(day,thr): c.append((day,pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=0: armed=True
    return c
def leg_gapL_c(s,line,look,band,thr):
    gap=(s-s.rolling(look,min_periods=look).min().shift(1)).dropna(); c=[]; armed=True
    for t,v in gap.items():
        if armed and v>=line:
            day=rel_iu(t)
            if v>=line+band or cosign(day,thr): c.append((day,pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=0: armed=True
    return c
def build_c(p,thr,icband=15.0,uband=0.2,cos_I=True,cos_U=True):
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
    U=(leg_gapL_c(spl,p['u45'],p['look'],uband,thr) if cos_U else leg_gapL(spl,p['u45'],p['look'],rearm='zero'))+F45
    I=leg_ic_c(ICfp,p['ic'],icband,thr) if cos_I else leg_ic(ICfp,p['ic'])
    legs={'U':[(a,b) for a,b,c in confirm_w(U,C1,'month')],
          'L':[(a,b) for a,b,c in confirm_w(leg_gapL(spl,p['low'],52,rearm='window')+F25,C2,'month')],
          'X':[(a,b) for a,b,c in hubv(p['sahm'],p['hback'])],'I':[(a,b) for a,b,c in confirm_w(I,C1,'month')]}
    if p.get('wline'): legs['W']=[(a,b) for a,b,c in confirm_w(leg_sv(p['wline'],rearm='zero'),C2,'month')]
    if p.get('wline2'): legs['V']=[(a,b) for a,b,c in confirm_w(leg_sv(p['wline2'],rearm='window'),C2,'month')]
    if p.get('bshare'): legs['B']=[(a,b) for a,b,c in confirm_w(leg_br(p['bshare']),C2,'month')]
    TL=dict(TLH); TL['R']=RC[p['rst']]; TL['T']=TC[p['tst']]; TL['Q']=QC[p['qst']]
    if p.get('cD') is not None: TL['C']=CMENU[(p['cD'],p['cn'],p['cs'])]
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TL)
    return turns
print('co-signer readings (unemployment gap, first prints) as published: Mar 2001 report',[(d.strftime('%Y-%m-%d'),v) for d,v in gpub['2001-02':'2001-05'].items()])
print('  Jul-Sep 1990:',[(d.strftime('%Y-%m-%d'),v) for d,v in gpub['1990-06':'1990-09'].items()],' Mar-May 2023:',[(d.strftime('%Y-%m-%d'),v) for d,v in gpub['2023-03':'2023-05'].items()],' Jul-Oct 2022:',[(d.strftime('%Y-%m-%d'),v) for d,v in gpub['2022-07':'2022-10'].items()])
report(build_x(p,None),'baseline, walk-end lines, no co-signer')
for thr in (0.2,0.3):
    report(build_c(p,thr),'co-signer %.1f at the walk-end lines'%thr)
    for name,q in [('ic 40',dict(p,ic=40)),('ic 35',dict(p,ic=35)),('u45 0.35',dict(p,u45=0.35)),('u45 0.30',dict(p,u45=0.30)),('ic 35 + u45 0.35',dict(p,ic=35,u45=0.35)),('ic 40 + u45 0.35',dict(p,ic=40,u45=0.35))]:
        report(build_c(q,thr),'co-signer %.1f, %s'%(thr,name))
