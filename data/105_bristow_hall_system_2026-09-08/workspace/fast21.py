"""Window definition audit (after the Bristow line's ALERT on the 19-day Feb 1967 margin): the confirmation window
re-defined on DATA MONTHS ([dated month-6, dated month+4]) and on PUBLICATION DATES, against the calendar slicing
used so far (confirmer label >= proposal publication - 6 months). Every v2 configuration re-run under each."""
from mini import *
from legu_min import s_cur, spl
exec(open('fast17.py').read().split("for vint,s in [('CURRENT FILE',s_cur),('FIRST PRINTS',spl)]:")[0].replace("out=open('fast17.out','w')","out=open('fast21.out','w')"))
PAIRX2=pd.concat([hous_half,rate_half],axis=1).min(axis=1,skipna=False).dropna(); HpX2=dict(name='housing35x',gap=PAIRX2,line=1.0,pub_day=18)
def pubof(cf,t): return (t+pd.Timedelta(days=cf['pub_lag_days'])) if 'pub_lag_days' in cf else (pd.Timestamp(t.year,t.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=cf['pub_day']-1))
def confirm_w(calls,confs,mode='cal',back=6,fwd=4):
    outc=[]
    for p,dd in calls:
        best=None
        for cf in confs:
            ser=cf['gap']
            if mode=='cal': seg=ser[(ser.index>=p-pd.DateOffset(months=back))&(ser.index<=p+pd.DateOffset(months=fwd))]
            elif mode=='month': seg=ser[(ser.index>=dd-pd.DateOffset(months=back))&(ser.index<=dd+pd.DateOffset(months=fwd))]
            elif mode=='pub':
                pubs=pd.Series({t:pubof(cf,t) for t in ser.index}); seg=ser[(pubs>=p-pd.DateOffset(months=back))&(pubs<=p+pd.DateOffset(months=fwd))]
            hit=seg[seg>=cf['line']]
            if len(hit)==0: continue
            t=hit.index[0]; ps=pubof(cf,t)
            if best is None or ps<best[0]: best=(ps,cf['name'],t)
        if best: outc.append((max(p,best[0]),dd,best[1]+'@'+best[2].strftime('%Y-%m')))
    return outc
def run3(nm,legs,TL=TLC):
    pk={k:[(p,dd) for p,dd,_ in v] for k,v in legs.items()}
    with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(pk,TL)
    r=score13(turns); lp=[r['lags_p'].get(i) for i in range(13)]; v73=[r['lags_p'][i] for i in range(5,13) if i in r['lags_p']]; lt=[r['lags_t'].get(i) for i in range(13)]; tv=[l for l in lt if l is not None]
    P(f"\n{nm}\n   onsets {[('-' if l is None else l) for l in lp]} other {[(d,lg) for _,d,lg in r['other']]} | 1973 on median {np.median(v73):.1f} mean {np.mean(v73):.1f} | dates exact {sum(1 for e in r['errs_p'].values() if e==0)} w1 {sum(1 for e in r['errs_p'].values() if abs(e)<=1)} | troughs median {np.median(tv):.0f} exact {sum(1 for e in r['errs_t'].values() if e==0)}")
    cond={(p,dd):c for vv in legs.values() for p,dd,c in vv}
    P("      "+" | ".join(f"{PK[i]:%Y-%m}:{r['opens'][i]['published']:%Y-%m-%d} {r['opens'][i]['leg']} d{r['opens'][i]['date']:%Y-%m} ({cond.get((r['opens'][i]['published'],r['opens'][i]['date']),'?')})" for i in range(13) if i in r['opens']))
    if r['other']:
        for t in r['turns']:
            if t['kind']=='peak' and t['published'].strftime('%Y-%m-%d') in [d for d,_,_ in r['other']]: P(f"      OTHER {t['published']:%Y-%m-%d} {t['leg']} dated {t['date']:%Y-%m} ({cond.get((t['published'],t['date']),'?')})")
    return r
def inw(dd): return any(p-pd.DateOffset(months=6)<=dd<=t for p,t in zip(PK,TR))
def wmax_m(ser,dd,back=6,fwd=4): seg=ser[(ser.index>=dd-pd.DateOffset(months=back))&(ser.index<=dd+pd.DateOffset(months=fwd))]; return (seg.max(),seg.idxmax().strftime('%Y-%m')) if len(seg) else (float('nan'),'')
FHz=[x for x in leg_gap_mx(gm,0.45,rearm='window') if x[1]<pd.Timestamp('1971-01-01')]
P("pair (exact tenths, both halves) months at line 1966-1967:",[m.strftime('%Y-%m') for m,v in PAIRX2['1966':'1967'].items() if v>=1.0])
P("FH 0.45 proposals (window re-arm) 1966-68:",[(p.strftime('%Y-%m-%d'),dd.strftime('%Y-%m')) for p,dd in FHz if pd.Timestamp('1966-01-01')<=dd<=pd.Timestamp('1968-12-01')])
for mode in ['cal','month','pub']:
    P(f"\n######## WINDOW MODE: {mode} ########")
    for vint,s in [('CURRENT FILE',s_cur),('FIRST PRINTS',spl)]:
        P(f"\n==== {vint} ====")
        for lab_,Vc,sl in [('a-priori (vac .36, Sahm .50)',V36,0.50),('construction-grade (vac .30, Sahm .43)',V30,0.43)]:
            X=hub(sl,vr,Vc['line'])
            U=confirm_w(leg_gapx(s,0.45,rearm='zero')+FHz,[Vc,HpX2,Pp],mode); L=confirm_w(leg_gapx(s,0.25,rearm='window'),[HpX2],mode)
            run3(f"v2 {lab_}: U45{{V|H|P}} + U25{{H}} + hub",{'U':U,'L':L,'X':X})
            U2=confirm_w(leg_gapx(s,0.45,rearm='zero')+FHz,[Vc,Pp],mode)
            run3(f"v2 {lab_}: U45{{V|P}} (no housing on the 0.45 branch) + U25{{H}} + hub",{'U':U2,'L':L,'X':X})
        if mode=='month':
            ql=[(p,dd) for p,dd in leg_gapx(s,0.25,rearm='window') if not inw(dd)]
            P(f"   [month windows] U25 quiet proposals {len(ql)}; housing pair maxima >=0.5: {[(dd.strftime('%Y-%m'),round(wmax_m(PAIRX2,dd)[0],2),wmax_m(PAIRX2,dd)[1]) for p,dd in ql if wmax_m(PAIRX2,dd)[0]>=0.5]}")
            qu=[(p,dd) for p,dd in leg_gapx(s,0.45,rearm='zero') if not inw(dd)]; P(f"   [month windows] U45 quiet proposals {len(qu)}")
    if mode=='month':
        qf=[(p,dd) for p,dd in FHz if not inw(dd)]
        P("   [month windows] FH45 quiet proposals (vacancy, housing pair, hours pair maxima):",[(dd.strftime('%Y-%m'),wmax_m(vr,dd),wmax_m(PAIRX2,dd),wmax_m(P1,dd)) for p,dd in qf])
out.close()
