"""ITEMS 3-4: legs U (insured unemployment rate) and B (national weekly claims conjunct) on the Department's ADVANCE figures as
first published (collection 45, Nov 2002 on; the current file before), inside the full route."""
exec(open('dominance.py').read().split('rows=[]')[0])
N=pd.read_csv(os.path.expanduser("~/mnt/")+'Onset Detector Data/45_dol_first_prints_2026-09/national_first_prints.csv',parse_dates=['release_date','ic_week_ended','iu_week_ended'])
# ---- leg U on first prints: IURSA current before 2002-10, the advance s.a. rate after
iur_fp=N.set_index('iu_week_ended')['iur_sa'].dropna(); iur_fp=iur_fp[~iur_fp.index.duplicated()].sort_index()
_i=pd.read_csv(shim.W+'/archive/data/fred/IURSA.csv'); _i.columns=['d','v']; _i['d']=pd.to_datetime(_i['d']); s_cur=_i.set_index('d')['v'].astype(float).dropna()
spl=s_cur.copy(); common=iur_fp.index.intersection(spl.index); spl.loc[common]=iur_fp.loc[common]
extra=iur_fp.index.difference(spl.index); print('IUR first prints matched to the current index:',len(common),'unmatched',len(extra))
def leg_U_fp(series,line=0.50,look=52,pub=5):
    gap=series-series.rolling(look,min_periods=look).min().shift(1); c=[]; armed=True
    for t,v in gap.dropna().items():
        if armed and v>=line: c.append((t+pd.Timedelta(days=pub),pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=0.0: armed=True
    return c
U_cur=leg_U_fp(s_cur); U_fp=leg_U_fp(spl)
print('leg U calls 2002 on, current:',[(str(p.date()),str(d.date())[:7]) for p,d in U_cur if p>=pd.Timestamp('2002-10-01')])
print('leg U calls 2002 on, first prints:',[(str(p.date()),str(d.date())[:7]) for p,d in U_fp if p>=pd.Timestamp('2002-10-01')])
# ---- leg B on first prints: unadjusted initial claims and insured unemployment, advance, vs the current file a year earlier
V=G['U'].V if hasattr(G['U'],'V') else None
import importlib, sys as _s
Vm=_s.modules.get('v8_legs') or importlib.import_module('v8_legs')
D=Vm.D; ic=D['ic_nsa'].dropna(); cc=D['cc_nsa'].dropna()
icf=N.set_index('ic_week_ended')['icnsa'].dropna(); ccf=N.set_index('iu_week_ended')['iunsa'].dropna()
icf=icf[~icf.index.duplicated()]; ccf=ccf[~ccf.index.duplicated()]
ic2=ic.copy(); m=ic2.index.intersection(icf.index); ic2.loc[m]=icf.loc[m]; cc2=cc.copy(); m2=cc2.index.intersection(ccf.index); cc2.loc[m2]=ccf.loc[m2]
print('B first prints matched: ic',len(m),'cc',len(m2))
def legB(icx,ccx,th=0.20):
    c=B.claims_conjunct(icx,ccx); return [(p,None) for p in B.conjunct_peak_calls(c,line=th,quiet_weeks=26,publication_days=7) if p>=pd.Timestamp('1969-01-08')]
Bc=legB(ic,cc); Bf=legB(ic2,cc2)
print('leg B calls 2002 on, current:',[str(p.date()) for p,_ in Bc if p>=pd.Timestamp('2002-10-01')]); print('leg B calls 2002 on, first prints:',[str(p.date()) for p,_ in Bf if p>=pd.Timestamp('2002-10-01')])
# ---- the route with U and B on first prints (and C on first prints from route_firstprint.py)
Cfp=[(pd.Timestamp('2001-04-14'),pd.Timestamp('2001-03-01')),(pd.Timestamp('2008-06-07'),pd.Timestamp('2008-05-01')),(pd.Timestamp('2020-04-04'),pd.Timestamp('2020-03-01')),(pd.Timestamp('2023-08-19'),pd.Timestamp('2023-08-01'))]
Bw=[(p,pd.Timestamp((p-pd.Timedelta(days=7)).year,(p-pd.Timedelta(days=7)).month,1)) for p,_ in Bf]
pl=dict(PLU); pl['U']=U_fp; pl['B']=Bw; pl['C']=[c for c in PLU['C'] if c[0]<pd.Timestamp('2002-11-01')]+[c for c in Cfp if c[0]>=pd.Timestamp('2002-11-01')]
for nm,P_ in [('current file',PLU),('U, B, C on first prints',pl)]:
    with contextlib.redirect_stdout(io.StringIO()):
        t=B.american_chronology({q:P_[q] for q in PK5},{q:TLG[q] for q in TR3},sahm=g,line=0.5,second=[CONF['V'],CONF['H'],CONF['P']],horizon_months=4,back_months=6)
    on=[(o['published'],o['date'],o['leg'],o.get('condition')) for o in t if o['kind']=='peak' and o['published']>=pd.Timestamp('1948-06-01')]
    lags={}; other=[]; info={}
    for pub,d,l,c in on:
        hit=None
        for i,(p,q) in enumerate(zip(PK,TR)):
            if p-pd.DateOffset(months=6)<=d<=q: hit=i; break
        if hit is None: other.append(d)
        elif hit not in lags: lags[hit]=(pub-me(PK[hit])).days; info[hit]=(l,c,str(pub.date()))
    print(f"\n{nm}: {len(lags)}/12, median {np.median(list(lags.values())):.0f}, worst {max(lags.values())}, other {[str(x.date())[:7] for x in other]}"); print('  lags',[lags.get(i) for i in range(12)]); print('  2007',info.get(10),' 2020',info.get(11))
