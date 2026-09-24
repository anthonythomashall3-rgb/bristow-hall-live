"""Publication lags corrected (IUR and continued claims: 12 days after their week, not 5; state page-8 insured unemployment 12; K and J +7 days),
Sahm hub on ALFRED's actual first-print release dates; then structural speed variants: re-arm rule, 26-week minimum, permits pair."""
from mini import *
from legu_min import s_cur, spl
import alfred
exec(open('fast8.py').read().split("X43=[(p,dd,'hub')")[0].replace("out=open('fast8.out','w')","out=open('fast16.out','w')"))
# ---- actual release dates of the unemployment rate's first prints (ALFRED vintage dates)
vd=pd.DatetimeIndex(alfred.vintages('UNRATE'))
def ur_release(m):
    """first vintage date after month m ends (the first print of m)"""
    after=vd[vd>m+pd.offsets.MonthEnd(0)]; return after[0] if len(after) else m+pd.DateOffset(months=1)+pd.Timedelta(days=4)
rel=pd.Series({m:ur_release(m) for m in g.index if m>=pd.Timestamp('1960-03-01')})
P("UNRATE first-print release day-of-month (1960 on): median",int(rel.dt.day.median()),"min",int(rel.dt.day.min()),"max",int(rel.dt.day.max()))
def hub(sahm_line,vac,vac_line,back=6):
    calls=[]; armed=True
    for m,v in g.items():
        if m<pd.Timestamp('1948-06-01'): continue
        if armed and v>=sahm_line:
            w=vac[(vac.index>=m-pd.DateOffset(months=back))&(vac.index<=m)]; hit=w[w>=vac_line]
            if len(hit):
                k=hit.index[0]; sp=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
                pub=max(sp,pd.Timestamp(k.year,k.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29))
                calls.append((pub,m-pd.DateOffset(months=3),'hub')); armed=False
        elif not armed and v<sahm_line: armed=True
    return calls
rate_half=(((UR-UR.rolling(12).min())*10).round()/2.0); hous_half=(lh.rolling(12).max()-lh.rolling(2).mean())/35.0
PAIRX=pd.concat([hous_half,rate_half],axis=1).min(axis=1).dropna(); HpX=dict(name='housing35x',gap=PAIRX,line=1.0,pub_day=18)
PM=first_prints('PERMIT'); lp_=np.log(PM)*100
perm2=(lp_.rolling(12).max()-lp_.rolling(2).mean())/35.0; PERM=pd.concat([perm2,rate_half],axis=1).min(axis=1).dropna(); HpP=dict(name='permits35x',gap=PERM,line=1.0,pub_day=18)
V36=dict(name='vacancy36',gap=vr,line=0.36,pub_day=30)
sys.path.insert(0,W+'/lab/slack'); from objects import load
fh=load()['IUR (FH)'].dropna(); gm=(fh-fh.rolling(12,min_periods=12).min().shift(1)).dropna()
def leg_gap_m(gap,line,rearm=0.0,pub_day=10):
    c=[]; armed=True
    for m,v in gap.items():
        if armed and v>=line: c.append((pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=pub_day-1),pd.Timestamp(m.year,m.month,1))); armed=False
        elif not armed and v<=rearm: armed=True
    return c
FH45=[x for x in leg_gap_m(gm,0.45) if x[1]<pd.Timestamp('1971-01-01')]
def leg_gapx(s,line,look=52,pub=12,rearm='zero'):
    """re-arm: 'zero' = gap back to <=0; 'line' = gap back below the line; 'window' = the proposal's window (4 months) closed and gap below the line"""
    gap=(s-s.rolling(look,min_periods=look).min().shift(1)).dropna(); c=[]; armed=True; last=None
    for t,v in gap.items():
        if armed and v>=line: c.append((t+pd.Timedelta(days=pub),pd.Timestamp(t.year,t.month,1))); armed=False; last=t
        elif not armed:
            if rearm=='zero' and v<=0: armed=True
            elif rearm=='line' and v<line: armed=True
            elif rearm=='window' and v<line and t>last+pd.DateOffset(months=4): armed=True
    return c
