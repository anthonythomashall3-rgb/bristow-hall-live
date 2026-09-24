"""THE TRUE ANALOGUE ABROAD: BANK PAPER OVER THE SOVEREIGN BILL. The interbank-less-call spread of intl2 was the wrong
object — it is a term spread inside the banking system, and it fails even in America (5 of 6 ECRI turns at 20 per cent
quiet exposure). The American object is PRIVATE PAPER OVER A TREASURY BILL, a credit-risk spread. Five economies have
both legs monthly: the OECD three-month interbank rate (collection 93) and the OECD three-month Treasury-bill rate
(fetched from FRED into the same collection) — United Kingdom, Mexico, Sweden, South Africa, Hungary (Turkey and China
too short). Scored the same way, one global line in each country's own trailing robust scale."""
exec(open('intl1.py').read().split('P("\\nspread spans:")')[0].replace("out=open('intl1.out','w')","out=open('intl3.out','w')"))
BILL={}
import glob
for f in glob.glob(os.path.join(D93,'data','fred_bills','*.csv')):
    sid=os.path.basename(f)[:-4]; cc=sid[8:10]
    m={'CN':'CHN','GB':'GBR','HU':'HUN','MX':'MEX','SE':'SWE','TR':'TUR','ZA':'ZAF'}[cc]
    BILL[m]=ld(f)
P("bill-rate legs held:",{k:(str(v.index.min().date())+'->'+str(v.index.max().date())) for k,v in BILL.items()})
IB={}
for iso,d in CO.items():
    if 'IR3TIB' in d: IB[iso]=ld(d['IR3TIB'].get('STES') or d['IR3TIB'].get('KEI'))
PB={}
for iso in BILL:
    if iso not in IB: continue
    a=IB[iso]; b=BILL[iso]; idx=a.index.intersection(b.index)
    s=(a.reindex(idx)-b.reindex(idx)).dropna()
    if len(s)>=120: PB[iso]=s; P(f"   {iso}: paper-over-bill spread {s.index.min().date()} -> {s.index.max().date()} ({len(s)} months), median {float(s.median()):.2f}")
ISO={'United States':'USA','Canada':'CAN','Mexico':'MEX','Brazil':'BRA','Germany':'DEU','France':'FRA','United Kingdom':'GBR','Italy':'ITA',
     'Japan':'JPN','Korea':'KOR','Australia':'AUS','Spain':'ESP','Switzerland':'CHE','Sweden':'SWE','Austria':'AUT','New Zealand':'NZL','China':'CHN','South Africa':'ZAF','Hungary':'HUN'}
def episodes(country):
    v=E[country]; pk=[pd.Timestamp(d) for k,d in v if k=='P']; tr=[pd.Timestamp(d) for k,d in v if k=='T']
    n=min(len(pk),len(tr)); return pk[:n],tr[:n]
rows=[]
for name in E:
    iso=ISO.get(name)
    if iso is None or iso not in PB: continue
    pk,tr=episodes(name); G=obj(PB[iso]); Z=zscale(G)
    if not len(Z): continue
    ep=[(p,t) for p,t in zip(pk,tr) if Z.index.min()<=p<=Z.index.max()]
    quiet=[m for m in Z.index if not any(p-pd.DateOffset(months=6)<=m<=t+pd.DateOffset(months=6) for p,t in zip(pk,tr))]
    rows.append((name,iso,Z,ep,quiet)); P(f"   {name} ({iso}): {len(ep)} ECRI episodes in range, {len(quiet)} quiet months")
P(f"\n{'k':>5} {'detected':>10} {'quiet months at the line':>26} {'exposure %':>11}")
for k in [1.5,2.0,2.5,3.0,4.0,5.0]:
    det=0; tot=0; qf=0; qm=0
    for name,iso,Z,ep,quiet in rows:
        for p,t in ep:
            tot+=1; w=Z[(Z.index>=p-pd.DateOffset(months=6))&(Z.index<=p+pd.DateOffset(months=4))]
            if len(w) and float(w.max())>=k: det+=1
        qz=Z.reindex(quiet).dropna(); qm+=len(qz); qf+=int((qz>=k).sum())
    P(f"{k:5.1f} {str(det)+'/'+str(tot):>10} {qf:26d} {qf/max(qm,1)*100:11.1f}")
P("\nFOR COMPARISON — the AMERICAN object (one-month commercial paper less the three-month bill, weekly) read the same way:")
exec(open('fast51.py').read().split("def full(")[0].replace("out=open('fast51.out','w')","out2=open('/dev/null','w')").replace("P(","P0(").replace("out2=open","out=open"))
