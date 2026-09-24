"""WALK 49 - WALK 48 WITH BUILDING PERMITS IN PLACE OF STARTS IN THE HOUSING x RATE PAIR (10 September 2026). A permit is
the decision to build; a start is its execution a month or two later, and the Census publishes both on the same
morning. The pair keeps its line (29 log points, the starts line, over the three-month mean's fall from its twelve-month
high; the unemployment rate 0.4 above its eighteen-month low; both at 1.0) and its release days; only the series
changes, and only in this pair - the starts x vacancy pair keeps starts, because permits in both pairs confirm a
breadth proposal in November 2022 that no recession followed (s2/q20.py). Permits are read as they stood on the day:
ALFRED vintages from August 1999 (collection 27), the Economic Indicators tables as printed for 1969 and 1990 (collection
107), the current file elsewhere, declared as a bound. Frozen 1948-2026 at walk46's lines the change moves one call,
1990, from 19 September 1990 (+50) to 26 July 1990 (-5): the pair had stood at both its lines since the April print of
16 May 1990 (36 log points below the January high on the data of the day, 1.25 times the line). Everything else is
walk48's. Run:  python3 walk49.py 1962 2026 w49"""
import sys,pickle,os
_MARK="# ---- the walk "+"itself"
exec(open('walk48.py').read().split(_MARK)[0].replace("walk48_%s.out","walk49_%s.out"))
exec(open('s2/asof_permits.py').read())
import pandas as pd, numpy as np
# ---- the rule: walk48's build_v with the housing x rate pair on permits ----
def build_v(p):
    global cosign
    G=vgap2_asof(p['vk'],p['vb']); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=p['vl'],pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,p['u45'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt_x(RT,p['u45'])
    F25=[x for x in leg_gap_mx2(gm,p['low'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt_x(RT,p['low'])
    Hc=mkpair_perm_asof(p['hline']); Hh=HOURS_ASOF   # permits in the housing x rate pair
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
