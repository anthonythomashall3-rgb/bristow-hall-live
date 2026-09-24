"""TWO CLEAN GAINS. (1) The Fieldhouse gap is a reconstruction carried to six places: August 1953 reads 0.249993 and misses the 0.25 line by
seven millionths, which costs thirty days at 1953. Rounded to three decimals — the precision the reconstruction actually carries — it fires.
(2) Leg H dates its call on the tenth of the following month; the weekly release that completes a month's initial claims is public about five
days after the month ends (collection 45 verifies this on every release since 2002). Both are clocks/precision, not lines."""
from mini import *
from legu_min import s_cur, spl
exec(open('fast40.py').read().split("V26=dict(")[0].replace("out=open('fast40.out','w')","out=open('fix1.out','w')"))
V26=dict(sahm=0.50,vac=0.35,u45=0.45,low=0.25,starts=33,half=4,h1=2.0,h2=1.20)
P("Fieldhouse gap near its lines:",[(m.strftime('%Y-%m'),float(v)) for m,v in gm['1953-07':'1953-09'].items()])
def leg_gap_mx3(gap,line,pub_day=10,rearm='window',rnd=3):
    c=[]; armed=True; last=None
    for m,v in gap.round(rnd).items():
        if armed and v>=line: c.append((pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=pub_day-1),m)); armed=False; last=m
        elif not armed and rearm=='window' and v<line and m>=last+pd.DateOffset(months=4): armed=True
    return c
for rnd in [9,3,2]:
    P(f"round {rnd}dp: FH 0.45 {[(d.strftime('%Y-%m')) for p,d in leg_gap_mx3(gm,0.45,rnd=rnd) if d<pd.Timestamp('1971-01-01')]} | FH 0.25 {[(d.strftime('%Y-%m')) for p,d in leg_gap_mx3(gm,0.25,rnd=rnd) if d<pd.Timestamp('1971-01-01')]}")
TL2={k:list(v) for k,v in TLC.items()}
TL2['H']=[(pd.Timestamp(d.year,d.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=5),d) for p,d in TLC['H']]
def run2(p,s,rnd=9,TL=TLC):
    F45=[x for x in leg_gap_mx3(gm,p['u45'],rnd=rnd) if x[1]<pd.Timestamp('1971-01-01')]
    F25=[x for x in leg_gap_mx3(gm,p['low'],rnd=rnd) if x[1]<pd.Timestamp('1971-01-01')]
    Vc=dict(name='vac',gap=vr,line=p['vac'],pubs=VJ36['pubs']); Hc,_=mkpair(p['starts'],p['half']); Hh=mkhours(p['h1'],p['h2'])
    U=confirm_w(leg_gapx(s,p['u45'],rearm='zero')+F45,[Vc,Hh],'month'); L=confirm_w(leg_gapx(s,p['low'],rearm='window')+F25,[Hc],'month'); X=hub_actual(p['sahm'],vr,p['vac'])
    pk={'U':[(a,b) for a,b,c in U],'L':[(a,b) for a,b,c in L],'X':[(a,b) for a,b,c in X]}
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(pk,TL)
    return score13(turns)
for nm,rnd,TL in [('v2.6 as shipped',9,TLC),('+ Fieldhouse gap rounded to 3dp',3,TLC),('+ leg H on the true release clock (5 days after month end)',9,TL2),('+ BOTH',3,TL2)]:
    rs=[run2(V26,s,rnd,TL) for s in (s_cur,spl)]
    lp=[rs[0]['lags_p'].get(i) for i in range(13)]; lt=[rs[0]['lags_t'].get(i) for i in range(13)]
    v73=[rs[0]['lags_p'][i] for i in range(5,13) if i in rs[0]['lags_p']]; tv=[x for x in lt if x is not None]
    P(f"\n{nm}\n   onsets {lp} | fp2007 {rs[1]['lags_p'].get(10)} | 1973-on med {np.median(v73):.1f} | others {[o[1] for r in rs for o in r['other']]} | detected {len(rs[0]['lags_p'])}/13")
    P(f"   troughs {lt} | median {np.median(tv):.0f} mean {np.mean(tv):.1f} | dates exact {sum(1 for e in rs[0]['errs_t'].values() if e==0)}")
out.close()
