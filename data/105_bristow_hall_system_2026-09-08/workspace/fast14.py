"""Pair arithmetic fixed (rate half in exact tenths), fast form re-run on both vintages; closers with P (Philadelphia survey), I, T added."""
from mini import *
from hub import leg_X2
from legu_min import s_cur, spl
exec(open('fast8.py').read().split("X43=[(p,dd,'hub')")[0].replace("out=open('fast8.out','w')","out=open('fast14.out','w')"))
# exact pair: rate half = round((UR-min)*10)/2 ; housing half continuous
rate_half=(((UR-UR.rolling(12).min())*10).round()/2.0); hous_half=(lh.rolling(12).max()-lh.rolling(2).mean())/35.0
PAIRX=pd.concat([hous_half,rate_half],axis=1).min(axis=1).dropna()
diff=(PAIRX>=1.0)!=(PAIR>=1.0); P("months where the exact pair differs from the float pair at the 1.0 line:",[m.strftime('%Y-%m') for m in PAIRX.index[diff.reindex(PAIRX.index).fillna(False)]])
HpX=dict(name='housing35x',gap=PAIRX,line=1.0,pub_day=18)
sys.path.insert(0,W+'/lab/slack'); from objects import load
fh=load()['IUR (FH)'].dropna(); gm=(fh-fh.rolling(12,min_periods=12).min().shift(1)).dropna()
def leg_gap_m(gap,line,rearm=0.0,pub_day=10):
    c=[]; armed=True
    for m,v in gap.items():
        if armed and v>=line: c.append((pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=pub_day-1),pd.Timestamp(m.year,m.month,1))); armed=False
        elif not armed and v<=rearm: armed=True
    return c
FH45=[x for x in leg_gap_m(gm,0.45) if x[1]<pd.Timestamp('1971-01-01')]
V36=dict(name='vacancy36',gap=vr,line=0.36,pub_day=30)
def runT(nm,legs,TL):
    pk={k:[(p,dd) for p,dd,_ in v] for k,v in legs.items()}
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(pk,TL)
    r=score13(turns); lp=[r['lags_p'].get(i) for i in range(13)]; lt=[r['lags_t'].get(i) for i in range(13)]; et=[r['errs_t'].get(i) for i in range(13)]
    v73=[r['lags_p'][i] for i in range(5,13) if i in r['lags_p']]; tv=[l for l in lt if l is not None]
    P(f"\n{nm}\n   onsets {[('-' if l is None else l) for l in lp]} other {[(d,lg) for _,d,lg in r['other']]} | 1973 on median {np.median(v73):.1f} mean {np.mean(v73):.1f}")
    P(f"   troughs {[('-' if l is None else l) for l in lt]} errs {[('-' if e is None else e) for e in et]} | n {len(tv)} median {np.median(tv):.0f} mean {np.mean(tv):.1f} worst {max(tv)} <=31 {sum(1 for l in tv if l<=31)} exact {sum(1 for e in et if e==0)} within1 {sum(1 for e in et if e is not None and abs(e)<=1)}")
    tr=[t for t in turns if t['kind']=='trough']; opens=[t for t in turns if t['kind']=='peak']
    others=[(t['published'].strftime('%Y-%m-%d'),t['leg'],t['date'].strftime('%Y-%m')) for t in tr if not any(abs(md(t['date'],q))<=6 for q in TR)]
    if others: P("   other trough calls:",others)
    return r
for vint,s,Bx in [('CURRENT FILE',s_cur,BR),('FIRST PRINTS',spl,BRs)]:
    gp=gapof(s)
    U45=confirm(leg_gap(gp,0.45)+FH45,[V36,HpX,Pp]); UL=confirm(leg_gap(gp,0.25),[HpX]); BRL=confirm(leg_br(Bx),[HpX]); X=[(p,dd,'hub') for p,dd in leg_X2(sahm_line=0.50,vac_line=0.36)]
    legs={'U':U45,'L':UL,'R':BRL,'X':X}
    P(f"\n==== {vint}, exact pair ====")
    for cl,keys in [("K,J,H,S",'KJHS'),("K,J,H,S + P (Philadelphia survey)",'KJHSP'),("K,J,H,S + I (weekly initial claims)",'KJHSI'),("K,J,H,S + T",'KJHST'),("K,J,H,S + P + I",'KJHSPI')]:
        runT(f"{vint}: closers {cl}",legs,{k:TLG[k] for k in keys})
out.close()
