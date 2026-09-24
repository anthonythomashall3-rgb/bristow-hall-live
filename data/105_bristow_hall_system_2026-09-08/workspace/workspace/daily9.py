"""ANTHONY'S VINTAGE RULE APPLIED TO THE PRE-1971 BRANCH: use what was actually known at the time. Collection 59 holds
the Department's own national weekly first prints, 1945-1983 — initial claims, insured unemployment, and a weekly
insured RATE seasonally adjusted in real time (national_iur_realtime_sa_first_prints_1948_1983.csv). The tool has been
running the Fieldhouse monthly reconstruction before 1971, published the tenth of the following month; that is the
binding side at 1953 (+71) and 1957 (+40). Here the first-print weekly rate replaces it, published twelve days after
its week, and the national first-print initial claims are read year-over-year (no seasonal adjustment, none existed)."""
from mini import *
from legu_min import s_cur, spl
exec(open('daily1.py').read().split('P("\\nbaseline v3.0")')[0].replace("out=open('daily1.out','w')","out=open('daily9.out','w')"))
C25=os.path.join(os.environ['HOME'],'mnt','Onset Detector Data','25_fred_daily_weekly')
D59=W.replace('24_bristow_rule_lab/workspace','59_dol_weekly_state_claims_1945-1983_2026-09')
def L25(nm):
    for d in ['fred_daily','fred_weekly','fred_biweekly']:
        p=os.path.join(C25,d,nm+'.csv')
        if os.path.exists(p):
            x=pd.read_csv(p).iloc[:,:2]; x.columns=['d','v']; x['d']=pd.to_datetime(x['d'],errors='coerce')
            s=pd.to_numeric(x.set_index('d')['v'],errors='coerce').dropna(); return s[s.index.notna()]
CS=L25('NFCICREDIT'); CRED=dict(name='credit12',gap=(CS-CS.rolling(12).min()).dropna(),line=1.25,pub_lag_days=1)
RT=pd.read_csv(os.path.join(D59,'national_iur_realtime_sa_first_prints_1948_1983.csv'),index_col=0,parse_dates=True).iloc[:,0].dropna()
P("first-print weekly insured rate, real-time SA:",RT.index.min().date(),"->",RT.index.max().date(),len(RT),"weeks")
NP=pd.read_csv(os.path.join(D59,'national_weekly_first_prints_1945_1983.csv'),parse_dates=['week']).set_index('week').sort_index()
ICp=NP['ic'].dropna(); P("national weekly initial claims first prints:",ICp.index.min().date(),"->",ICp.index.max().date(),len(ICp),"weeks")
icy=(ICp.rolling(4).mean()/ICp.rolling(4).mean().shift(52)-1)*100; icy=icy.dropna()
def leg_rt(s,pct,look=52,pub=12,rearm='zero',stop='1971-01-01'):
    m=s.rolling(look,min_periods=look).min().shift(1); rel_=s-m; c=[]; armed=True
    for t,v in rel_.dropna().items():
        if armed and v>=pct: c.append((t+pd.Timedelta(days=pub),pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and (v<=0 if rearm=='zero' else v<pct): armed=True
    return [x for x in c if x[1]<pd.Timestamp(stop)]
def leg_icy(pct,pub=12,stop='1971-01-01'):
    c=[]; armed=True
    for t,v in icy.items():
        if armed and v>=pct: c.append((t+pd.Timedelta(days=pub),pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=0: armed=True
    return [x for x in c if x[1]<pd.Timestamp(stop)]
def go(nm,extra,F45x=None,F25x=None,Ix=None,hubline=0.50,pct=50,vk=4,vb=4,vl=0.20,starts=29):
    G=vgap(vk,vb); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=vl,pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,0.45,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')] if F45x is None else F45x
    F25=[x for x in leg_gap_mx2(gm,0.25,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')] if F25x is None else F25x
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
    C1=[Vc,Hh]+extra; C2=[Hc]+extra; res=[]
    for s,ics in [(s_cur,IC),(spl,ICfp)]:
        U=confirm_w(leg_gapL(s,0.45,52,rearm='zero')+F45,C1,'month'); L=confirm_w(leg_gapL(s,0.25,52,rearm='window')+F25,C2,'month'); X=hubv(hubline)
        I=confirm_w(leg_ic(ics,pct)+(Ix or []),C1,'month')
        legs={'U':[(a,b) for a,b,c in U],'L':[(a,b) for a,b,c in L],'X':[(a,b) for a,b,c in X],'I':[(a,b) for a,b,c in I]}
        with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TLH)
        res.append(score13(turns))
    ok=all(len(r['other'])==0 and len(r['lags_p'])==13 for r in res)
    lp=[res[0]['lags_p'].get(i) for i in range(13)]; ep=[res[0]['errs_p'].get(i) for i in range(13)]
    av=[x for x in lp if x is not None]
    P(f"{'OK ' if ok else 'BAD'} {nm:44s} {lp} MEAN {np.mean(av):.1f} in31 {sum(1 for x in av if x<=31)}/13 ERR {ep} others {[o[1] for r in res for o in r['other']][:5]}")
    return ok,np.mean(av)
P("\n=== baseline v3.1 ==="); go('v3.1',[CRED])
P("\n=== the first-print weekly rate REPLACING the Fieldhouse monthly, both branches ===")
for l45,l25 in [(0.45,0.25),(0.50,0.30),(0.60,0.35),(0.75,0.45),(1.00,0.60)]:
    go(f'rt first prints {l45}/{l25}',[CRED],F45x=leg_rt(RT,l45),F25x=leg_rt(RT,l25))
P("\n=== the first-print weekly rate ADDED to the Fieldhouse legs ===")
for l45,l25 in [(0.45,0.25),(0.60,0.35),(0.75,0.45),(1.00,0.60),(1.25,0.75)]:
    F45=[x for x in leg_gap_mx2(gm,0.45,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    F25=[x for x in leg_gap_mx2(gm,0.25,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    go(f'rt added {l45}/{l25}',[CRED],F45x=F45+leg_rt(RT,l45),F25x=F25+leg_rt(RT,l25))
P("\n=== national initial claims first prints, year-over-year, as a pre-1971 proposer ===")
for ln in [20,30,40,50,60,75]: go(f'IC yoy >= {ln}%',[CRED],Ix=leg_icy(ln))
out.close()
