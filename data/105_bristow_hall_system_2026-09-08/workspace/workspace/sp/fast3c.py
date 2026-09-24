def leg_Kb(pct,look=52):
    s=ICfp.dropna(); low=s.rolling(look,min_periods=look).min().shift(1); med=s.rolling(4).mean().rolling(MED_W,min_periods=156).median().shift(1)
    base=np.maximum(low,ALPHA*med); rel_=((s/base-1)*100).dropna(); c=[]; armed=True
    for t,v in rel_.items():
        if armed and v>=pct: c.append((rel_ic(t),pd.Timestamp(t.year,t.month,1))); armed=False
        elif not armed and v<=0: armed=True
    return c,rel_
ks,relK=leg_Kb(35)
out=[(d.date().isoformat(),round(float(crash[crash.index<=d].iloc[-1]),1)) for d,m in ks if d.year>=1962 and not any(pk-pd.DateOffset(months=6)<=m<=tr+pd.DateOffset(months=3) for pk,tr in zip(PK,TR))]
print('K 35 on the floored base, outside recessions (day, S&P fall):',out)
print('2020-03-14 week on the floored base: %.1f'%relK[pd.Timestamp('2020-03-14')])
leg_K=lambda pct,look=52: leg_Kb(pct,look)[0]
r,t,Kc=build_K(p0,35,15); report("K 35 (floored base) + crash 15",r,t); print('   fires:',[(d.date().isoformat(),m.strftime('%Y-%m')) for d,m in Kc if d.year>=1962])
