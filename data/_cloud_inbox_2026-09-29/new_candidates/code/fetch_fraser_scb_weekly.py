#!/usr/bin/env python3
"""Download every issue of 'Survey of Current Business. Business Statistics (Weekly Supplement)'
held by FRASER (title 57), 1939-1981: 4-page weekly issues whose 'WEEKLY BUSINESS STATISTICS' table
prints, as they stood that week, steel ingot production, electric power (EEI), bituminous coal,
crude runs, freight carloadings (AAR), lumber, department store sales, initial claims, insured
unemployment, business failures (D&B), wholesale prices, bank and Fed data, bond yields, stocks.

Item list comes from the decade browse pages (?browse=1930s ... 1980s). The PDF path is guessed from
the issue date (files/docs/releases/busstat_wkly/scb_weekly_YYYYMMDD.pdf); if that is not a PDF the
item page is fetched and its files/docs link used. Plain urllib UA (FRASER drops browser UAs),
>= 1.1 s between requests. Resume-safe.
"""
import os, re, csv, time, datetime, urllib.request

W = '/tmp/claude-0/-home-user/49f76bce-ebc7-5769-b106-ce7685453d86/scratchpad/collect/new_candidates'
D = os.path.join(W, 'raw', 'fraser'); P = os.path.join(D, 'pages'); O = os.path.join(D, 'scb_weekly_pdf')
os.makedirs(O, exist_ok=True)
T = 'survey-current-business-business-statistics-weekly-supplement-57'
BASE = 'https://fraser.stlouisfed.org'
_last = [0.0]
MONTHS = {m: i for i, m in enumerate(['january', 'february', 'march', 'april', 'may', 'june', 'july',
                                       'august', 'september', 'october', 'november', 'december'], 1)}

def get(url, timeout=180):
    wait = float(os.environ.get('SPACING', '1.1')) - (time.time() - _last[0])
    if wait > 0: time.sleep(wait)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.getcode(), r.read()
    except urllib.error.HTTPError as e:
        return e.code, b''
    except Exception as e:
        return 0, repr(e).encode()
    finally:
        _last[0] = time.time()

items = {}
for dec in ['1930s', '1940s', '1950s', '1960s', '1970s', '1980s']:
    p = os.path.join(P, 't57_%s.html' % dec)
    if not os.path.exists(p):
        c, b = get('%s/title/%s?browse=%s' % (BASE, T, dec)); open(p, 'wb').write(b)
    for m in re.finditer(r'href="/title/%s/([a-z]+)-(\d+)-(\d{4})-(\d+)"' % T, open(p, errors='replace').read()):
        mon, day, yr, iid = m.groups()
        if mon not in MONTHS: continue
        d = datetime.date(int(yr), MONTHS[mon], int(day))
        items[iid] = (d, '%s/title/%s/%s-%s-%s-%s' % (BASE, T, mon, day, yr, iid))

import sys
# Optional date window: fetch_fraser_scb_weekly.py [FROM YYYY-MM-DD] [TO YYYY-MM-DD]
# 2026-09-29 run: 1939-01-05..1948-11-26 fetched here, then STOPPED because a sibling collector
# (collect/claims_pre1975, scripts/fetch_all.py scbw) is pulling 1947-1976 from the same host; this
# script is re-run for 1977-01-01..1981-12-31 only, to fill the gap without duplicating it.
lo = datetime.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else datetime.date(1900, 1, 1)
hi = datetime.date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else datetime.date(2100, 1, 1)
rows = sorted(((d, iid, u) for iid, (d, u) in items.items() if lo <= d <= hi))
logp = os.path.join(D, 'scb_weekly_index_%s_%s.csv' % (lo.year, hi.year) if len(sys.argv) > 1 else 'scb_weekly_index.csv')
done = {}
if os.path.exists(logp):
    for r in csv.DictReader(open(logp)):
        done[r['item_id']] = r
out = []
for d, iid, u in rows:
    if iid in done and done[iid]['status'] == 'ok' and os.path.exists(os.path.join(O, done[iid]['file'])):
        out.append(done[iid]); continue
    fn = 'scb_weekly_%s.pdf' % d.strftime('%Y%m%d')
    url = '%s/files/docs/releases/busstat_wkly/%s' % (BASE, fn)
    c, b = get(url)
    if not b.startswith(b'%PDF'):
        c2, h = get(u)
        m = re.search(rb'(files/docs/[^"\' <]+\.pdf)', h)
        if m:
            url = BASE + '/' + m.group(1).decode(); fn = os.path.basename(url)
            c, b = get(url)
    ok = b.startswith(b'%PDF')
    if ok: open(os.path.join(O, fn), 'wb').write(b)
    out.append(dict(issue_date=d.isoformat(), item_id=iid, item_url=u, pdf_url=url, file=fn,
                    bytes=len(b), status='ok' if ok else 'fail_%s' % c))
    print(d, c, len(b), flush=True)
    if len(out) % 25 == 0:
        with open(logp, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
with open(logp, 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
print('DONE', len(out), sum(r['status'] == 'ok' for r in out))
