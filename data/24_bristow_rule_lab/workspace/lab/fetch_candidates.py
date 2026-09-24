import urllib.request, os, csv, sys
CC={'United States':'USA','Canada':'CAN','Japan':'JPN','Euro area':'EA19','Spain':'ESP','France':'FRA'}
TPL=[('industrial production','PRINTO01{cc}M661S'),
     ('manufacturing production','PRMNTO01{cc}M661S'),
     ('retail trade volume','SLRTTO01{cc}M661S'),
     ('passenger car registrations','SLRTCR03{cc}M661S'),
     ('exports value','XTEXVA01{cc}M664S'),
     ('imports value','XTIMVA01{cc}M664S'),
     ('business confidence','BSCICP03{cc}M665S'),
     ('consumer confidence','CSCICP03{cc}M665S'),
     ('employment','LFEMTTTT{cc}M647S'),
     ('unemployment level','LFHUTTTT{cc}M647S'),
     ('hours worked manufacturing','HOHWMN02{cc}M065S'),
     ('total construction','PRCNTO01{cc}M661S')]
os.makedirs('cand',exist_ok=True)
ok=[]
for c,cc in CC.items():
    for nm,tpl in TPL:
        sid=tpl.format(cc=cc); path=f'cand/{sid}.csv'
        if os.path.exists(path) and os.path.getsize(path)>200: ok.append((c,nm,sid)); continue
        try:
            urllib.request.urlretrieve(f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}', path)
            rows=[r for r in csv.reader(open(path))][1:]
            rows=[r for r in rows if r and r[1] not in ('','.')]
            if len(rows)>120: ok.append((c,nm,sid)); print(f'{c:14s} {nm:28s} {sid:18s} {rows[0][0]} .. {rows[-1][0]}  n={len(rows)}')
            else: os.remove(path)
        except Exception as e:
            pass
print('usable:',len(ok))
