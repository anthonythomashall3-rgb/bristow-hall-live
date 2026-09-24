for pct in (25,30):
    ks,relK=leg_Kb(pct)
    out=[(d.date().isoformat(),round(float(crash[crash.index<=d].iloc[-1]),1)) for d,m in ks if d.year>=1962 and not any(pk-pd.DateOffset(months=6)<=m<=tr+pd.DateOffset(months=3) for pk,tr in zip(PK,TR))]
    print(f'K {pct} on the floored base, outside recessions (day, S&P fall):',out)
    for cl in (10,15):
        r,t,Kc=build_K(p0,pct,cl); report(f"K {pct} (floored base) + crash {cl}",r,t); print('   fires:',[(d.date().isoformat(),m.strftime('%Y-%m')) for d,m in Kc if d.year>=1962])
