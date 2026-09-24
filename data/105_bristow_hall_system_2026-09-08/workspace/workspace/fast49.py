"""v3.3 RECORD SCRIPT — the money-market spread admitted, the 2024 dating relaxed as Anthony asked, and a scoring
defect fixed. Three things happened here:
 (1) A CLASS OF OBJECT THE SWEEP COULD NOT SEE. A spread between two series is not a series on the shelf, so the
     15,128-file sweep never tested one. Credit stress IS a spread, and the private money-market rates run weekly from
     1954-56 — fifteen years before the Chicago Fed's credit subindex begins. The one-month commercial paper rate over
     the three-month Treasury bill, read as a thirteen-week mean standing above its lowest value of the previous nine
     months, with the line set at 1.5x the highest reading in any quiet proposal window on the whole record.
 (2) THE 2024 DATING. The hub on 0.43 rather than Sahm's published 0.50 calls 2024 on 5 July instead of 2 August —
     66 days instead of 94 — and dates it March rather than April.
 (3) A SCORING DEFECT (Rule Zero). score13 ignores every peak turn published before 1 June 1948. The shipped rule
     makes no such call, but candidates tested today did, and were scored as if silent. Everything below is scored
     with those calls counted."""
from mini import *
from legu_min import s_cur, spl
exec(open('daily4.py').read().split("qq=sorted(")[0].replace("out=open('daily4.out','w')","out=open('fast49.out','w')"))
CRD=dict(name='credit12',gap=G12,line=1.25,pub_lag_days=1)
C25=os.path.join(os.environ['HOME'],'mnt','Onset Detector Data','25_fred_daily_weekly')
D59=W.replace('24_bristow_rule_lab/workspace','59_dol_weekly_state_claims_1945-1983_2026-09')
def L25(nm):
    for d in ['fred_daily','fred_weekly','fred_biweekly']:
        p=os.path.join(C25,d,nm+'.csv')
        if os.path.exists(p):
            x=pd.read_csv(p).iloc[:,:2]; x.columns=['d','v']; x['d']=pd.to_datetime(x['d'],errors='coerce')
            s=pd.to_numeric(x.set_index('d')['v'],errors='coerce').dropna(); return s[s.index.notna()]
