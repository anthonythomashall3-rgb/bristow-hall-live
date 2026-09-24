#!/usr/bin/env python3
"""The objects for the financial-leg conjunction. Fixed list, one GET each, cosd pinned."""
import csv, os, time, urllib.request
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, 'data'); os.makedirs(DATA, exist_ok=True)
URL = 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=%s&cosd=1776-07-04&coed=9999-12-31'
SERIES = [
 # --- the labour core (what already works) ---
 ('UNRATE','labour','unemployment rate, 1948 on'),
 ('ICNSA','labour','initial claims, unadjusted weekly, 1967 on'),
 ('CCNSA','labour','continued claims, unadjusted weekly, 1967 on'),
 ('IURNSA','labour','insured unemployment rate, weekly, 1971 on'),
 ('PAYEMS','labour','total nonfarm payrolls, 1939 on'),
 ('AWHMAN','labour','average weekly hours manufacturing, 1939 on'),
 ('TEMPHELPS','labour','temporary help employment, 1990 on'),
 # --- the money and credit channel (collection 164, orphaned) ---
 ('DTB3','money','three-month Treasury bill daily, 1954 on'),
 ('WTB3MS','money','three-month Treasury bill weekly, 1954 on'),
 ('TB3MS','money','three-month Treasury bill monthly, 1934 on'),
 ('AAA','money','Moody s Aaa corporate bond yield, monthly, 1919 on'),
 ('BAA','money','Moody s Baa corporate bond yield, monthly, 1919 on'),
 ('MPRIME','money','bank prime loan rate, 1949 on'),
 ('FEDFUNDS','money','effective federal funds rate, monthly, 1954 on'),
 ('DCPN3M','money','three-month AA nonfinancial commercial paper, 1997 on'),
 ('DCPF3M','money','three-month AA financial commercial paper, 1997 on'),
 ('H0RIFSPPFD15NB','money','fifteen-day finance paper placed directly, 1972-1996'),
 ('H0RIFSPPFM06NB','money','six-month finance paper placed directly, 1954-1997'),
 ('WCP3M','money','three-month prime commercial paper weekly, 1971-1997'),
 # --- the term spread: collection 85 found the gate moved the causal frontier ---
 ('GS10','term','ten-year Treasury constant maturity, monthly, 1953 on'),
 ('GS1','term','one-year Treasury constant maturity, monthly, 1953 on'),
 ('T10Y3M','term','ten-year less three-month spread, daily, 1982 on'),
 # --- the activity channel (collection 165, orphaned) ---
 ('CFNAI','activity','Chicago Fed national activity index, 1967 on'),
 ('CFNAIMA3','activity','Chicago Fed national activity index, three-month average'),
 ('CFNAIDIFF','activity','Chicago Fed national activity index, diffusion form'),
 ('INDPRO','activity','industrial production, 1919 on'),
 ('IPMAT','activity','industrial production, materials, 1939 on'),
 # --- the diffusion channel (collection 173, orphaned; live and reaches 1968) ---
 ('GACDFSA066MSFRBPHI','diffusion','Philadelphia Fed general activity diffusion index, May 1968 on'),
 ('NOCDFSA066MSFRBPHI','diffusion','Philadelphia Fed new orders diffusion index, May 1968 on'),
 ('NECDFSA066MSFRBPHI','diffusion','Philadelphia Fed number of employees diffusion index, May 1968 on'),
 # --- market ---
 ('SP500','market','S&P 500, daily, recent only'),
]
rows = []
for sid, ch, note in SERIES:
    p = os.path.join(DATA, sid + '.csv')
    try:
        with urllib.request.urlopen(URL % sid, timeout=60) as r: body = r.read()
        ln = body.decode('utf-8', 'replace').strip().split('\n')
        n = len(ln) - 1
        first = ln[1].split(',')[0] if n > 0 else ''
        last = ln[-1].split(',')[0] if n > 0 else ''
        if not first[:4].isdigit(): n, first, last, st = 0, '', '', 'INVALID_ID'
        else: open(p, 'wb').write(body); st = 'ok'
    except Exception as e:
        n, first, last, st = 0, '', '', 'FAIL %s' % e
    rows.append(dict(id=sid, channel=ch, file=sid + '.csv', n=n, first=first, last=last,
                     status=st, source=URL % sid, gathered='2026-09-15', note=note))
    print('%-20s %-9s %-11s %s .. %s' % (sid, ch, st, first, last), flush=True)
    time.sleep(0.12)
with open(os.path.join(HERE, 'MANIFEST.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print('manifest rows', len(rows))
