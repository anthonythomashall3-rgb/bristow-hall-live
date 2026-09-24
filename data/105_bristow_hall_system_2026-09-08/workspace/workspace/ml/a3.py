m4=ICfp.dropna().rolling(4).mean(); low=m4.rolling(52,min_periods=52).min().shift(1); med=m4.rolling(260,min_periods=156).median().shift(1)
t=pd.Timestamp('2022-08-06'); print('Aug 6 2022: 4wk mean',int(m4[t]),'52wk low',int(low[t]),'5yr median',int(med[t]),'low/median %.2f'%(low[t]/med[t]),'0.85*median',int(0.85*med[t]))
print('lowest 4-week mean since 1968 before 2022:',int(m4[:'2021'].min()),'at',m4[:'2021'].idxmin().date(),'| 2022 min',int(m4['2022'].min()),'at',m4['2022'].idxmin().date())
print('MAD10 at year-ends:',{y:round(float(MAD10[str(y)].dropna().iloc[-1]),2) for y in (1979,1999,2019,2026)})
