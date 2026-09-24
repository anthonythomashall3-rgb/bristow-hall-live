"""THE PAPER SPREAD ABROAD, SCORED. One global line in each country's own trailing robust scale — no per-country
fitting, and the scale is a TRAILING median absolute deviation, never a whole-sample statistic (the defect the
alternative line hit). Detection = the object stands at the line inside [peak-6, peak+4] data months. A quiet month is
one outside [peak-6, trough+6] of any episode in that country's chronology."""
exec(open('intl1.py').read().split('P("\\nspread spans:")')[0].replace("out=open('intl1.out','w')","out=open('intl2.out','w')"))
P("\nECRI chronology shape:", {k:(list(v)[:2] if isinstance(v,dict) else str(v)[:80]) for k,v in list(E.items())[:2]})
ISO={'United States':'USA','Canada':'CAN','Mexico':'MEX','Brazil':'BRA','Germany':'DEU','France':'FRA','United Kingdom':'GBR','Italy':'ITA',
     'Japan':'JPN','Korea':'KOR','Australia':'AUS','Spain':'ESP','Switzerland':'CHE','Sweden':'SWE','Austria':'AUT','New Zealand':'NZL','India':'IND','China':'CHN','Taiwan':'TWN','South Africa':'ZAF'}
def episodes(country):
    v=E[country]
    pk=[pd.Timestamp(d) for k,d in v if k=='P']; tr=[pd.Timestamp(d) for k,d in v if k=='T']
    n=min(len(pk),len(tr)); return pk[:n],tr[:n]
rows=[]
for name in E:
    iso=ISO.get(name)
    if iso is None or iso not in SP: P(f"   {name}: no spread held"); continue
    pk,tr=episodes(name); s=SP[iso]; G=obj(s); Z=zscale(G)
    if not len(Z): continue
    lo,hi=Z.index.min(),Z.index.max()
    ep=[(p,t) for p,t in zip(pk,tr) if p>=lo and p<=hi]
    quiet=[m for m in Z.index if not any(p-pd.DateOffset(months=6)<=m<=t+pd.DateOffset(months=6) for p,t in zip(pk,tr))]
    rows.append((name,iso,Z,ep,quiet))
    P(f"   {name} ({iso}): scale from {lo.date()}, {len(ep)} ECRI episodes in range, {len(quiet)} quiet months")
P(f"\n{'k':>5} {'detected':>10} {'quiet fires':>12} {'per 100 quiet yrs':>18}")
for k in [1.5,2.0,2.5,3.0,3.5,4.0,5.0,6.0]:
    det=0; tot=0; qf=0; qm=0
    for name,iso,Z,ep,quiet in rows:
        for p,t in ep:
            tot+=1
            w=Z[(Z.index>=p-pd.DateOffset(months=6))&(Z.index<=p+pd.DateOffset(months=4))]
            if len(w) and float(w.max())>=k: det+=1
        qz=Z.reindex(quiet).dropna(); qm+=len(qz); qf+=int((qz>=k).sum())
    P(f"{k:5.1f} {str(det)+'/'+str(tot):>10} {qf:12d} {qf/(qm/12)*100:18.1f}")
P("\nAMERICA ALONE, the same object and the same scaling, for comparison:")
nm=[r for r in rows if r[1]=='USA']
if nm:
    name,iso,Z,ep,quiet=nm[0]
    for k in [1.5,2.0,2.5,3.0,4.0]:
        det=sum(1 for p,t in ep if len(Z[(Z.index>=p-pd.DateOffset(months=6))&(Z.index<=p+pd.DateOffset(months=4))]) and float(Z[(Z.index>=p-pd.DateOffset(months=6))&(Z.index<=p+pd.DateOffset(months=4))].max())>=k)
        qz=Z.reindex(quiet).dropna(); qf=int((qz>=k).sum())
        P(f"   k {k}: {det}/{len(ep)} detected, {qf} quiet fires in {len(qz)/12:.0f} quiet years")
out.close()