def leg_br12(Bx,line=50.0,k=1,quiet_weeks=26,pub_days=12): return leg_br(Bx,line,k,quiet_weeks,pub_days)
TLC={k:TLG[k] for k in 'HS'}; TLC['K']=[(p+pd.Timedelta(days=7),d) for p,d in TLG['K']]; TLC['J']=[(p+pd.Timedelta(days=7),d) for p,d in TLG['J']]
def run2(nm,legs,TL=TLC):
    pk={k:[(p,dd) for p,dd,_ in v] for k,v in legs.items()}
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(pk,TL)
    r=score13(turns); lp=[r['lags_p'].get(i) for i in range(13)]; v73=[r['lags_p'][i] for i in range(5,13) if i in r['lags_p']]; lt=[r['lags_t'].get(i) for i in range(13)]; tv=[l for l in lt if l is not None]
    P(f"\n{nm}\n   onsets {[('-' if l is None else l) for l in lp]} other {[(d,lg) for _,d,lg in r['other']]} | 1973 on median {np.median(v73):.1f} mean {np.mean(v73):.1f} <=31 {sum(1 for l in v73 if l<=31)} | dates exact {sum(1 for e in r['errs_p'].values() if e==0)} w1 {sum(1 for e in r['errs_p'].values() if abs(e)<=1)}")
    P(f"   troughs {[('-' if l is None else l) for l in lt]} | median {np.median(tv):.0f} exact {sum(1 for e in r['errs_t'].values() if e==0)}")
    cond={(p,dd):c for vv in legs.values() for p,dd,c in vv}
    for i in range(5,13):
        if i in r['opens']: t=r['opens'][i]; P(f"      {PK[i]:%Y-%m}: {t['published']:%Y-%m-%d} by {t['leg']} dated {t['date']:%Y-%m} ({cond.get((t['published'],t['date']),'?')})")
    return r
for vint,s,Bx in [('CURRENT FILE',s_cur,BR),('FIRST PRINTS',spl,BRs)]:
    P(f"\n==== {vint} ====")
    X=hub(0.50,vr,0.36)
    base={'U':confirm(leg_gapx(s,0.45)+FH45,[V36,HpX,Pp]),'L':confirm(leg_gapx(s,0.25),[HpX]),'R':confirm(leg_br12(Bx),[HpX]),'X':X}
    run2("A. fast form, CORRECTED publication lags (IUR/CC 12 d, breadth 12 d, K/J +7, Sahm on actual release dates)",base)
    run2("B. A with U-low re-armed when its window closes (4 months) and the gap is below the line",{**base,'L':confirm(leg_gapx(s,0.25,rearm='window'),[HpX])})
    run2("C. B without the breadth branch",{k:v for k,v in {**base,'L':confirm(leg_gapx(s,0.25,rearm='window'),[HpX])}.items() if k!='R'})
    run2("D. A with U-low on a 26-week minimum",{**base,'L':confirm(leg_gapx(s,0.25,look=26),[HpX])})
    run2("E. A with the pair on PERMITS instead of starts (U-low and breadth confirmers)",{**base,'L':confirm(leg_gapx(s,0.25),[HpP]),'R':confirm(leg_br12(Bx),[HpP])})
    run2("F. A with permits OR starts as confirmers",{**base,'L':confirm(leg_gapx(s,0.25),[HpX,HpP]),'R':confirm(leg_br12(Bx),[HpX,HpP])})
def inwin(d,back=6,fwd=18): return any(pp-pd.DateOffset(months=back)<=d<=t+pd.DateOffset(months=fwd) for pp,t in zip(PK,TR))
q=[(m.strftime('%Y-%m'),round(v,2)) for m,v in PERM.items() if v>=0.8 and not inwin(m) and m>=pd.Timestamp('1960-01-01')]
P("\npermits pair quiet readings >=0.8:",q)
P("permits pair first at-line month vs peak:",[ (lambda seg: (md(seg[seg>=1.0].index[0],pp) if (seg>=1.0).any() else None))(PERM[(PERM.index>=pp-pd.DateOffset(months=6))&(PERM.index<=t)]) for pp,t in zip(PK,TR)])
P("starts pair first at-line month vs peak: ",[ (lambda seg: (md(seg[seg>=1.0].index[0],pp) if (seg>=1.0).any() else None))(PAIRX[(PAIRX.index>=pp-pd.DateOffset(months=6))&(PAIRX.index<=t)]) for pp,t in zip(PK,TR)])
out.close()
