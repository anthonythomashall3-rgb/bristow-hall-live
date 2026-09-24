# q34.py - THE HUB'S HOLD, THE FULL RULE FROZEN 1948-2026 on walk51's objects at its walk-end lines, with the hold read
# two ways that carry no new line: (C) the latest JOLTS print at the line OR the vacancy at the line in a majority of the
# prior nine months (five or more; the hold's own window), and (C3) OR in three of the prior nine (the hold's own count,
# one more). As walked (A): the latest print at the line, and two of the prior nine. Reported: every call and any call
# outside a recession, and the 2024 open. Run: PYTHONPATH=. python3 s2/q34.py
import sys,os,io,contextlib,pickle
sys.path.insert(0,os.getcwd()); sys.argv=['walk51.py','1962','2026','w51']
import pandas as pd, numpy as np
_MARK="# ---- the walk "+"itself"
with contextlib.redirect_stdout(io.StringIO()): exec(open('walk51.py').read().split(_MARK)[0])
p=pickle.load(open('cache/w51_carry.pkl','rb'))
HOLD='A'
def build_hold(p):
    global cosign
    G=vgap2_asof(p['vk'],p['vb']); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=p['vl'],pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,p['u45'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt_x(RT,p['u45'])
    F25=[x for x in leg_gap_mx2(gm,p['low'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt_x(RT,p['low'])
    Hc=mkpair_either_asof(p['hline']); Hh=HOURS_ASOF
    SP=dict(name='spread',gap=GSP,line=p['spr'],pubs=SP_PUBS); SV=mkpair_sv_asof(G,pubs,p['vl'])
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
                    if HOLD=='A': ok=latest
                    elif HOLD=='C': ok=latest or len(hit)>=5
                    elif HOLD=='C3': ok=latest or len(hit)>=3
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
for HOLD in ('A','C','C3'):
    r,t=build_hold(p); op={i:(r['opens'][i]['published'].date().isoformat(),r['opens'][i]['leg']) for i in r['opens']}
    print(f"hold {HOLD}: peaks {len(r['lags_p'])}/13 other {r['other']} lags {[r['lags_p'][i] for i in sorted(r['lags_p'])]} | 2024 {op.get(12)} | troughs {len(r['lags_t'])}/13")
    print('   opens',op)
