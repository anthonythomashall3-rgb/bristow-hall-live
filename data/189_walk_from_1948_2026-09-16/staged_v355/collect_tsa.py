#!/usr/bin/env python3
"""TSA checkpoint throughput (daily passengers), the one activity series that blocks direct fetch (Akamai 403).
Fetched through the Nimble web API -- eight requests once for the history, one per refresh -- and parsed from the
table on tsa.gov. Output: /mnt/user-data/outputs/alt/tsa_throughput.csv (date, passengers[, prior-year columns])."""
import re, os, json, csv, time, urllib.request, html
OUT = '/mnt/user-data/outputs/alt'; os.makedirs(OUT, exist_ok=True)
ENV = '/mnt/user-data/uploads/Onset Detector Data/onset-detector-new-2026-08-23/live_data/config/local.env'
k = re.search(r'^NIMBLE_API_KEY=([^\r\n]+)', open(ENV).read(), re.M).group(1).strip().strip('"').strip("'")
def nimble(url):
    body = json.dumps({"url": url, "format": "html", "render": False, "country": "US"}).encode()
    req = urllib.request.Request('https://api.webit.live/api/v1/realtime/web', data=body, headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + k})
    with urllib.request.urlopen(req, timeout=180) as r: return r.read().decode(errors='ignore')
rows = {}
pages = ['https://www.tsa.gov/travel/passenger-volumes'] + ['https://www.tsa.gov/travel/passenger-volumes/%d' % y for y in range(2019, 2026)]
for u in pages:
    try:
        h = nimble(u); time.sleep(1)
    except Exception as e:
        print(u, 'ERR', type(e).__name__); continue
    trs = re.findall(r'<tr[^>]*>(.*?)</tr>', h, re.S); n = 0
    for tr in trs:
        cells = [html.unescape(re.sub(r'<[^>]+>', '', c)).strip() for c in re.findall(r'<td[^>]*>(.*?)</td>', tr, re.S)]
        if len(cells) >= 2 and re.fullmatch(r'\d{1,2}/\d{1,2}/\d{4}', cells[0]):
            m, d, y = cells[0].split('/'); date = '%s-%02d-%02d' % (y, int(m), int(d))
            v = cells[1].replace(',', '')
            if v.isdigit(): rows[date] = int(v); n += 1
    print(u, 'rows', n, flush=True)
with open(os.path.join(OUT, 'tsa_throughput.csv'), 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['date', 'passengers'])
    for d in sorted(rows): w.writerow([d, rows[d]])
print('tsa total days', len(rows), min(rows) if rows else '', max(rows) if rows else '')
