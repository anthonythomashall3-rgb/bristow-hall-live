for pct in (30,35,40):
    ks=[(d,m) for d,m in leg_K(pct) if d.year>=1962]
    inrec=[(d.date().isoformat(),m.strftime('%Y-%m')) for d,m in ks if any(pk-pd.DateOffset(months=6)<=m<=tr+pd.DateOffset(months=3) for pk,tr in zip(PK,TR))]
    out=[(d.date().isoformat(),m.strftime('%Y-%m'),round(float(crash[crash.index<=d].iloc[-1]),1)) for d,m in ks if not any(pk-pd.DateOffset(months=6)<=m<=tr+pd.DateOffset(months=3) for pk,tr in zip(PK,TR))]
    print(f"K {pct}%: proposals inside recession windows {len(inrec)}: {inrec}")
    print(f"        outside (day, month, S&P fall from 20-day high on that day): {out}")
print('2020: K single-week reading on Mar 19 release (week ending Mar 14):', round(float(((ICfp.dropna()/ICfp.dropna().rolling(52).min().shift(1)-1)*100)[pd.Timestamp('2020-03-14')]),1),'%; S&P fall from 20-day high on Mar 19, 2020:',round(float(crash[crash.index<=pd.Timestamp('2020-03-19')].iloc[-1]),1),'%')
print('crash days >=10% since 1962 by year:',sorted(set(crash[crash>=10].index.year.tolist())))
