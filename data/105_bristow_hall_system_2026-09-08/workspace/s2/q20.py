# q20.py - BUILDING PERMITS IN THE HOUSING HALF, on the release-day vintage (ALFRED from 1999; Economic Indicators as
# printed for 1969 and 1990; the current file elsewhere), frozen 1948-2026 at w46's walk-end lines.
#   base       walk46 (starts)                perm_rate  permits in the housing x rate pair only
#   perm_both  permits in both pairs           either     starts pairs and permits pairs all admitted
# Run in the workspace: PYTHONPATH=. python3 s2/q20.py
import sys,pickle,io,contextlib,os
sys.path.insert(0,os.getcwd()); sys.argv=['walk46.py','1962','2026','w46']
import pandas as pd, numpy as np
_MARK="# ---- the walk "+"itself"
exec(open('walk46.py').read().split(_MARK)[0])
exec(open('s2/asof_permits.py').read())
pw=pickle.load(open('cache/w46_carry.pkl','rb'))
print('permits half by source:',pd.Series(PERM_SRC).value_counts().to_dict())
print('permits half 1990 (as it stood):',{m.strftime('%Y-%m'):(round(float(PERM_ASOF[m]),3),PERM_SRC[m],PERM_PUB[m].date().isoformat()) for m in pd.date_range('1990-03-01','1990-09-01',freq='MS')})
print('rate half 1990 (as it stood):',{m.strftime('%Y-%m'):(round(float(rate_asof[m]),2),rate_pub[m].date().isoformat() if hasattr(rate_pub[m],'date') else str(rate_pub[m])) for m in pd.date_range('1990-03-01','1990-09-01',freq='MS')})
print('permits half at its line 1961-2026, first-print/alfred months only:',[m.strftime('%Y-%m') for m,v in PERM_ASOF.items() if v>=1-EPS and PERM_SRC[m]!='current-file'][:40])
def build_variant(p,mode='base'):
    global cosign
    G=vgap2_asof(p['vk'],p['vb']); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=p['vl'],pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,p['u45'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt_x(RT,p['u45'])
    F25=[x for x in leg_gap_mx2(gm,p['low'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt_x(RT,p['low'])
    Hs=mkpair_asof(p['hline']); SVs=mkpair_sv_asof(G,pubs,p['vl']); Hp=mkpair_perm_asof(p['hline']); SVp=mkpair_sv_perm_asof(G,pubs,p['vl'])
    Hh=HOURS_ASOF; SP=dict(name='spread',gap=GSP,line=p['spr'],pubs=SP_PUBS)
    C2={'base':[Hs,SP,SVs],'perm_rate':[Hp,SP,SVs],'perm_both':[Hp,SP,SVp],'either':[Hs,Hp,SP,SVs,SVp]}[mode]
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
                    kk=hit.index[1]; calls.append((max(sp,pubs[kk]),m-pd.DateOffset(months=3),'hub')); armed=False
            elif not armed and v<sl-EPS: armed=True
        return calls
    _c0=cosign; cosign=cosign_asof
    try:
        C1=[Vc,Hh,SP]
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
for mode in ('base','perm_rate','perm_both','either'):
    r,t=build_variant(pw,mode)
    lags=[r['lags_p'][i] for i in sorted(r['lags_p'])]; op={i:(r['opens'][i]['published'].date().isoformat(),r['opens'][i]['leg']) for i in r['opens']}
    print(f"{mode:10} peaks {len(r['lags_p'])}/13 FALSE {len(r['other'])} {r['other']} | lags {lags} | 1969 {op.get(4)} 1981 {op.get(7)} 1990 {op.get(8)} 2008 {op.get(10)} | troughs {len(r['lags_t'])}/13")
