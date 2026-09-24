from mini import *
from hub import leg_X2
from legu_min import leg_U, s_cur, spl
out=open('fast4.out','w')
def P(*a):
    print(*a); print(*a,file=out); out.flush()
n=o['nat67']; ic4=n['ic_sa'].dropna().rolling(4).mean(); rise=(ic4/ic4.rolling(52,min_periods=52).min().shift(1)-1)*100
def leg_N(line=30.0,pub=5):
    c=[]; armed=True
    for t,v in rise.dropna().items():
        if armed and v>=line: c.append((t+pd.Timedelta(days=pub),pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=0.0: armed=True
    return c
N30=leg_N(30.0); P("leg N (initial claims 4-wk avg 30% above 52-wk min, re-arm at 0):",[(p.strftime('%Y-%m-%d'),d.strftime('%Y-%m')) for p,d in N30])
KJHS={k:TLG[k] for k in 'KJHS'}
SEC['V']=dict(name='vacancy',gap=vr,line=0.30,pub_day=30)
X43=leg_X2(sahm_line=0.43,vac_line=0.30); X50=leg_X2(sahm_line=0.50,vac_line=0.30)
U45=leg_U(s_cur,0.45); U45f=leg_U(spl,0.45)
def show(nm,pk,cf):
    r=score13(chron(pk,KJHS,cf)); lp=[r['lags_p'].get(i) for i in range(13)]; v=[l for l in lp if l is not None]; v73=[r['lags_p'][i] for i in range(5,13) if i in r['lags_p']]
    P(f"\n{nm}\n   lags {[('-' if l is None else l) for l in lp]}  other {[(d,lg) for _,d,lg in r['other']]}")
    P(f"   all 13: median {np.median(v):.0f} mean {np.mean(v):.1f} worst {max(v)} | 1973 on: median {np.median(v73):.1f} mean {np.mean(v73):.1f} | <=0 {sum(1 for l in v if l<=0)} <=7 {sum(1 for l in v if l<=7)} <=31 {sum(1 for l in v if l<=31)} | dates exact {sum(1 for e in r['errs_p'].values() if e==0)} within1 {sum(1 for e in r['errs_p'].values() if abs(e)<=1)}")
    for i in range(5,13):
        if i in r['opens']: t=r['opens'][i]; P(f"      {PK[i]:%Y-%m}: {t['published']:%Y-%m-%d} by {t['leg']} dated {t['date']:%Y-%m} ({t.get('condition')})")
show("A-PRIORI CORNER: U 0.50 | hub Sahm 0.50, vacancy 0.36, U confirmed by V|H|P",{'U':leg_U(s_cur,0.50),'X':leg_X2(0.50,vac_line=0.36)},['V','H','P']) if False else None
show("CONSTRUCTION-GRADE CORNER: U 0.45, vacancy 0.30, hub Sahm 0.43; U confirmed by V|H|P",{'U':U45,'X':X43},['V','H','P'])
show("same + leg N (initial claims +30%) as a second weekly proposer",{'U':U45,'N':N30,'X':X43},['V','H','P'])
show("same, U on the Department's advance first prints",{'U':U45f,'N':N30,'X':X43},['V','H','P'])
show("core only (no pairs): U 0.45, vacancy 0.30, hub 0.43, V confirms",{'U':U45,'X':X43},['V'])
show("core + N, no pairs",{'U':U45,'N':N30,'X':X43},['V'])
out.close()
