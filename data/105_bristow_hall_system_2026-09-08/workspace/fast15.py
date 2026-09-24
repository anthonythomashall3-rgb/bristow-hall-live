"""Causal replay of the fast form's new branch: at each recession from 1973 choose (U-low line, pair line) on the record before it."""
from mini import *
from hub import leg_X2
from legu_min import s_cur, spl
exec(open('fast8.py').read().split("X43=[(p,dd,'hub')")[0].replace("out=open('fast8.out','w')","out=open('fast15.out','w')"))
rate_half=(((UR-UR.rolling(12).min())*10).round()/2.0); hous_half=(lh.rolling(12).max()-lh.rolling(2).mean())/35.0
PAIRX=pd.concat([hous_half,rate_half],axis=1).min(axis=1).dropna()
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
gp=gapof(s_cur); X=[(p,dd,'hub') for p,dd in leg_X2(sahm_line=0.50,vac_line=0.36)]
KJHS={k:TLG[k] for k in 'KJHS'}
cells={}
for ul in [0.15,0.25,0.35,0.45]:
    for pl in [0.8,1.0,1.2]:
        Hx=dict(name='housing',gap=PAIRX,line=pl,pub_day=18)
        U45=confirm(leg_gap(gp,0.45)+FH45,[V36,Hx,Pp]); UL=confirm(leg_gap(gp,ul),[Hx]) if ul<0.45 else []; BRL=confirm(leg_br(BR),[Hx])
        pk={k:[(p,dd) for p,dd,_ in v] for k,v in {'U':U45,'L':UL,'R':BRL,'X':X}.items()}
        with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(pk,KJHS)
        r=score13(turns); cells[(ul,pl)]=dict(lags=r['lags_p'],other=[pd.Timestamp(d+'-01') for _,d,_ in r['other']])
        P(f"cell U-low {ul} pair {pl}: 1973 on {[r['lags_p'].get(i,'-') for i in range(5,13)]} other {[(d,lg) for _,d,lg in r['other']]}")
P("\nCAUSAL REPLAY (fast criterion: every prior recession called, no prior other call, then fastest prior median; safe: fewest prior other, then highest lines)")
for crit in ['fast','safe']:
    res=[]
    for k in range(5,13):
        p=PK[k]; best=None
        for (ul,pl),c in cells.items():
            if any(i not in c['lags'] for i in range(k)): continue
            noth=sum(1 for d in c['other'] if d<p)
            if crit=='fast':
                if noth>0: continue
                key=(np.median([c['lags'][i] for i in range(k)]),)
            else: key=(noth,-ul,-pl)
            if best is None or key<best[0]: best=(key,(ul,pl))
        (ul,pl)=best[1]; lag=cells[(ul,pl)]['lags'].get(k); res.append(lag); P(f"  {crit} {p:%Y-%m}: chose U-low {ul} pair {pl} -> lag {lag}")
    P(f"  {crit}: {sum(1 for l in res if l is not None)}/8 called, median {np.median([l for l in res if l is not None]):.1f}")
out.close()
