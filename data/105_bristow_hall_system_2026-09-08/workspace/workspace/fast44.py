"""The pre-1971 branches moved onto the WEEKLY insured rate built in preweek.py (twelve-day clock) instead of the Fieldhouse monthly series
(tenth of the following month). The Fieldhouse series still carries 1948, which is before the weekly build starts. Zero other calls on both
vintages and on the pre-1971 era required."""
from mini import *
from legu_min import s_cur, spl
exec(open('sweep11.py').read().split('P("\\nbaseline v2.8")')[0].replace("out=open('sweep11.out','w')","out=open('fast44.out','w')"))
wk=pd.read_csv('cache/weekly_iur_prewar.csv',index_col=0,parse_dates=True).iloc[:,0].dropna()
P("weekly pre-1971 insured rate:",wk.index.min().date(),"->",wk.index.max().date(),len(wk))
def leg_w(line,pub=12,rearm='zero',look=52,end='1971-01-01'):
    s=wk[wk.index<pd.Timestamp(end)]
    gap=(s-s.rolling(look,min_periods=look).min().shift(1)).dropna(); c=[]; armed=True; last=None
    for t,v in gap.items():
        if armed and v>=line: c.append((t+pd.Timedelta(days=pub),pd.Timestamp(t.year,t.month,1))); armed=False; last=t
        elif not armed:
            if rearm=='zero' and v<=0: armed=True
            elif rearm=='window' and v<line and t>=last+pd.DateOffset(months=4): armed=True
    return c
P("weekly 0.45 proposals before 1971:",[(p.strftime('%Y-%m-%d'),d.strftime('%Y-%m')) for p,d in leg_w(0.45)])
P("weekly 0.25 proposals before 1971:",[(p.strftime('%Y-%m-%d'),d.strftime('%Y-%m')) for p,d in leg_w(0.25,rearm='window')])
def go7(nm,vk=4,vb=4,vl=0.20,starts=29,use_weekly=True,w45=0.45,w25=0.25):
    G=vgap(vk,vb); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=vl,pubs=pubs)
    FHm45=[x for x in leg_gap_mx2(gm,0.45,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    FHm25=[x for x in leg_gap_mx2(gm,0.25,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    if use_weekly:
        F45=[x for x in FHm45 if x[1]<wk.index.min()]+leg_w(w45); F25=[x for x in FHm25 if x[1]<wk.index.min()]+leg_w(w25,rearm='window')
    else: F45,F25=FHm45,FHm25
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
    for s in (s_cur,spl):
        U=confirm_w(leg_gapL(s,0.45,52,rearm='zero')+F45,[Vc,Hh],'month'); L=confirm_w(leg_gapL(s,0.25,52,rearm='window')+F25,[Hc],'month'); X=hubv(0.50)
        pk={'U':[(a,b) for a,b,c in U],'L':[(a,b) for a,b,c in L],'X':[(a,b) for a,b,c in X]}
        with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(pk,TLH)
        res.append(score13(turns))
    ok=all(len(r['other'])==0 and len(r['lags_p'])==13 for r in res)
    lp=[res[0]['lags_p'].get(i) for i in range(13)]; allv=[x for x in lp if x is not None]
    P(f"{'OK ' if ok else 'BAD'} {nm:40s} {lp} fp2007 {res[1]['lags_p'].get(10)} MEAN {np.mean(allv):.1f} within-31 {sum(1 for x in allv if x<=31)}/13 dates_w1 {sum(1 for e in res[0]['errs_p'].values() if abs(e)<=1)} others {[o[1] for r in res for o in r['other']]}")
    return ok,lp
P("\nbaseline v2.9 (Fieldhouse monthly before 1971)"); go7('v2.9',use_weekly=False)
P("\nwith the weekly pre-1971 rate:")
for a in [0.45,0.50,0.55,0.60,0.70]:
    for b in [0.25,0.30,0.35]:
        go7(f'weekly 0.45-line {a}, low-line {b}',w45=a,w25=b)
out.close()
