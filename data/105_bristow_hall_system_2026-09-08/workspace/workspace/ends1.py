"""Two-sided END: the Philadelphia survey's turn (leg P) paired with a LIGHTER continued-claims fall (K-light: fewer falling weeks,
smaller drop); the call is the later of the two, the date is the claims maximum's month.  Compared with K,J,H,S and with P alone."""
from mini import *
from hub import leg_X2
from legu_min import s_cur, spl
exec(open('fast8.py').read().split("X43=[(p,dd,'hub')")[0].replace("out=open('fast8.out','w')","out=open('ends1.out','w')"))
import cc_trough_grid as CG
rate_half=(((UR-UR.rolling(12).min())*10).round()/2.0); hous_half=(lh.rolling(12).max()-lh.rolling(2).mean())/35.0
PAIRX=pd.concat([hous_half,rate_half],axis=1).min(axis=1).dropna(); HpX=dict(name='housing35x',gap=PAIRX,line=1.0,pub_day=18)
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
gp=gapof(s_cur)
U45=confirm(leg_gap(gp,0.45)+FH45,[V36,HpX,Pp]); UL=confirm(leg_gap(gp,0.25),[HpX]); BRL=confirm(leg_br(BR),[HpX]); X=[(p,dd,'hub') for p,dd in leg_X2(sahm_line=0.50,vac_line=0.36)]
PKL={k:[(p,dd) for p,dd,_ in v] for k,v in {'U':U45,'L':UL,'R':BRL,'X':X}.items()}
D4=CG.series(4)
Pcalls=TLG['P']
def klight(rt,delta,nth=30.0): return [(p,d) for p,d in CG.calls(D4,rt,delta,nth) if p>=pd.Timestamp('1969-06-01')]
def two_sided_end(kl, pc, back_months=6, fwd_months=4):
    """K-light call confirmed by a Philadelphia call inside [k_pub - back, k_pub + fwd] (P may come first); published at the later; dated K-light's month"""
    out=[]
    for kp,kd in kl:
        ps=[pp for pp,_ in pc if kp-pd.DateOffset(months=back_months)<=pp<=kp+pd.DateOffset(months=fwd_months)]
        if ps: out.append((max(kp,min(ps)),kd))
    return out
def runT(nm,TL):
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(PKL,TL)
    r=score13(turns); lt=[r['lags_t'].get(i) for i in range(13)]; et=[r['errs_t'].get(i) for i in range(13)]; tv=[l for l in lt if l is not None]
    tr=[t for t in turns if t['kind']=='trough']
    others=[(t['published'].strftime('%Y-%m-%d'),t['leg'],t['date'].strftime('%Y-%m')) for t in tr if not any(abs(md(t['date'],q))<=6 for q in TR)]
    P(f"{nm:52} troughs {[('-' if l is None else l) for l in lt]} errs {[('-' if e is None else e) for e in et]} | n {len(tv)} med {np.median(tv):.0f} mean {np.mean(tv):.1f} <=31 {sum(1 for l in tv if l<=31)} exact {sum(1 for e in et if e==0)} w1 {sum(1 for e in et if e is not None and abs(e)<=1)} | other ends {others}")
P("K as shipped: rt=6 falling weeks, drop 4, arm 30.  P: Philadelphia survey after D (calls 1975-02-18, 1980-08-18, 1982-10-18, 1991-05-18, 2009-04-18, 2020-05-18)")
runT("K,J,H,S",{k:TLG[k] for k in 'KJHS'})
runT("K,J,H,S,P",{k:TLG[k] for k in 'KJHSP'})
for rt,delta in [(6,4.0),(4,2.0),(3,2.0),(3,1.0),(2,1.0),(2,0.5),(1,0.5)]:
    kl=klight(rt,delta)
    P(f"\nK-light rt={rt} drop={delta}: raw calls {[(p.strftime('%Y-%m-%d'),d.strftime('%Y-%m')) for p,d in kl]}")
    TL={k:TLG[k] for k in 'JHS'}; TL['K']=TLG['K']; TL['E']=two_sided_end(kl,Pcalls)
    runT(f"  K,J,H,S + (K-light rt{rt}/d{delta} & P)",TL)
    TL2={k:TLG[k] for k in 'JHS'}; TL2['Kl']=kl
    runT(f"  K-light alone replacing K (+J,H,S)",TL2)
out.close()
