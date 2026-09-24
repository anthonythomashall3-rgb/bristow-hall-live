"""WALK 54 - WALK 53 WITH THE MAJORITY COUNTED ON THE PRINTS PUBLISHED BY THE DAY (10 September 2026, evening). The hub X
fires when the Sahm gap, as it stood on the release day, is at 0.3667 and vacancies are still falling: the vacancy gap at
its line in two of the prior nine months AND (walk40) in the latest JOLTS print known that day. walk53 read 'still
falling' as the latest print at the line OR the vacancy at the line in a majority of the window (five or more) - but it
counted the months of the window m-9..m whichever were published, and the month m itself (and at times m-1) is not out on
the Sahm release day. Here the majority is counted over the months of the window whose JOLTS print was published by that
day, as the 'latest' test already is (s2/q35.py: the two counts differ in many months; no call differs - thirteen of
thirteen frozen, none false, 2024 opens 3 May 2024 by the five published hits of July-November 2023). The hold's purpose is
kept: December 2025 (two of the prior nine at the line, the latest at -0.005) is still blocked. Everything else is walk51's.
Run:  python3 walk54.py 1962 2026 w54"""
import sys,pickle,os
_MARK="# ---- the walk "+"itself"
exec(open('walk51.py').read().split(_MARK)[0].replace("walk51_%s.out","walk54_%s.out"))
import pandas as pd, numpy as np
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
                    latest=len(known)>0 and float(G.get(known.index.max(),np.nan))>=p['vl']-EPS
                    hitk=hit[[k for k in hit.index if k in known.index]]      # the hits published by the release day
                    ok=latest or len(hitk)>=5   # the latest print at the line, or a majority of the window as published (walk54)
                if ok:
                    kk=hit.index[1]
                    calls.append((max(sp,pubs[kk]),m-pd.DateOffset(months=3),'hub')); armed=False
            elif not armed and v<sl-EPS: armed=True
        return calls
    _c0=cosign; cosign=cosign_asof
    try:
        C1=[Vc,Hh,SP]; C2=[Hc,SP,SV]
        legs={'U':[(a,b) for a,b,c in confirm_wx(leg_gapL_cx(spl,p['u45'],p['look'])+F45,C1,'month')],
              'L':[(a,b) for a,b,c in confirm_wx(leg_gapL_x(spl,p['low'],52,rearm='window')+F25,C2,'month')],
              'X':[(a,b) for a,b,c in hubv(p['sahm'],p['hback'])],'I':[(a,b) for a,b,c in confirm_wx(leg_ic_cx(ICfp,p['ic']),C1,'month')]}
        if p.get('wline'): legs['W']=[(a,b) for a,b,c in confirm_wx(leg_sv_x(p['wline'],rearm='zero'),C2,'month')]
        if p.get('wline2'): legs['V']=[(a,b) for a,b,c in confirm_wx(leg_sv_x(p['wline2'],rearm='window'),C2,'month')]
        if p.get('bshare'): legs['B']=[(a,b) for a,b,c in confirm_wx(leg_br_x(p['bshare']),C2,'month')]
        if p.get('kc'): legs['K']=[(a,b) for a,b in leg_K_x(ICfp,p['kc'][0],p['kc'][1])]
    finally: cosign=_c0
    TL=dict(TLH); TL['R']=RC[p['rst']]; TL['T']=TC[p['tst']]; TL['Q']=QC[p['qst']]
    if p.get('cD') is not None: TL['C']=CMENU[(p['cD'],p['cn'],p['cs'])]
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TL)
    return score13(turns),turns
# ---- the walk itself: walk39's loop, verbatim ----
exec(open('walk39.py').read().split(_MARK)[1].split("\n",1)[1])
