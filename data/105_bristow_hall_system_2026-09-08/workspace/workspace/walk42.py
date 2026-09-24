"""WALK 42 - WALK 40 WITH THE CO-SIGNER (declared 9 September 2026, before the run). Everything is walk40's - the
objects on first prints, the actual release days, the hub's still-falling clause, the windows, the walk, the objective,
the tie-break, the depth step - with one clause added to two proposers and two values added to one grid:

THE CO-SIGNER. The two proposers the walk sets at the fast edge of the grid - the four-week mean of initial claims
(the claims line is the loosest the grid offers) and the insured unemployment rate above its 91-week low - are
administrative counts, and in the 2020s their expansion-time readings came within a point (August 2022) and a tenth
(April 2023) of their lines while a demand-side confirmer was in place. A NEAR-LINE proposal from either object - the
claims object within 15 points above its line, the insured rate within 0.2 point above its line - must be co-signed by
the household survey: the three-month average of the unemployment rate at least 0.2 point above its low of the prior
twelve months, as last published (first print) on the proposal day. A STRONG proposal, above the band, needs no
co-signer. A near-line proposal that is not co-signed stays armed and is re-tested each week; it fires the week the
co-signature arrives or the reading clears the band. Both objects had refused the 2022 and 2023 readings by a hair;
with the co-signer the household survey refuses them outright (its gap was 0.0 in August 2022 and 0.0 in April 2023),
so the claims line can be walked lower without a false alarm. The other proposers are untouched: the early calls of
1969, 1973, 1979 and 1981 were theirs, made before the household survey had moved, and the co-signer would only slow them.

THE GRID. The claims line's grid gains 40 and 35 below 45 (60, 50, 45, 40, 35), safest first as before.

Declared after the 2022-2023 readings were examined (Rule Zero); the walk decides from 1962 whether and when the
lower lines are clean. Run:  python3 walk42.py 1962 2026 w42   (fresh summary cache; ~20-40 minutes)"""
import sys,pickle,os
_MARK="# ---- the walk "+"itself"
exec(open('walk40.py').read().split(_MARK)[0].replace("walk40_%s.out","walk42_%s.out"))
import pandas as pd, numpy as np

# ---- the grid: the claims line may go to 40 and 35 ----
GRID=[(n,([60,50,45,40,35] if n=='ic' else g)) for n,g in GRID]; NAMES=[n for n,_ in GRID]; GD=dict(GRID)

# ---- the co-signer ----
COS_THR=0.2; IC_BAND=15.0; U_BAND=0.2
gpub=pd.Series({rel[m]:float(g[m]) for m in g.index if m in rel}).sort_index()
def cosign(day,thr=COS_THR):
    s=gpub[gpub.index<=day]; return len(s)>0 and float(s.iloc[-1])>=thr
def leg_ic_c(s,pct,band=IC_BAND,look=52):
    m4=s.rolling(4).mean(); rel_=(m4/m4.rolling(look,min_periods=look).min().shift(1)-1)*100
    c=[]; armed=True
    for t,v in rel_.dropna().items():
        if armed and v>=pct:
            day=rel_ic(t)
            if v>=pct+band or cosign(day): c.append((day,pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=0: armed=True
    return c
def leg_gapL_c(s,line,look,band=U_BAND):
    gap=(s-s.rolling(look,min_periods=look).min().shift(1)).dropna(); c=[]; armed=True
    for t,v in gap.items():
        if armed and v>=line:
            day=rel_iu(t)
            if v>=line+band or cosign(day): c.append((day,pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=0: armed=True
    return c

# ---- the rule: walk40's build_v with the co-signed U and I legs ----
def build_v(p):
    G=vgap2(p['vk'],p['vb']); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=p['vl'],pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,p['u45'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['u45'])
    F25=[x for x in leg_gap_mx2(gm,p['low'],boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]+leg_rt(RT,p['low'])
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
                    kk=hit.index[1]
                    calls.append((max(sp,pubs[kk]),m-pd.DateOffset(months=3),'hub')); armed=False
            elif not armed and v<sl: armed=True
        return calls
    C1=[Vc,Hh,SP]; C2=[Hc,SP]
    legs={'U':[(a,b) for a,b,c in confirm_w(leg_gapL_c(spl,p['u45'],p['look'])+F45,C1,'month')],
          'L':[(a,b) for a,b,c in confirm_w(leg_gapL(spl,p['low'],52,rearm='window')+F25,C2,'month')],
          'X':[(a,b) for a,b,c in hubv(p['sahm'],p['hback'])],'I':[(a,b) for a,b,c in confirm_w(leg_ic_c(ICfp,p['ic']),C1,'month')]}
    if p.get('wline'): legs['W']=[(a,b) for a,b,c in confirm_w(leg_sv(p['wline'],rearm='zero'),C2,'month')]
    if p.get('wline2'): legs['V']=[(a,b) for a,b,c in confirm_w(leg_sv(p['wline2'],rearm='window'),C2,'month')]
    if p.get('bshare'): legs['B']=[(a,b) for a,b,c in confirm_w(leg_br(p['bshare']),C2,'month')]
    TL=dict(TLH); TL['R']=RC[p['rst']]; TL['T']=TC[p['tst']]; TL['Q']=QC[p['qst']]
    if p.get('cD') is not None: TL['C']=CMENU[(p['cD'],p['cn'],p['cs'])]
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TL)
    return score13(turns),turns

# ---- the walk itself: walk39's loop (walk38's, with the followed-to-its-close clause), verbatim ----
exec(open('walk39.py').read().split(_MARK)[1].split("\n",1)[1])
