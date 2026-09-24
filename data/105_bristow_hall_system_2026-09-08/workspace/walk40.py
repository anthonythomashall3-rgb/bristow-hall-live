"""WALK 40 - WALK 39 WITH THE HUB'S "STILL FALLING" CLAUSE (Rule 20; declared 8 September 2026, in the evening, after the
audit's finding). Everything is walk39's - the objects on first prints, the actual release days, the grid, the windows,
the walk - with one clause added to the hub and one detail of the vacancy's construction:

THE HUB READS A RISE IN UNEMPLOYMENT AGAINST VACANCIES ALREADY FALLING. "Already falling" is a statement about the
present. The hub as walked asked the vacancy rate to have held its line (a fall of 0.20 or more from its four-month
high) in two months of the previous year; it did not ask whether the fall was still under way when the unemployment
reading arrived. On the data a user had at the time, that let it fire on 16 December 2025: the vacancy rate as first
printed had fallen in March to June 2025 and recovered by the autumn (its latest print on 16 December, September's,
stood at 0.06 against the line of 0.20), and the Sahm gap crossed its line five months after the fall in vacancies had
ended - the sequence the hub was built to read, demand giving way and then labor following, had broken. The clause:
on the day the unemployment reading arrives, the vacancy's latest published print must stand at its line. Two holds
within the year say the fall was real; the latest print says it has not ended. Every hub call that dates a recession
in the record (1957, 2024) and every one the record does not need (1949, 1953, 1960, 1970, 1974, 1980, 1981, 1990,
2001, 2008, 2020 - all made after another branch had opened the recession) satisfies it: in each the vacancy was at
its line in the last print before the unemployment reading. It is a clause, not a number: nothing is added to the
grid. Declared after the December 2025 case was seen, and logged as such (Rule Zero).

THE LABOR FORCE CARRIED OVER A MISSING MONTH. The vacancy rate on first prints is openings over the labor force, both
as first printed. The household survey was not taken in October 2025 (the lapse in appropriations), so no labor-force
figure exists for that month; walk39 dropped the month, which made the four-month windows around it span five
calendar months. Here the last published labor force is carried over a gap of at most two months, as any user would
have done, so the openings of October 2025 (released 9 December 2025) give a reading.

Run:  python3 walk40.py 1962 2026 w40   (the diary from the 1962 cut; ~20 minutes)"""
import sys,pickle,os
_MARK="# ---- the walk "+"itself"                      # the marker bhs_build.py and bhs_verify.py split a walk file at (kept out of these lines)
exec(open('walk39.py').read().split(_MARK)[0].replace("walk39_%s.out","walk40_%s.out"))
import pandas as pd, numpy as np

# ---- the vacancy on first prints, the labor force carried over a missing month ----
_vf2=(_JF/_CF.reindex(_JF.index).ffill(limit=2)*100).dropna(); _vf2=_vf2[_vf2.index>=pd.Timestamp('2010-07-01')]
assert len(_vf2)>150 and _vf2.index.max()>=pd.Timestamp('2026-01-01'), 'vacancy first prints missing'
V0=pd.concat([V0[V0.index<_vf2.index.min()],_vf2]).sort_index()

# ---- the rule: walk39's build_v with the hub's "still falling" clause ----
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
                ok=len(hit)>=2                                   # a line touched in one month is not a confirmation
                if ok:                                           # STILL FALLING: the latest print public on the reading's day stands at the line
                    known=pubs[(pubs.index<=m)&(pubs<=sp)]
                    ok=len(known)>0 and float(G.get(known.index.max(),np.nan))>=p['vl']
                if ok:
                    kk=hit.index[1]
                    calls.append((max(sp,pubs[kk]),m-pd.DateOffset(months=3),'hub')); armed=False
            elif not armed and v<sl: armed=True
        return calls
    C1=[Vc,Hh,SP]; C2=[Hc,SP]
    legs={'U':[(a,b) for a,b,c in confirm_w(leg_gapL(spl,p['u45'],p['look'],rearm='zero')+F45,C1,'month')],
          'L':[(a,b) for a,b,c in confirm_w(leg_gapL(spl,p['low'],52,rearm='window')+F25,C2,'month')],
          'X':[(a,b) for a,b,c in hubv(p['sahm'],p['hback'])],'I':[(a,b) for a,b,c in confirm_w(leg_ic(ICfp,p['ic']),C1,'month')]}
    if p.get('wline'): legs['W']=[(a,b) for a,b,c in confirm_w(leg_sv(p['wline'],rearm='zero'),C2,'month')]
    if p.get('wline2'): legs['V']=[(a,b) for a,b,c in confirm_w(leg_sv(p['wline2'],rearm='window'),C2,'month')]
    if p.get('bshare'): legs['B']=[(a,b) for a,b,c in confirm_w(leg_br(p['bshare']),C2,'month')]
    TL=dict(TLH); TL['R']=RC[p['rst']]; TL['T']=TC[p['tst']]; TL['Q']=QC[p['qst']]
    if p.get('cD') is not None: TL['C']=CMENU[(p['cD'],p['cn'],p['cs'])]
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TL)
    return score13(turns),turns

# ---- the walk itself: walk39's loop (walk38's, with the followed-to-its-close clause), verbatim ----
exec(open('walk39.py').read().split(_MARK)[1].split("\n",1)[1])
