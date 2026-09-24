"""WALK 52 - WALK 51 WITH THE CO-SIGNER CLAUSE (10 September 2026): walk48's clause on walk51's objects. A weak proposal
(the 0.20 branch, the survey-week rate, state breadth) that the household survey has co-signed - the three-month average
unemployment rate, as last published, at least 0.2 point above its twelve-month low, the rule's own co-signer line - may
be confirmed by the strong proposers' confirmers (vacancy, hours pair, spread) as well as by the weak proposers' (the
housing x rate pair on starts or permits, the spread, the starts x vacancy pair); an unsigned weak proposal takes the
weak confirmers only. walk48 walked the clause on walk47's objects: 2024 opened 1 February 2024 (-89) and 2001 22 March
2001 (-9), none false, but the walk moved the vacancy line to 0.25 and the hub's look-back to 12 at its last cut, and the
clause stood one tenth of the survey-week rate from a false alarm in June 2025. This walk asks the same question with
the search week and the either pair in place. Run:  python3 walk52.py 1962 2026 w52"""
import sys,pickle,os
_MARK="# ---- the walk "+"itself"
exec(open('walk51.py').read().split(_MARK)[0].replace("walk51_%s.out","walk52_%s.out"))
import pandas as pd, numpy as np
_build51=build_v
def build_v(p):
    global cosign
    G=vgap2_asof(p['vk'],p['vb']); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=p['vl'],pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,p['u45'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt_x(RT,p['u45'])
    F25=[x for x in leg_gap_mx2(gm,p['low'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt_x(RT,p['low'])
    Hc=mkpair_either_asof(p['hline']); Hh=HOURS_ASOF
    SP=dict(name='spread',gap=GSP,line=p['spr'],pubs=SP_PUBS)
    SV=mkpair_sv_asof(G,pubs,p['vl'])
    def hubv(sl,back):
        calls=[]; armed=True
        for m,v in g_asof.items():
            if m<pd.Timestamp('1948-06-01'): continue
            if armed and v>=sl-EPS:
                w=G[(G.index>=m-pd.DateOffset(months=back))&(G.index<=m)]; hit=w[w>=p['vl']-EPS]
                sp=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
                ok=len(hit)>=2
                if ok:
                    known=pubs[(pubs.index<=m)&(pubs<=sp)]
                    ok=len(known)>0 and float(G.get(known.index.max(),np.nan))>=p['vl']-EPS
                if ok:
                    kk=hit.index[1]
                    calls.append((max(sp,pubs[kk]),m-pd.DateOffset(months=3),'hub')); armed=False
            elif not armed and v<sl-EPS: armed=True
        return calls
    _c0=cosign; cosign=cosign_asof
    try:
        C1=[Vc,Hh,SP]; C2=[Hc,SP,SV]
        def weak(props):
            co=[x for x in props if cosign_asof(x[0])]; un=[x for x in props if not cosign_asof(x[0])]
            return [(a,b) for a,b,c in confirm_wx(co,C1+C2,'month')]+[(a,b) for a,b,c in confirm_wx(un,C2,'month')]
        legs={'U':[(a,b) for a,b,c in confirm_wx(leg_gapL_cx(spl,p['u45'],p['look'])+F45,C1,'month')],
              'L':weak(leg_gapL_x(spl,p['low'],52,rearm='window')+F25),
              'X':[(a,b) for a,b,c in hubv(p['sahm'],p['hback'])],'I':[(a,b) for a,b,c in confirm_wx(leg_ic_cx(ICfp,p['ic']),C1,'month')]}
        if p.get('wline'): legs['W']=weak(leg_sv_x(p['wline'],rearm='zero'))
        if p.get('wline2'): legs['V']=weak(leg_sv_x(p['wline2'],rearm='window'))
        if p.get('bshare'): legs['B']=weak(leg_br_x(p['bshare']))
        if p.get('kc'): legs['K']=[(a,b) for a,b in leg_K_x(ICfp,p['kc'][0],p['kc'][1])]
    finally: cosign=_c0
    TL=dict(TLH); TL['R']=RC[p['rst']]; TL['T']=TC[p['tst']]; TL['Q']=QC[p['qst']]
    if p.get('cD') is not None: TL['C']=CMENU[(p['cD'],p['cn'],p['cs'])]
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TL)
    return score13(turns),turns
# ---- the walk itself: walk39's loop, verbatim ----
exec(open('walk39.py').read().split(_MARK)[1].split("\n",1)[1])
