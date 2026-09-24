# q16.py - THE SPEED CANDIDATES THAT CARRY NO NEW NUMBER, on the release-day vintage, frozen 1948-2026 at w46's walk-end
# lines (the acid test: any call outside a recession is a false alarm). Each candidate reuses a line the rule already has.
#   base      v3.26 as walked (the check)
#   nohold    the hub without its 'still falling' hold (the latest vacancy print need not be at the line)
#   c2hours   the hours pair admitted as a confirmer of the weak proposers (L, W, V, B)
#   c2vac     the vacancy admitted as a confirmer of the weak proposers (the refused route, re-run on the vintage)
#   cosign    a weak proposal that is co-signed by the household survey (the co-signer's own line, 0.2) may take the
#             strong proposers' confirmers (vacancy, hours, spread)
#   mkt15     the S&P 500 15 per cent under its 26-week high (the closer's own numbers) as a confirmer of the weak proposers
#   crash20   the S&P 500 20 per cent under its 20-day high (the sudden stop's number) as a confirmer of the weak proposers
#   permits   building permits in place of starts in the housing half (current file - a screen only; permits share the
#             starts release)
# Run in the workspace: PYTHONPATH=. python3 s2/q16.py
import sys,pickle,io,contextlib,os
sys.path.insert(0,os.getcwd()); sys.argv=['walk46.py','1962','2026','w46']
import pandas as pd, numpy as np
_MARK="# ---- the walk "+"itself"
exec(open('walk46.py').read().split(_MARK)[0])
pw=pickle.load(open('cache/w46_carry.pkl','rb'))
# market objects, read at each claims release day from the last close before it (as the sudden stop reads the market)
_px=_SPX.dropna()
_m26=(1-_px/_px.rolling(130,min_periods=60).max())*100; _m20=(1-_px/_px.rolling(20,min_periods=10).max())*100
_days=sorted(set(rel_ic(w) for w in ICfp.dropna().index if w>=pd.Timestamp('1948-01-01')))
def _at_prior_close(ser):
    out={}
    for d in _days:
        s=ser[ser.index<d]
        if len(s): out[d]=float(s.iloc[-1])
    return pd.Series(out).sort_index()
MK15=dict(name='mkt15',gap=_at_prior_close(_m26),line=15.0,pubs=pd.Series({d:d for d in _days}))
CR20=dict(name='crash20',gap=_at_prior_close(_m20),line=20.0,pubs=pd.Series({d:d for d in _days}))
# permits (current file) in the housing half
_pm=pd.read_csv('cache/surveys/PERMIT.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
_lp=np.log(_pm)*100; HH_PERM=((_lp.rolling(12).max()-_lp.rolling(3).mean())/BASE15['starts']).dropna()
HH_PERM_PUB=pd.Series({m:(relH[m] if m in relH.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=17)) for m in HH_PERM.index})
def mkpair_generic(hh,hpub,rate,rpub,hline):
    ev=[(pd.Timestamp(hpub[m]),'D',m) for m in hh.index if m in hpub.index]+[(pd.Timestamp(rpub[m]),'U',m) for m in rate.index if m>=pd.Timestamp('1960-01-01')]
    ev.sort(key=lambda x:(x[0],x[1])); lastD=None; lastU=None; fires={}; mx={}
    for d,kind,m in ev:
        if kind=='D': lastD=m if (lastD is None or m>lastD) else lastD
        else: lastU=m if (lastU is None or m>lastU) else lastU
        if lastD is None or lastU is None: continue
        v=min(hh.get(lastD,np.nan),rate.get(lastU,np.nan))
        if np.isnan(v): continue
        key=max(lastD,lastU); mx[key]=max(mx.get(key,-9),v)
        if v>=hline-EPS and key not in fires: fires[key]=d
    G_=pd.Series({m:(1.0 if m in fires else mx[m]) for m in mx}).sort_index(); PB=pd.Series({m:fires.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=2)) for m in mx}).sort_index()
    return dict(name='pairPERM',gap=G_,line=hline,pubs=PB)
def build_variant(p,hold=True,c2_extra=(),cosigned_c1=False,permits=False):
    global cosign
    G=vgap2_asof(p['vk'],p['vb']); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=p['vl'],pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,p['u45'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt_x(RT,p['u45'])
    F25=[x for x in leg_gap_mx2(gm,p['low'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt_x(RT,p['low'])
    Hc=mkpair_generic(HH_PERM,HH_PERM_PUB,rate_asof,rate_pub,p['hline']) if permits else mkpair_asof(p['hline'])
    Hh=HOURS_ASOF; SP=dict(name='spread',gap=GSP,line=p['spr'],pubs=SP_PUBS); SV=mkpair_sv_asof(G,pubs,p['vl'])
    def hubv(sl,back):
        calls=[]; armed=True
        for m,v in g_asof.items():
            if m<pd.Timestamp('1948-06-01'): continue
            if armed and v>=sl-EPS:
                w=G[(G.index>=m-pd.DateOffset(months=back))&(G.index<=m)]; hit=w[w>=p['vl']-EPS]
                sp=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
                ok=len(hit)>=2
                if ok and hold:
                    known=pubs[(pubs.index<=m)&(pubs<=sp)]
                    ok=len(known)>0 and float(G.get(known.index.max(),np.nan))>=p['vl']-EPS
                if ok:
                    kk=hit.index[1]; calls.append((max(sp,pubs[kk]),m-pd.DateOffset(months=3),'hub')); armed=False
            elif not armed and v<sl-EPS: armed=True
        return calls
    _c0=cosign; cosign=cosign_asof
    try:
        C1=[Vc,Hh,SP]; C2=[Hc,SP,SV]+[{'hours':Hh,'vac':Vc,'mkt15':MK15,'crash20':CR20}[k] for k in c2_extra]
        def weak(props):
            if not cosigned_c1: return [(a,b) for a,b,c in confirm_wx(props,C2,'month')]
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
VARIANTS=[('base',{}),('nohold',dict(hold=False)),('c2hours',dict(c2_extra=('hours',))),('c2vac',dict(c2_extra=('vac',))),
          ('cosign',dict(cosigned_c1=True)),('mkt15',dict(c2_extra=('mkt15',))),('crash20',dict(c2_extra=('crash20',))),('permits',dict(permits=True)),
          ('cosign+nohold',dict(cosigned_c1=True,hold=False))]
for nm,kw in VARIANTS:
    r,t=build_variant(pw,**kw)
    lags=[r['lags_p'][i] for i in sorted(r['lags_p'])]
    opens_={i:(r['opens'][i]['published'].date().isoformat(),r['opens'][i]['leg']) for i in r['opens']}
    print(f"{nm:14} peaks {len(r['lags_p'])}/13 FALSE {len(r['other'])} {r['other']} | lags {lags} | 1990 {opens_.get(8)} 2020 {opens_.get(11)} 2024 {opens_.get(12)} | troughs {len(r['lags_t'])}/13 premature {[(i,r['lags_t'][i]) for i in r['lags_t'] if r['lags_t'][i]<-31]}")
