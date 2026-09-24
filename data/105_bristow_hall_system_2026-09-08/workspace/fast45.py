"""Initial claims as a THIRD proposer — the fastest weekly object the Department publishes (five days after its week, against the insured
rate's twelve). Refused in earlier passes at the old conjunction (April 1979, April 2002, June 2023); retested at v2.9's much tighter one.
Four-week mean a given percentage above its 52-week minimum, confirmed like the 0.45 branch (vacancy or hours pair). Both vintages."""
from mini import *
from legu_min import s_cur, spl
exec(open('fast44.py').read().split('P("\\nbaseline v2.9')[0].replace("out=open('fast44.out','w')","out=open('fast45.out','w')"))
ic=pd.read_csv(W+'/archive/data/fred/ICSA.csv') if os.path.exists(W+'/archive/data/fred/ICSA.csv') else None
if ic is None:
    import glob
    cand=glob.glob(W+'/**/ICSA.csv',recursive=True); P("ICSA candidates:",cand[:4]); ic=pd.read_csv(cand[0])
ic.columns=['d','v']; ic['d']=pd.to_datetime(ic['d']); IC=ic.set_index('d')['v'].astype(float).dropna()
d45=pd.read_csv(W.replace('24_bristow_rule_lab/workspace','45_dol_first_prints_2026-09/national_first_prints.csv'),parse_dates=['release_date','ic_week_ended'])
adv=d45.dropna(subset=['ic_week_ended','icsa']).drop_duplicates('ic_week_ended',keep='first').set_index('ic_week_ended')['icsa'].sort_index()
ICfp=pd.concat([IC[IC.index<adv.index.min()],adv]).sort_index()
P("initial claims:",IC.index.min().date(),"->",IC.index.max().date(),"| advance first prints from",adv.index.min().date())
def leg_ic(s,pct,pub=5,look=52,rearm='zero'):
    m4=s.rolling(4).mean(); rel_=(m4/m4.rolling(look,min_periods=look).min().shift(1)-1)*100
    c=[]; armed=True
    for t,v in rel_.dropna().items():
        if armed and v>=pct: c.append((t+pd.Timedelta(days=pub),pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=0: armed=True
    return c
def go8(nm,pct,vk=4,vb=4,vl=0.20,starts=29):
    G=vgap(vk,vb); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=vl,pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,0.45,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    F25=[x for x in leg_gap_mx2(gm,0.25,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    Hc,MX=mkpair3(starts,4,3,18); Hh=mkhours(2.0,1.20)
    def hubv(sl):
        calls=[]; armed=True
        for m,v in g.items():
            if m<pd.Timestamp('1948-06-01'): continue
            if armed and v>=sl:
                w=G[(G.index>=m-pd.DateOffset(months=6))&(G.index<=m)]; hit=w[w>=vl]
                if len(hit):
                    kk=hit.index[0]; sp=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
                    calls.append((max(sp,pubs[kk]),m-pd.DateOffset(months=3),'hub')); armed=False
            elif not armed and v<sl: armed=True
        return calls
    res=[]
    for s,ics in [(s_cur,IC),(spl,ICfp)]:
        U=confirm_w(leg_gapL(s,0.45,52,rearm='zero')+F45,[Vc,Hh],'month'); L=confirm_w(leg_gapL(s,0.25,52,rearm='window')+F25,[Hc],'month'); X=hubv(0.50)
        legs={'U':[(a,b) for a,b,c in U],'L':[(a,b) for a,b,c in L],'X':[(a,b) for a,b,c in X]}
        if pct is not None:
            I=confirm_w(leg_ic(ics,pct),[Vc,Hh],'month'); legs['I']=[(a,b) for a,b,c in I]
        with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TLH)
        res.append(score13(turns))
    ok=all(len(r['other'])==0 and len(r['lags_p'])==13 for r in res)
    lp=[res[0]['lags_p'].get(i) for i in range(13)]; allv=[x for x in lp if x is not None]
    P(f"{'OK ' if ok else 'BAD'} {nm:34s} {lp} fp2007 {res[1]['lags_p'].get(10)} MEAN {np.mean(allv):.1f} within-31 {sum(1 for x in allv if x<=31)}/13 dates_w1 {sum(1 for e in res[0]['errs_p'].values() if abs(e)<=1)} others {[o[1] for r in res for o in r['other']]}")
    return ok,lp
go8('v2.9 (no initial-claims leg)',None)
for pct in [60,50,45,40,35,30,25,20]: go8(f'initial claims +{pct}%',pct)
P("\n1981 and 2020 diagnostics:")
gp=(s_cur-s_cur.rolling(52,min_periods=52).min().shift(1)).dropna()
P("  insured-rate gap weekly, Jul-Oct 1981:",[(t.strftime('%m-%d'),round(v,2)) for t,v in gp['1981-07':'1981-10'].items()])
P("  insured-rate gap weekly, Feb-Apr 2020:",[(t.strftime('%m-%d'),round(v,2)) for t,v in gp['2020-02':'2020-04'].items()])
m4=(IC.rolling(4).mean()/IC.rolling(4).mean().rolling(52,min_periods=52).min().shift(1)-1)*100
P("  initial-claims 4-week mean above its 52-week minimum, %:",[(t.strftime('%Y-%m-%d'),round(v,0)) for t,v in m4['2020-02':'2020-04'].items()])
out.close()
