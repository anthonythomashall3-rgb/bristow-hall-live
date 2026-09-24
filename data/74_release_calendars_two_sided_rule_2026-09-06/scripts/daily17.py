"""THREE MORE DOORS, ALL ON DATA ALREADY HELD.
(a) 1960 and 1969 are confirmer-bound: housing starts ALONE at a deep line, and BUILDING PERMITS (which print in the
    same release as starts but turn earlier), tested as demand-side confirmers.
(b) 1953, 1957 and 1981 are proposal-bound: the Department's weekly STATE initial claims (collection 59, 1945-1983,
    and ETA 5159 spliced to 2026) read as BREADTH - the share of states whose claims stand above their own year-earlier
    level - which needs no seasonal adjustment and no national denominator, as an extra proposer.
(c) the same collection's national weekly INITIAL claims first prints, adjusted in real time, as a proposer."""
exec(open('daily16.py').read().split('G=obj(CPB,13,6)')[0].replace("out=open('daily16.out','w')","out=open('daily17.out','w')"))
G=obj(CPB,13,6); SPR=dict(name='cpb',gap=G,line=1.20,pub_lag_days=1)
D59=W.replace('24_bristow_rule_lab/workspace','59_dol_weekly_state_claims_1945-1983_2026-09')
P("=== v3.2 baseline and v3.2 + the paper spread at 1.20 ===")
go9e('v3.2',[CRED],rt=True); go9e('v3.2 + paper spread 1.20',[CRED,SPR],rt=True)
P("\n=== (a) housing starts alone, and building permits, as demand confirmers ===")
def mkstarts(line_lp,k=3):
    m=lh.rolling(k).mean(); gp=(lh.rolling(12).max()-m).dropna()
    pubs=pd.Series({mm:(relH[mm] if mm in relH.index else pd.Timestamp(mm.year,mm.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=16)) for mm in gp.index})
    return dict(name=f'starts{line_lp}',gap=gp*100,line=line_lp,pubs=pubs)
for ln in [30,35,40,45,50,55]:
    go9e(f'  starts alone >= {ln} log points',[CRED,SPR,mkstarts(ln)],rt=True)
PM=L25('PERMIT')
if PM is not None:
    P(f"   PERMIT: {PM.index.min().date()} -> {PM.index.max().date()}")
    lp_=np.log(PM.dropna()); mp=lp_.rolling(3).mean(); gpp=(lp_.rolling(12).max()-mp).dropna()*100
    pubs=pd.Series({mm:(relH[mm] if mm in relH.index else pd.Timestamp(mm.year,mm.month,1)+pd.DateOffset(months=1)+pd.Timedelta(days=16)) for mm in gpp.index})
    for ln in [25,30,35,40,45]:
        go9e(f'  permits alone >= {ln} log points',[CRED,SPR,dict(name='perm',gap=gpp,line=ln,pubs=pubs)],rt=True)
P("\n=== (b) state claims BREADTH as an extra proposer ===")
SW=pd.read_csv(os.path.join(D59,'ic_weekly_state_1945_1983_wide.csv'),index_col=0,parse_dates=True)
SW=SW.drop(columns=[c for c in SW.columns if c in ('PR','VI')])
P(f"   weekly state initial claims: {SW.index.min().date()} -> {SW.index.max().date()}, {SW.shape[1]} jurisdictions")
r4=SW.rolling(4,min_periods=3).mean()
yy=(r4/r4.shift(52)-1)
cov=yy.notna().sum(axis=1)
br=((yy>0.20).sum(axis=1)/cov.replace(0,np.nan))*100
br=br[cov>=25].dropna()
P(f"   breadth (share of states 20 per cent above their own year-earlier four-week mean), {len(br)} weeks with 25+ states reporting")
def leg_br(pct,pub=14,stop='1971-01-01'):
    c=[]; armed=True
    for t,v in br.items():
        if armed and v>=pct: c.append((t+pd.Timedelta(days=pub),pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=pct*0.5: armed=True
    return [x for x in c if x[1]<pd.Timestamp(stop)]
for pct in [50,60,70,80]:
    cl=leg_br(pct); P(f"   breadth >= {pct}%: {len(cl)} proposals before 1971 — {[d.strftime('%Y-%m') for _,d in cl]}")
def go_br(nm,pct,stop='1971-01-01',extra=None):
    return go9e(nm,[CRED,SPR]+(extra or []),rt=True,brlegs=leg_br(pct,stop=stop))
P("\n=== (c) national weekly initial claims first prints, real-time adjusted, as a proposer ===")
NP=pd.read_csv(os.path.join(D59,'national_weekly_first_prints_1945_1983.csv'),parse_dates=['week']).set_index('week').sort_index()
ICp=NP['ic'].dropna(); lgc=np.log(ICp)
tr=lgc.rolling(53,center=True,min_periods=40).mean(); dev=(lgc-tr).dropna()
fac={}
for t in lgc.index:
    yr=t.year; wk=t.isocalendar()[1]
    hist=dev[(dev.index<pd.Timestamp(yr,1,1))&(dev.index>=pd.Timestamp(yr-7,1,1))]
    hw=hist[[x.isocalendar()[1]==wk for x in hist.index]]
    fac[t]=float(hw.median()) if len(hw)>=3 else 0.0
sa=np.exp(lgc-pd.Series(fac))
P(f"   real-time adjusted first-print initial claims: {sa.index.min().date()} -> {sa.index.max().date()}, {len(sa)} weeks")
out.close()
