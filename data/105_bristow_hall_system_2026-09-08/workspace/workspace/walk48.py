"""WALK 48 - WALK 47 WITH THE HOUSEHOLD CO-SIGNER ADMITTING A WEAK PROPOSAL TO THE STRONG PROPOSERS' CONFIRMERS
(10 September 2026). The rule already has one co-signer: a proposal by the insured rate's 0.45 branch or by initial claims
that stands only a little above its line fires only if the household survey co-signs it - the three-month average of the
unemployment rate, as last published, at least 0.2 point above its low of the prior twelve months. Here the same
co-signer, at the same line, does the same work for the weak proposers (the insured rate's 0.20 branch, the survey-week
rate, state breadth): a weak proposal that the household survey has co-signed may be confirmed by any demand-side
object on the menu - the vacancy rate or the hours pair as well as the housing pairs and the spread - because a weak
supply signal that the household survey has already ratified is, in the rule's own terms, a strong one. An unsigned weak
proposal takes only the housing pairs and the spread, as before. No new number. On the release-day vintage, frozen
1948-2026 at walk46's lines, the clause fires once: 1 February 2024 (the 0.20 branch, co-signed on the December 2023
report, confirmed by the vacancy), moving 2024 from +38 to -89 days; every other call and every close is unchanged
(s2/q16.py). Everything else is walk47's. Run:  python3 walk48.py 1962 2026 w48"""
import sys,pickle,os
_MARK="# ---- the walk "+"itself"
exec(open('walk47.py').read().split(_MARK)[0].replace("walk47_%s.out","walk48_%s.out"))
import pandas as pd, numpy as np
# ---- the rule: walk45's build_v with the co-signed weak proposals confirmed by C1 as well as C2 ----
def build_v(p):
    global cosign
    G=vgap2_asof(p['vk'],p['vb']); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=p['vl'],pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,p['u45'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt_x(RT,p['u45'])
    F25=[x for x in leg_gap_mx2(gm,p['low'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt_x(RT,p['low'])
    Hc=mkpair_asof(p['hline']); Hh=HOURS_ASOF
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
