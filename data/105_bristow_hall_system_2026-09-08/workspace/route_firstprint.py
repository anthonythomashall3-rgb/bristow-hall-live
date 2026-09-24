"""The route with leg C read on FIRST PRINTS (DOL page 8, Nov 2002 on): C's calls replaced by the first-print calls."""
exec(open('dominance.py').read().split('rows=[]')[0])
Cfp=[(pd.Timestamp('2001-04-14'),pd.Timestamp('2001-03-01')),(pd.Timestamp('2008-06-07'),pd.Timestamp('2008-05-01')),(pd.Timestamp('2020-04-04'),pd.Timestamp('2020-03-01')),(pd.Timestamp('2023-08-19'),pd.Timestamp('2023-08-01'))]
print('leg C current-file calls:', [(str(p.date()),str(d.date())[:7]) for p,d in PLU['C'] if p>=pd.Timestamp('2000-01-01')])
for nm,pl in [('current file',PLU),('first prints (2002-11 on)',{**PLU,'C':[c for c in PLU['C'] if c[0]<pd.Timestamp('2002-11-01')]+[c for c in Cfp if c[0]>=pd.Timestamp('2002-11-01')]})]:
    with contextlib.redirect_stdout(io.StringIO()):
        t=B.american_chronology({q:pl[q] for q in PK5},{q:TLG[q] for q in TR3},sahm=g,line=0.5,second=[CONF['V'],CONF['H'],CONF['P']],horizon_months=4,back_months=6)
    on=[(o['published'],o['date'],o['leg'],o.get('condition')) for o in t if o['kind']=='peak' and o['published']>=pd.Timestamp('1948-06-01')]
    lags={}; other=[]; info={}
    for pub,d,l,c in on:
        hit=None
        for i,(p,q) in enumerate(zip(PK,TR)):
            if p-pd.DateOffset(months=6)<=d<=q: hit=i; break
        if hit is None: other.append(d)
        elif hit not in lags: lags[hit]=(pub-me(PK[hit])).days; info[hit]=(l,c,str(pub.date()),str(d.date())[:7])
    L=[lags.get(i) for i in range(12)]
    print(f"\n{nm}: called {len(lags)}/12, median {np.median(list(lags.values())):.0f}, worst {max(lags.values())}, other {[str(x.date())[:7] for x in other]}")
    print('  lags', L); print('  2007:',info.get(10),' 2020:',info.get(11))
