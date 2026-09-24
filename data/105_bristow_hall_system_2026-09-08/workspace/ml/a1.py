low=spl.rolling(52,min_periods=52).min().shift(1); gapP=(spl-low); gapR=((spl/low-1)*100); rows=[]
for pk,tr in zip(PK,TR):
    if pk<pd.Timestamp('1971-06-01'): continue
    w=(spl.index>=pk-pd.DateOffset(months=6))&(spl.index<=tr+pd.DateOffset(months=3))
    lp=low[w].iloc[0]; d45=gapP[w][gapP[w]>=0.45]; d20=gapP[w][gapP[w]>=0.20]
    first45=d45.index[0].date() if len(d45) else None; first20=d20.index[0].date() if len(d20) else None
    r45=round(float(gapR[w].loc[:d45.index[0]].max()),1) if len(d45) else None
    r20=round(float(gapR[w].loc[:d20.index[0]].max()),1) if len(d20) else None
    rows.append(dict(peak=pk.strftime('%Y-%m'),low_at_start=round(float(lp),2),first_045=first45,pct_at_045=r45,first_020=first20,pct_at_020=r20,max_pt=round(float(gapP[w].max()),2),max_pct=round(float(gapR[w].max()),1)))
for r in rows: print(r)
print('calm maxima of the gaps by span (weeks outside NBER recessions, 3 months before the peak to 6 after the trough):')
mask=pd.Series(True,index=spl.index)
for pk,tr in zip(PK,TR): mask[(spl.index>=pk-pd.DateOffset(months=3))&(spl.index<=tr+pd.DateOffset(months=6))]=False
for a,b in [('1972','1979'),('1983','1989'),('1992','2000'),('2002','2007'),('2010','2019'),('2021','2026')]:
    s=gapR[mask][a:b].dropna(); sp=gapP[mask][a:b].dropna()
    print(a,b,'pct max %.1f'%s.max(),'at',s.idxmax().date(),'| point max %.2f'%sp.max(),'at',sp.idxmax().date(),'| low level at pct max %.2f'%low[s.idxmax()],'| median level %.2f'%spl[a:b].median())
