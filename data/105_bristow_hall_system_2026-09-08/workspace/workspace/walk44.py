"""WALK 44 - WALK 43 WITH (1) EXACT ARITHMETIC AT THE LINE, (2) THE STARTS x VACANCY PAIR AS A CONFIRMER OF THE WEAK
PROPOSERS, (3) THE PAPER SPREAD READ ON THE WIDER OF THE FED'S TWO TOP-TIER PAPER MARKETS FROM SEPTEMBER 1997, AND
(4) THE SUDDEN-STOP PROPOSER (a single week of claims above its base with the equity market fallen the same week).
10 September 2026. Everything else is walk43's: the objects on first prints, the release days, the co-signer, the moving
base, the grid, the windows, the walk, the objective, the tie-break, the depth step.

(1) EXACT ARITHMETIC (Rule Zero). The insured-rate legs compared a floating-point difference with the line: 2.3 - 2.1 is
0.19999999999999973 in binary and was read as BELOW a line of 0.2, while 2.4 - 2.2 is 0.20000000000000018 and was read
as above it. A reading equal to its line is at the line and fires (the published series says so: the rule calls at 1.00).
Every one-decimal object is now read in exact tenths and every comparison with a line carries a tolerance of 1e-9. At the
walk-end lines of walk43 the frozen record 1948-2026 is unchanged to the day and still makes no other call (s2/q7.py).

(2) THE STARTS x VACANCY PAIR. The weak proposers (the insured rate's low branch, the survey-week rate, state breadth)
are confirmed by the housing pair or the paper spread. The housing pair is starts down AND the unemployment rate up -
half demand, half the household survey, which reports once a month on the first Friday, and in 1990 and 2007 the pair's
household half was what the rule waited for. A second pair is added to the same confirmer set: starts down (the same
half, the same line) AND the vacancy rate off its four-month high (the rule's own vacancy object, the same line). Two
demand objects agreeing is the conjunction's own principle; the vacancy alone was refused for the weak proposers
because it is in place in every slowdown (1989, 2019, 2022, 2025), and starts down alone was refused because it is in
place in every housing downturn (1966, 1978, 1979, 1984, 2006); the two together are in place, 1960-2026, only inside
recessions (1974-75, 1980, 1981-82, 1990-91, 2008-09, 2020). No new number: the starts line and the vacancy line are the
walked ones. Declared after the July 1990 case was examined (Rule Zero).

(3) THE PAPER SPREAD ON THE WIDER OF TWO MARKETS. Before September 1997 the H.15 commercial paper rate covered dealer-
placed paper of prime issuers, financial and nonfinancial alike. From September 1997 the Federal Reserve reports the two
separately (AA nonfinancial, AA financial); walk37 spliced the nonfinancial rate on. The object now reads the wider
of the two spreads over the bill, so that stress in either paper market is seen as the single series would have seen it.
Same construction (13-week mean above its 39-week minimum), same line. Outside recessions the wider object's largest
reading since 1997 is 0.48 (December 1998) against the nonfinancial 0.46; the only call it changes is December 2007,
where financial paper crossed the line in the H.15 week of 21 December (public Monday 24 December) and nonfinancial
paper reached 0.85. Declared after the December 2007 case was examined (Rule Zero).

(4) THE SUDDEN STOP. A single week of initial claims (first print) K per cent above the claims object's base (the higher
of the four-week mean's 52-week low and 85 per cent of its five-year median), confirmed the same week by the S&P 500
standing c per cent or more below its high of the prior twenty trading days on the release day. Both sides of the
conjunction breaking in the same week is a different event from a slow turn, and the four-week mean built to smooth
ordinary weeks is the wrong instrument for a week that is not ordinary. K and c go into the grid, safest first
(35/20, 35/15, 30/15, 30/10, off), and the route is kept where it costs nothing on the past (as for the survey-week
lines and breadth). 1948-2019 it never fires; SPEED-FRONTIER s5, 9 September 2026.

Run:  python3 walk44.py 1962 2026 w44   (fresh summary cache; ~30-40 minutes)"""
import sys,pickle,os
_MARK="# ---- the walk "+"itself"
exec(open('walk43.py').read().split(_MARK)[0].replace("walk43_%s.out","walk44_%s.out"))
import pandas as pd, numpy as np
exec(open('s2/exact.py').read().split("def build_v3(")[0])
# the paper spread on the wider of the two markets from September 1997
_f=pd.read_csv(os.path.join(C25,'fred_daily','DCPF1M.csv')).iloc[:,:2]; _f.columns=['d','v']; _f['d']=pd.to_datetime(_f['d'],errors='coerce')
_f=pd.to_numeric(_f.set_index('d')['v'],errors='coerce').dropna(); _fw=_f.resample('W-FRI').mean().dropna()
aam=aa.copy(); _common=aa.index.intersection(_fw.index); aam.loc[_common]=np.maximum(aa.loc[_common].values,_fw.loc[_common].values)
_idx3=aam.index.union(bb.index); CPBm=(aam.reindex(_idx3).ffill()-bb.reindex(_idx3).ffill()).dropna(); CPBm=CPBm[CPBm.index>=max(aam.index.min(),bb.index.min())]
_Smm=CPBm.rolling(13).mean().dropna(); GSPm=(_Smm-_Smm.rolling(39).min()).dropna()
GSP=GSPm; SP_PUBS=pd.Series({t:rel_h15(t) for t in GSP.index})
assert GSP.index.max()>=pd.Timestamp('2026-06-01'), 'spread object short'
# ---- the rule ----
def build_v(p):
    G=vgap2(p['vk'],p['vb']); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=p['vl'],pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,p['u45'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt_x(RT,p['u45'])
    F25=[x for x in leg_gap_mx2(gm,p['low'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt_x(RT,p['low'])
    Hc,MX=mkpair3(p['starts'],p['half'],3,p['minw']); Hc=dict(Hc); Hc['line']=p['hline']; Hh=mkhours(p['hrs'],p['nd'])
    SP=dict(name='spread',gap=GSP,line=p['spr'],pubs=SP_PUBS)
    SV=mkpair_svx(p['starts'],p['vk'],p['vb'],p['vl'])
    def hubv(sl,back):
        calls=[]; armed=True
        for m,v in g.items():
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
    C1=[Vc,Hh,SP]; C2=[Hc,SP,SV]
    legs={'U':[(a,b) for a,b,c in confirm_wx(leg_gapL_cx(spl,p['u45'],p['look'])+F45,C1,'month')],
          'L':[(a,b) for a,b,c in confirm_wx(leg_gapL_x(spl,p['low'],52,rearm='window')+F25,C2,'month')],
          'X':[(a,b) for a,b,c in hubv(p['sahm'],p['hback'])],'I':[(a,b) for a,b,c in confirm_wx(leg_ic_cx(ICfp,p['ic']),C1,'month')]}
    if p.get('wline'): legs['W']=[(a,b) for a,b,c in confirm_wx(leg_sv_x(p['wline'],rearm='zero'),C2,'month')]
    if p.get('wline2'): legs['V']=[(a,b) for a,b,c in confirm_wx(leg_sv_x(p['wline2'],rearm='window'),C2,'month')]
    if p.get('bshare'): legs['B']=[(a,b) for a,b,c in confirm_wx(leg_br_x(p['bshare']),C2,'month')]
    if p.get('kc'): legs['K']=[(a,b) for a,b in leg_K_x(ICfp,p['kc'][0],p['kc'][1])]
    TL=dict(TLH); TL['R']=RC[p['rst']]; TL['T']=TC[p['tst']]; TL['Q']=QC[p['qst']]
    if p.get('cD') is not None: TL['C']=CMENU[(p['cD'],p['cn'],p['cs'])]
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TL)
    return score13(turns),turns
# ---- the grid gains the sudden-stop route, safest first, kept where it costs nothing ----
GRID=GRID+[('kc',[(35,20),(35,15),(30,15),(30,10),None])]; NAMES=[n for n,_ in GRID]; GD=dict(GRID)
BASE15=dict(BASE15); BASE15['kc']=None
# ---- the walk itself: walk39's loop, verbatim ----
exec(open('walk39.py').read().split(_MARK)[1].split("\n",1)[1])
