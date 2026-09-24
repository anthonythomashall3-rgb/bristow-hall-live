print('MAD10 of the claims object (percent above 52-week low), by year-end:')
print({y:round(float(MAD10[str(y)].dropna().iloc[-1]),1) for y in range(1975,2027,3) if len(MAD10[str(y)].dropna())})
print('implied line at k=5:',{y:round(5*float(MAD10[str(y)].dropna().iloc[-1]),1) for y in (1979,1989,1999,2007,2019,2022,2026) if len(MAD10[str(y)].dropna())})
RESN={}
print('==== family N (claims line = k x trailing 10-year MAD)')
for k in (2,3,4,5,6,8,10):
    r,t=build_alt(p0,'N',dict(k=k)); RESN[('N',k)]=(r,t); report(f"N k={k}",r,t)
print('==== family Q (claims line = expanding quantile of its own history, from 1973)')
for q in (95,97.5,99,99.5):
    r,t=build_alt(p0,'Q',dict(q=q)); RESN[('Q',q)]=(r,t); report(f"Q q={q}",r,t)
for q in (95,97.5,99,99.5):
    L=_EQ[q]; print('quantile',q,'line path:',{y:round(float(L[str(y)].dropna().iloc[-1]),1) for y in (1975,1985,1995,2005,2015,2026) if len(L[str(y)].dropna())})
