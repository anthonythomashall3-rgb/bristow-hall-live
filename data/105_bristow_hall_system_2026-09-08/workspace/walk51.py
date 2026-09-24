"""WALK 51 - WALK 50 WITH BUILDING PERMITS ADMITTED BESIDE STARTS IN THE HOUSING x RATE PAIR (10 September 2026). walk49
put permits IN PLACE OF starts and lost 1969 (+89: permits had fallen 21 log points by September 1969 where starts had
fallen 29); here the pair is confirmed by EITHER series at the starts line (29 log points below the twelve-month high
of the three-month mean, with the unemployment rate 0.4 above its eighteen-month low, both at 1.0): starts keep 1969,
permits reach the line in May 1990 (36 log points on the data of the day, collection 107) where starts waited for the
August print. The starts x vacancy pair keeps starts (permits there confirm a breadth proposal in January 2023 that no
recession followed, s2/q20.py). No co-signer clause (walk48's, which produced walk49's June 2025 false alarm at a
survey-week line of 0.3, is not here). Everything else is walk50's: the search week in the sudden stop, the trough
closers on the vintage, the grid, the walk, the objective, the tie-break, the depth step.
Run:  python3 walk51.py 1962 2026 w51"""
import sys,pickle,os
_MARK="# ---- the walk "+"itself"
exec(open('walk50.py').read().split(_MARK)[0].replace("walk50_%s.out","walk51_%s.out"))
exec(open('s2/asof_permits.py').read())
import pandas as pd, numpy as np
def mkpair_either_asof(hline):
    """the housing x rate pair at 1.0 when starts or permits stand at the starts line with the rate at its line; the
    reading is the larger of the two pairs' readings; the release day is the earlier of the two confirmations"""
    A=mkpair_asof(hline); Pm=mkpair_perm_asof(hline)
    idx=A['gap'].index.union(Pm['gap'].index); gap={}; pubs={}
    for m in idx:
        c=[(float(A['gap'].get(m,np.nan)),A['pubs'].get(m,pd.NaT)),(float(Pm['gap'].get(m,np.nan)),Pm['pubs'].get(m,pd.NaT))]
        c=[(g,p) for g,p in c if not np.isnan(g)]
        atl=[(g,p) for g,p in c if g>=hline-EPS]
        if atl: gap[m]=1.0; pubs[m]=min(p for g,p in atl)
        else:
            g,p=max(c,key=lambda x:x[0]); gap[m]=g; pubs[m]=p
    return dict(name='pairEITHER',gap=pd.Series(gap).sort_index(),line=hline,pubs=pd.Series(pubs).sort_index())
# ---- the rule: walk47's build_v (no co-signer clause) with the either pair; K from s2/search_week.py ----
def build_v(p):
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
    global cosign
    _c0=cosign; cosign=cosign_asof   # the strong proposers' co-signer, as it stood on the release day (walk45)
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
