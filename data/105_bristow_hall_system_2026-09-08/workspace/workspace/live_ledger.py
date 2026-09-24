"""ITEM 27: the live edge.  Every object of route v8 at its latest reading, and the state of each leg, as of the data in hand."""
exec(open('dominance.py').read().split('rows=[]')[0])
print("ROUTE v8 LIVE LEDGER —", pd.Timestamp.today().date())
print("\nclaims legs — last call (published, dated) and whether an episode is open:")
for q in PK5:
    calls=PLU[q]; last=calls[-1] if calls else None
    print(f"  leg {q}: last call {'' if last is None else f'{last[0]:%Y-%m-%d} dated {last[1]:%Y-%m}'}   ({len(calls)} calls in the file)")
_i=pd.read_csv(shim.W+'/archive/data/fred/IURSA.csv'); _i.columns=['d','v']; _i['d']=pd.to_datetime(_i['d']); iur=_i.set_index('d')['v'].astype(float).dropna()
gapU=iur-iur.rolling(52,min_periods=52).min().shift(1); print(f"  leg U object now: IURSA {iur.iloc[-1]:.1f} ({iur.index[-1].date()}), gap to 52-week min {gapU.iloc[-1]:+.2f} (line 0.50)")
print("\nconfirming objects — latest readings against their lines:")
print(f"  Sahm gap (first prints)        {sahm.dropna().iloc[-1]:+.2f}  ({sahm.dropna().index[-1]:%Y-%m})  line 0.50")
print(f"  vacancy fast form (2,6)        {vac.dropna().iloc[-1]:+.2f}  ({vac.dropna().index[-1]:%Y-%m})  line 0.36")
hp=pair(35); print(f"  housing35 x rate0.20 pair      {hp.dropna().iloc[-1]:+.2f}  ({hp.dropna().index[-1]:%Y-%m})  line 1.00")
print(f"  hours2.0 x nondurable1.20 pair {P1.dropna().iloc[-1]:+.2f}  ({P1.dropna().index[-1]:%Y-%m})  line 1.00")
print("\nlast twelve months of each object:")
tab=pd.concat([sahm.rename('sahm'),vac.rename('vac'),hp.rename('housing_pair'),P1.rename('hours_pair')],axis=1).dropna(how='all').tail(12).round(2)
print(tab.to_string())
with contextlib.redirect_stdout(io.StringIO()):
    t=B.american_chronology({q:PLU[q] for q in PK5},{q:TLG[q] for q in TR3},sahm=g,line=0.5,second=[CONF['V'],CONF['H'],CONF['P']],horizon_months=4,back_months=6)
last=[o for o in t if o['published']>=pd.Timestamp('2023-01-01')]
print("\nthe route's calls since 2023:"); [print(f"  {o['kind']:6} published {o['published']:%Y-%m-%d} by {o['leg']} dated {o['date']:%Y-%m} {o.get('condition','')}") for o in last]