aa=L25('H0RIFSPPFM01NWF'); bb=L25('WTB3MS'); idx=aa.index.union(bb.index)
CPB=(aa.reindex(idx).ffill()-bb.reindex(idx).ffill()).dropna(); CPB=CPB[CPB.index>=max(aa.index.min(),bb.index.min())]
SM,WIN=13,39
Sm=CPB.rolling(SM).mean().dropna(); GSP=(Sm-Sm.rolling(WIN).min()).dropna()
RT=pd.read_csv(os.path.join(D59,'national_iur_realtime_sa_first_prints_1948_1983.csv'),index_col=0,parse_dates=True).iloc[:,0].dropna()
def leg_rt(s,pct,look=52,pub=12,stop='1971-01-01'):
    m=s.rolling(look,min_periods=look).min().shift(1); c=[]; armed=True
    for t,v in (s-m).dropna().items():
        if armed and v>=pct: c.append((t+pd.Timedelta(days=pub),pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=0: armed=True
    return [x for x in c if x[1]<pd.Timestamp(stop)]
def inw_(dd): return any(p_-pd.DateOffset(months=6)<=dd<=t for p_,t in zip(PK,TR))
QP=sorted({dd for p_,dd in leg_gapL(s_cur,0.25,52,rearm='window') if not inw_(dd)}|{dd for p_,dd in leg_gapL(spl,0.25,52,rearm='window') if not inw_(dd)}
          |{dd for p_,dd in leg_gap_mx2(gm,0.25,boundary='ge') if dd<pd.Timestamp('1971-01-01') and not inw_(dd)}
          |{dd for p_,dd in leg_gap_mx2(gm,0.45,boundary='ge') if dd<pd.Timestamp('1971-01-01') and not inw_(dd)}
          |{dd for p_,dd in leg_gapL(s_cur,0.45,52,rearm='zero') if not inw_(dd)}|{dd for p_,dd in leg_ic(IC,50) if not inw_(dd)})
def wseg(Gx,dd):
    lo=dd-pd.DateOffset(months=6); hi=dd+pd.DateOffset(months=4)+pd.offsets.MonthEnd(0); return Gx[(Gx.index>=lo)&(Gx.index<=hi)]
QMAX=max(float(wseg(GSP,dd).max()) for dd in QP if len(wseg(GSP,dd)))
LINE=round(QMAX*1.5,3)
SPR=dict(name='paper spread',gap=GSP,line=LINE,pub_lag_days=1)
def full(nm,extra,rt=True,hubline=0.50,xleg=None):
    G=vgap(4,4); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=0.20,pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,0.45,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    F25=[x for x in leg_gap_mx2(gm,0.25,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    if rt: F45=F45+leg_rt(RT,0.45); F25=F25+leg_rt(RT,0.25)
    if xleg: F45=F45+xleg; F25=F25+xleg
    Hc,MX=mkpair3(29,4,3,18); Hh=mkhours(2.0,1.20)
    def hubv(sl):
        calls=[]; armed=True
        for m,v in g.items():
            if m<pd.Timestamp('1948-06-01'): continue
            if armed and v>=sl:
                w=G[(G.index>=m-pd.DateOffset(months=6))&(G.index<=m)]; hit=w[w>=0.20]
                if len(hit):
                    kk=hit.index[0]; sp=rel.get(m,pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=4))
                    calls.append((max(sp,pubs[kk]),m-pd.DateOffset(months=3),'hub')); armed=False
            elif not armed and v<sl: armed=True
        return calls
    C1=[Vc,Hh]+extra; C2=[Hc]+extra
    for tag,s,ics in [('CURRENT FILE',s_cur,IC),('FIRST PRINTS',spl,ICfp)]:
        U=confirm_w(leg_gapL(s,0.45,52,rearm='zero')+F45,C1,'month'); L=confirm_w(leg_gapL(s,0.25,52,rearm='window')+F25,C2,'month'); X=hubv(hubline); I=confirm_w(leg_ic(ics,50),C1,'month')
        legs={'U':[(a,b) for a,b,c in U],'L':[(a,b) for a,b,c in L],'X':[(a,b) for a,b,c in X],'I':[(a,b) for a,b,c in I]}
        with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TLH)
        r=score13(turns); lp=[r['lags_p'].get(i) for i in range(13)]; lt=[r['lags_t'].get(i) for i in range(13)]
        allv=[x for x in lp if x is not None]; tv=[x for x in lt if x is not None]
        early=[t for t in turns if t['kind']=='peak' and t['published']<pd.Timestamp('1948-06-01')]
        P(f"\n{nm} — {tag}\n   onsets {lp} | all-13 mean {np.mean(allv):.1f} | within the month {sum(1 for x in allv if x<=31)}/13 | detected {len(r['lags_p'])}/13 | OTHER CALLS {[o[1] for o in r['other']]} | calls before June 1948 {[(t['published'].strftime('%Y-%m-%d'),t['date'].strftime('%Y-%m')) for t in early]}")
        P(f"   peak dates {[r['errs_p'].get(i) for i in range(13)]} exact {sum(1 for e in r['errs_p'].values() if e==0)} within one {sum(1 for e in r['errs_p'].values() if abs(e)<=1)} | troughs median {np.median(tv):.0f} exact {sum(1 for e in r['errs_t'].values() if e==0)} early {sum(1 for x in tv if x<0)}")
        if tag=='CURRENT FILE':
            cond={(p,dd):c for v in [U,L,X,I] for p,dd,c in v}
            P("   carried by: "+" | ".join(f"{PK[i]:%Y-%m}:{r['opens'][i]['published']:%Y-%m-%d}{r['opens'][i]['leg']}({cond.get((r['opens'][i]['published'],r['opens'][i]['date']),'hub')})" for i in range(13) if i in r['opens']))
P(f"THE PAPER SPREAD: one-month commercial paper less the three-month Treasury bill, {CPB.index.min().date()} to {CPB.index.max().date()}, weekly, published the next day, never revised.")
P(f"   reading: a {SM}-week mean standing above its lowest value of the previous {WIN} weeks (nine months). LINE = 1.5 x the highest quiet reading = 1.5 x {QMAX:.3f} = {LINE}")
qs=sorted([(float(wseg(GSP,dd).max()),dd.strftime('%Y-%m')) for dd in QP if len(wseg(GSP,dd))],reverse=True)
P(f"   quiet readings, highest first: {[(round(a,2),b) for a,b in qs[:8]]} ({len(qs)} of {len(QP)} quiet windows covered)")
P(f"   recession-window maxima: {[(PK[i].strftime('%Y-%m'),round(float(wseg(GSP,PK[i]).max()),2) if len(wseg(GSP,PK[i])) else None) for i in range(13)]}")
P(f"   2025-26 maximum {float(GSP[GSP.index>=pd.Timestamp('2025-01-01')].max()):.3f}; latest reading {float(GSP.iloc[-1]):.3f} on {GSP.index[-1].date()}")
full('v3.2 (the 6 September record)',[CRD])
full('v3.3 (+ the paper spread)',[CRD,SPR])
full('v3.3r (v3.3 with the hub on 0.43 — ANTHONY\'S 2024 CHOICE)',[CRD,SPR],hubline=0.43)
NP=pd.read_csv(os.path.join(D59,'national_weekly_first_prints_1945_1983.csv'),parse_dates=['week']).set_index('week').sort_index()
lgc=np.log(NP['ic'].dropna()); tr=lgc.rolling(53,center=True,min_periods=40).mean(); dev=(lgc-tr).dropna()
fac={}
for t in lgc.index:
    wk=t.isocalendar()[1]; hist=dev[(dev.index<pd.Timestamp(t.year,1,1))&(dev.index>=pd.Timestamp(t.year-7,1,1))]
    hw=hist[[x.isocalendar()[1]==wk for x in hist.index]]; fac[t]=float(hw.median()) if len(hw)>=3 else 0.0
sa=np.exp(lgc-pd.Series(fac)).dropna()
def leg_icrt(pctv,pub=5,look=78,stop='1971-01-01'):
    m4=sa.rolling(4).mean(); rel_=(m4/m4.rolling(look,min_periods=look).min().shift(1)-1)*100
    c=[]; armed=True
    for t,v in rel_.dropna().items():
        if armed and v>=pctv: c.append((t+pd.Timedelta(days=pub),pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=0: armed=True
    return [x for x in c if x[1]<pd.Timestamp(stop)]
full('v3.3f PRICED (+ first-print initial claims 40 per cent over 78 weeks) — 1957 to 26 days, at two months of 1948 dating',[CRD,SPR],hubline=0.43,xleg=leg_icrt(40))
P("\nTHE LINE IS A RULE, AND IT SURVIVES ITS OWN CAUSAL REPLAY (causal27.py): at every turn from 1960 on, the line the")
P("record BEFORE that turn would have set — 1.5 times the highest quiet reading known by then — gives the identical call")
P("and no other call. Before 1980 the past's line is 1.052 and after it 1.323; both fire in December 2007 and in neither")
P("case does the object fire in a quiet month. The 2007 gain is causal.")
P("\nWHAT WAS REFUSED TODAY, WITH NUMBERS: housing starts alone at any deep line (1961-09, 1976-01, 1978-02, 1984-11);")
P("building permits alone (July 1966 at every line); state-claims breadth from the Department's weekly state file at any")
P("breadth threshold below 90 per cent (June 1950), and inert at 90; the first-print initial-claims proposer over 52 and")
P("65 weeks (a December 1947 call the scorer was hiding); the vacancy object at every other shape in a 5x5x5 grid (none")
P("reaches its line before June 1960); the first-print weekly rate carried past 1971 (a December 1975 call, or the loss")
P("of the 1953 gain at the lines that avoid it).")
out.close()
