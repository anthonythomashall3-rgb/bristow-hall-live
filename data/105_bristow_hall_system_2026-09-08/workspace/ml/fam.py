# MOVING-LINE FAMILIES for the Bristow Hall Rule, frozen sweeps (9 September 2026). Everything not named is v3.23's.
# P: the insured rate's branches U and L as a PERCENT rise over the 52-week low (the printed rate, tenths)
# C: U and L on CONTINUED CLAIMS (4-week mean, first prints where they exist), percent rise over the 52-week low
# N: the claims branch I with a NOISE-SCALED line: k x the trailing ten-year MAD of the object, as known at the time
# Q: the claims branch I at an EXPANDING QUANTILE of its own history (label-free)
import numpy as np, pandas as pd
STRONG_U=0.65/0.45; STRONG_I=55/40
def _pct_gap(s,look): return ((s/s.rolling(look,min_periods=look).min().shift(1))-1)*100
def leg_pct_c(s,pct,look=52,pubfn=None,strong=STRONG_U):
    """percent-rise proposer with the co-signer (rearm at zero)"""
    gap=_pct_gap(s,look).dropna(); c=[]; armed=True
    for t,v in gap.items():
        if armed and v>=pct:
            day=pubfn(t)
            if v>=pct*strong or cosign(day): c.append((day,pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=0: armed=True
    return c
def leg_pct(s,pct,look=52,pubfn=None,rearm='window'):
    gap=_pct_gap(s,look).dropna(); c=[]; armed=True; last=None
    for t,v in gap.items():
        if armed and v>=pct: c.append((pubfn(t),pd.Timestamp(t.year,t.month,1))); armed=False; last=t
        elif not armed:
            if rearm=='zero' and v<=0: armed=True
            elif rearm=='window' and v<pct and t>=last+pd.DateOffset(months=4): armed=True
    return c
gmp=((fh/fh.rolling(12,min_periods=12).min().shift(1))-1)*100; gmp=gmp.dropna()          # the monthly Fieldhouse rate, percent
def leg_rt_pct(s,pct,look=52,stop='1971-01-01'):
    gap=_pct_gap(s,look).dropna(); c=[]; armed=True
    for t,v in gap.items():
        if armed and v>=pct: c.append((rel_iu(t),pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=0: armed=True
    return [x for x in c if x[1]<pd.Timestamp(stop)]
CC4=_CCfp.rolling(4).mean().dropna()
# noise-scaled and quantile lines for the claims object
_m4=ICfp.dropna().rolling(4).mean(); ICR=((_m4/_m4.rolling(52,min_periods=52).min().shift(1)-1)*100).dropna()
def _mad(x): m=np.nanmedian(x); return np.nanmedian(np.abs(x-m))
MAD10=ICR.rolling(520,min_periods=260).apply(_mad,raw=True).shift(1)
def leg_icN(k,strong=STRONG_I):
    c=[]; armed=True
    for t,v in ICR.items():
        line=k*MAD10.get(t,np.nan)
        if np.isnan(line): continue
        if armed and v>=line:
            day=rel_ic(t)
            if v>=line*strong or cosign(day): c.append((day,pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=0: armed=True
    return c
def _expq(q,minw=260):
    out=pd.Series(np.nan,index=ICR.index); vals=[]
    arr=ICR.values
    for i,t in enumerate(ICR.index):
        if i>=minw: out.iloc[i]=np.percentile(arr[:i],q)
    return out
_EQ={}
def leg_icQ(q,strong=STRONG_I):
    if q not in _EQ: _EQ[q]=_expq(q)
    L=_EQ[q]; c=[]; armed=True
    for t,v in ICR.items():
        line=L.get(t,np.nan)
        if np.isnan(line): continue
        if armed and v>=line:
            day=rel_ic(t)
            if v>=line*strong or cosign(day): c.append((day,pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=0: armed=True
    return c
def build_alt(p,fam,prm):
    G=vgap2(p['vk'],p['vb']); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=p['vl'],pubs=pubs)
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
                    kk=hit.index[1]; calls.append((max(sp,pubs[kk]),m-pd.DateOffset(months=3),'hub')); armed=False
            elif not armed and v<sl: armed=True
        return calls
    C1=[Vc,Hh,SP]; C2=[Hc,SP]
    if fam in ('P','C'):
        pU,pL=prm['pU'],prm['pL']
        F45=[x for x in leg_gap_mx2(gmp,pU,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt_pct(RT,pU)
        F25=[x for x in leg_gap_mx2(gmp,pL,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt_pct(RT,pL)
        if fam=='P': Uc=leg_pct_c(spl,pU,52,rel_iu); Lc=leg_pct(spl,pL,52,rel_iu,'window')
        else:
            Uc=[x for x in leg_pct_c(CC4,pU,52,rel_iu) if x[1]>=pd.Timestamp('1971-01-01')]; Lc=[x for x in leg_pct(CC4,pL,52,rel_iu,'window') if x[1]>=pd.Timestamp('1971-01-01')]
        Ucalls=Uc+F45; Lcalls=Lc+F25; Icalls=leg_ic_c(ICfp,p['ic'])
    else:
        F45=[x for x in leg_gap_mx2(gm,p['u45'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['u45'])
        F25=[x for x in leg_gap_mx2(gm,p['low'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['low'])
        Ucalls=leg_gapL_c(spl,p['u45'],p['look'])+F45; Lcalls=leg_gapL(spl,p['low'],52,rearm='window')+F25
        Icalls=leg_icN(prm['k']) if fam=='N' else leg_icQ(prm['q'])
    legs={'U':[(a,b) for a,b,c in confirm_w(sorted(Ucalls),C1,'month')],'L':[(a,b) for a,b,c in confirm_w(sorted(Lcalls),C2,'month')],
          'X':[(a,b) for a,b,c in hubv(p['sahm'],p['hback'])],'I':[(a,b) for a,b,c in confirm_w(Icalls,C1,'month')]}
    if p.get('wline'): legs['W']=[(a,b) for a,b,c in confirm_w(leg_sv(p['wline'],rearm='zero'),C2,'month')]
    if p.get('wline2'): legs['V']=[(a,b) for a,b,c in confirm_w(leg_sv(p['wline2'],rearm='window'),C2,'month')]
    if p.get('bshare'): legs['B']=[(a,b) for a,b,c in confirm_w(leg_br(p['bshare']),C2,'month')]
    TL=dict(TLH); TL['R']=RC[p['rst']]; TL['T']=TC[p['tst']]; TL['Q']=QC[p['qst']]
    if p.get('cD') is not None: TL['C']=CMENU[(p['cD'],p['cn'],p['cs'])]
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TL)
    return score13(turns),turns
BASE_R,BASE_T=build_v(p0)
BASE_PK={PK[i].strftime('%Y-%m'):(BASE_R['opens'][i]['published'],BASE_R['opens'][i]['leg']) for i in BASE_R['called']}
def report(tag,r,t):
    pk=[(x['published'],x['leg']) for x in t if x['kind']=='peak' and x['published'].year>=1948]
    cells=[]
    for i in range(13):
        k=PK[i].strftime('%Y-%m')
        if i in r['lags_p']:
            d=r['opens'][i]['published']; leg=r['opens'][i]['leg']; base=BASE_PK.get(k)
            delta=(d-base[0]).days if base else None
            cells.append(f"{k}:{d:%Y-%m-%d}{leg}({'=' if delta==0 else ('%+d' % delta)})")
        else: cells.append(f"{k}:MISS")
    print(f"{tag:28s} called {len(r['called'])}/13 other {len(r['other'])} {r['other'][:4]} | troughs {len(r['closed'])}/13 | "+' '.join(cells))
print('base v3.23 frozen:'); report('v3.23',BASE_R,BASE_T)
