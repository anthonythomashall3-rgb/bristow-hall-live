"""THE PRE-1971 PROPOSAL, REBUILT WITHOUT A SEASONAL ADJUSTMENT. 1953 (+71), 1957 (+40) and 1960 (+91) are bound by the
monthly Fieldhouse insured rate, published the tenth of the following month. The Department's own WEEKLY state
continued-claims counts (collection 59, 1945-1983) were published about a fortnight after their week and were known at
the time. §5t built a weekly INSURED RATE from them and it was slower, because its real-time seasonal factors move the
crossing later. This tries the object that needs NO seasonal adjustment and no denominator: continued claims against
the SAME WEEK A YEAR EARLIER. Also tested: the housing x rate pair as a confirmer of the 0.45 branch (housing starts
begin in 1959, so it can reach 1960)."""
from mini import *
from legu_min import s_cur, spl
exec(open('daily1.py').read().split('P("\\nbaseline v3.0")')[0].replace("out=open('daily1.out','w')","out=open('daily8.out','w')"))
C25=os.path.join(os.environ['HOME'],'mnt','Onset Detector Data','25_fred_daily_weekly')
def L25(nm):
    for d in ['fred_daily','fred_weekly','fred_biweekly']:
        p=os.path.join(C25,d,nm+'.csv')
        if os.path.exists(p):
            x=pd.read_csv(p).iloc[:,:2]; x.columns=['d','v']; x['d']=pd.to_datetime(x['d'],errors='coerce')
            s=pd.to_numeric(x.set_index('d')['v'],errors='coerce').dropna(); return s[s.index.notna()]
CS=L25('NFCICREDIT'); CRED=dict(name='credit12',gap=(CS-CS.rolling(12).min()).dropna(),line=1.25,pub_lag_days=1)
CC=pd.read_csv(W.replace('24_bristow_rule_lab/workspace','59_dol_weekly_state_claims_1945-1983_2026-09/weekly_cc_1945_1983.csv'),index_col=0,parse_dates=True)
CC=CC.drop(columns=[c for c in CC.columns if c in ('PR','VI')])
base=CC.loc['1960':'1969'].mean(); share=(CC.notna()*base).sum(axis=1)/base.sum()
raw=(CC.sum(axis=1,skipna=True)/share.replace(0,np.nan))[share>=0.60].dropna()
P("weekly national continued claims (coverage-scaled):",raw.index.min().date(),"->",raw.index.max().date(),len(raw),"weeks")
yoy=(raw/raw.shift(52)-1)*100
yoy=yoy.dropna()
P("year-over-year, per cent: span",yoy.index.min().date(),"->",yoy.index.max().date())
def inw2(dd): return any(p_-pd.DateOffset(months=6)<=dd<=t for p_,t in zip(PK,TR))
for ln in [20,30,40,50,60,75,100]:
    fires=[];armed=True
    for t,v in yoy.items():
        if armed and v>=ln: fires.append(t); armed=False
        elif not armed and v<=0: armed=True
    q=[t.strftime('%Y-%m-%d') for t in fires if not inw2(pd.Timestamp(t.year,t.month,1))]
    P(f"   line {ln:3d}%: {len(fires)} firings, {len(q)} in quiet months {q[:8]}")
def leg_yoy(ln,pub=14):
    calls=[]; armed=True
    for t,v in yoy.items():
        if armed and v>=ln: calls.append((t+pd.Timedelta(days=pub),pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=0: armed=True
    return [c for c in calls if c[1]<pd.Timestamp('1971-01-01')]
def go9y(nm,extra,yline=None,ypub=14,mode='add',hubline=0.50,uconf_house=False,pct=50,vk=4,vb=4,vl=0.20,starts=29):
    G=vgap(vk,vb); pubs=pd.Series({m:(relJ[m] if m in relJ.index else pd.Timestamp(m.year,m.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=29)) for m in G.index})
    Vc=dict(name='vac',gap=G,line=vl,pubs=pubs)
    F45=[x for x in leg_gap_mx2(gm,0.45,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    F25=[x for x in leg_gap_mx2(gm,0.25,boundary='ge') if x[1]<pd.Timestamp('1971-01-01')]
    if yline is not None:
        Y=leg_yoy(yline,ypub)
        if mode=='replace': F45=Y; F25=Y
        else: F45=F45+Y; F25=F25+Y
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
    C1=[Vc,Hh]+([Hc] if uconf_house else [])+extra; C2=[Hc]+extra; res=[]
    for s,ics in [(s_cur,IC),(spl,ICfp)]:
        U=confirm_w(leg_gapL(s,0.45,52,rearm='zero')+F45,C1,'month'); L=confirm_w(leg_gapL(s,0.25,52,rearm='window')+F25,C2,'month'); X=hubv(hubline)
        I=confirm_w(leg_ic(ics,pct),C1,'month')
        legs={'U':[(a,b) for a,b,c in U],'L':[(a,b) for a,b,c in L],'X':[(a,b) for a,b,c in X],'I':[(a,b) for a,b,c in I]}
        with contextlib.redirect_stdout(io.StringIO()): turns=B.american_chronology(legs,TLH)
        res.append(score13(turns))
    ok=all(len(r['other'])==0 and len(r['lags_p'])==13 for r in res)
    lp=[res[0]['lags_p'].get(i) for i in range(13)]; ep=[res[0]['errs_p'].get(i) for i in range(13)]
    av=[x for x in lp if x is not None]
    P(f"{'OK ' if ok else 'BAD'} {nm:38s} {lp} MEAN {np.mean(av):.1f} in31 {sum(1 for x in av if x<=31)}/13 ERR {ep} others {[o[1] for r in res for o in r['other']][:4]}")
    return ok,np.mean(av)
P("\n=== baseline v3.1 ==="); go9y('v3.1',[CRED])
P("\n=== the year-over-year weekly claims object ADDED as a pre-1971 proposal ===")
for ln in [30,40,50,60,75,100]:
    for pub in [14,21]: go9y(f'yoy>={ln}% pub+{pub}d (added)',[CRED],yline=ln,ypub=pub)
P("\n=== the same REPLACING the Fieldhouse pre-1971 legs ===")
for ln in [30,40,50,60,75]: go9y(f'yoy>={ln}% pub+14d (replace)',[CRED],yline=ln,mode='replace')
P("\n=== the housing x rate pair as a SECOND confirmer of the 0.45 branch ===")
go9y('housing pair also confirms U',[CRED],uconf_house=True)
for ln in [40,50,60]: go9y(f'both: yoy>={ln}% + housing confirms U',[CRED],yline=ln,uconf_house=True)
out.close()
